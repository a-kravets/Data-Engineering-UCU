import os
import time
import logging
from flask import Flask, request, jsonify
import requests
import threading
from collections import OrderedDict, defaultdict

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [MASTER] %(levelname)s: %(message)s")

# Master log
master_log = []
master_lock = threading.Lock()

# Registered secondaries
secondaries = {}
secondaries_lock = threading.Lock()

# Pending per-secondary queues
pending_per_secondary = defaultdict(OrderedDict)
pending_lock = threading.Lock()

# Entry waiters for write concern blocking
entry_waiters = {}
entry_waiters_lock = threading.Lock()

# Secondary health tracking
secondary_status = {}
status_lock = threading.Lock()

# Config
REPLICATE_TIMEOUT_SEC = float(os.environ.get("REPLICATE_TIMEOUT_SEC", "5.0"))
MAX_WORKERS = int(os.environ.get("MASTER_MAX_WORKERS", "16"))
MASTER_WRITE_TIMEOUT_SEC = float(os.environ.get("MASTER_WRITE_TIMEOUT_SEC", "300.0"))
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL_SEC", "5.0"))
HEARTBEAT_THRESHOLD = int(os.environ.get("HEARTBEAT_THRESHOLD", "3"))
RE_ENQUEUE_INTERVAL = float(os.environ.get("MASTER_REENQUEUE_INTERVAL_SEC", "5.0"))

# Sequence
_seq_lock = threading.Lock()
_seq = 0
def next_seq():
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq

@app.route("/register", methods=["POST"])
def register_secondary():
    data = request.get_json() or {}
    sid = data.get("id")
    url = data.get("url")
    if not sid or not url:
        return jsonify({"error": "id and url required"}), 400

    with secondaries_lock:
        secondaries[sid] = url

    with status_lock:
        secondary_status[sid] = {"status": "Healthy", "last_seen": time.time(), "misses": 0}

    with pending_lock:
        _ = pending_per_secondary.setdefault(sid, OrderedDict())

    app.logger.info(f"Registered secondary {sid} -> {url}")

    # Start delivery worker
    start_delivery_worker_if_needed(sid, url)

    # Backfill: ask last applied id
    last_id = 0
    try:
        resp = requests.get(f"{url.rstrip('/')}/status", timeout=REPLICATE_TIMEOUT_SEC)
        if resp.status_code == 200:
            info = resp.json()
            last_id = int(info.get("last_id", 0))
    except Exception as e:
        app.logger.warning(f"Could not get status from {sid}: {e}")
        last_id = 0

    with master_lock, pending_lock:
        for e in master_log:
            if e["id"] > last_id and e["id"] not in pending_per_secondary[sid]:
                pending_per_secondary[sid][e["id"]] = e

    return jsonify({"status": "registered", "secondaries": list(secondaries.keys())}), 200


def replicate_to_secondary_once(sid, url, entry):
    replicate_url = f"{url.rstrip('/')}/replicate"
    try:
        r = requests.post(replicate_url, json=entry, timeout=REPLICATE_TIMEOUT_SEC)
        if r.status_code == 200:
            return True, None
        else:
            return False, {"status_code": r.status_code, "body": r.text}
    except requests.RequestException as e:
        return False, {"error": str(e)}


def start_delivery_worker_if_needed(sid, url):
    thread_name = f"delivery-worker-{sid}"
    if any(t.name == thread_name for t in threading.enumerate()):
        return

    def worker():
        base_backoff = 0.5
        while True:
            try:
                with pending_lock:
                    queue = pending_per_secondary.get(sid, OrderedDict())
                    items = list(queue.items())
                if not items:
                    time.sleep(0.2)
                    continue
                for entry_id, entry in items:
                    ok, detail = replicate_to_secondary_once(sid, url, entry)
                    if ok:
                        with entry_waiters_lock:
                            waiter = entry_waiters.get(entry_id)
                            if waiter:
                                waiter["results"][sid] = {"ack": True}
                                waiter["ack_count"] += 1
                                try:
                                    with waiter["cond"]:
                                        waiter["cond"].notify_all()
                                except RuntimeError:
                                    pass
                        with pending_lock:
                            pending_per_secondary[sid].pop(entry_id, None)
                        with status_lock:
                            st = secondary_status.setdefault(sid, {})
                            st["last_seen"] = time.time()
                            st["misses"] = 0
                            st["status"] = "Healthy"
                        continue
                    else:
                        with status_lock:
                            st = secondary_status.setdefault(sid, {"misses": 0})
                            st["misses"] = st.get("misses", 0) + 1
                            st["last_seen"] = time.time()
                            if st["misses"] >= HEARTBEAT_THRESHOLD:
                                st["status"] = "Unhealthy"
                            else:
                                st["status"] = "Suspected"
                        delay = min(base_backoff * (2 ** st["misses"]), 30)
                        time.sleep(delay)
                        break
            except Exception as e:
                app.logger.exception(f"Delivery worker {sid} crashed: {e}")
                time.sleep(1)

    t = threading.Thread(target=worker, name=thread_name, daemon=True)
    t.start()


@app.route("/", methods=["POST"])
def append_message():
    data = request.get_json() or {}
    message = data.get("message")
    try:
        w = int(data.get("w", len(dict(secondaries)) + 1))
    except Exception:
        return jsonify({"error": "w must be integer >= 1"}), 400

    if message is None:
        return jsonify({"error": "message required"}), 400
    if w < 1:
        return jsonify({"error": "w must be >= 1"}), 400

    seq_id = next_seq()
    entry = {"id": seq_id, "message": message, "timestamp": time.time()}

    with master_lock:
        master_log.append(entry)

    with secondaries_lock:
        targets = dict(secondaries)
    total_nodes = 1 + len(targets)
    if w > total_nodes:
        return jsonify({"error": f"w={w} too large for cluster size {total_nodes}"}), 400
    required_acks = max(0, w - 1)

    if required_acks == 0:
        with pending_lock:
            for sid, url in targets.items():
                pending_per_secondary[sid][seq_id] = entry
                start_delivery_worker_if_needed(sid, url)
        return jsonify({"status": "ok", "w": w, "entry": entry}), 200

    if len(targets) == 0 and required_acks > 0:
        return jsonify({"status": "failed", "reason": "no secondaries", "required_acks": required_acks}), 500

    cond = threading.Condition()
    waiter = {"cond": cond, "ack_count": 0, "results": {}}
    with entry_waiters_lock:
        entry_waiters[seq_id] = waiter

    with pending_lock:
        for sid, url in targets.items():
            pending_per_secondary[sid][seq_id] = entry
            start_delivery_worker_if_needed(sid, url)

    start_wait = time.time()
    with cond:
        while waiter["ack_count"] < required_acks:
            remaining = MASTER_WRITE_TIMEOUT_SEC - (time.time() - start_wait)
            if remaining <= 0:
                break
            cond.wait(timeout=remaining)

    with entry_waiters_lock:
        final_ack = waiter["ack_count"]
        final_results = waiter["results"]
        try:
            del entry_waiters[seq_id]
        except KeyError:
            pass

    if final_ack >= required_acks:
        return jsonify({"status": "ok", "w": w, "entry": entry, "acks_received": final_ack, "results": final_results}), 200
    else:
        return jsonify({"status": "partial_failure", "required_acks": required_acks, "acks_received": final_ack, "results": final_results}), 500


@app.route("/", methods=["GET"])
def get_messages():
    with master_lock:
        return jsonify({"messages": list(master_log)}), 200


@app.route("/secondaries/messages", methods=["GET"])
def get_secondary_messages():
    with secondaries_lock:
        targets = dict(secondaries)
    aggregated = {}
    for sid, url in targets.items():
        try:
            resp = requests.get(f"{url.rstrip('/')}/", timeout=REPLICATE_TIMEOUT_SEC)
            aggregated[sid] = resp.json() if resp.status_code == 200 else {"error": resp.status_code}
        except Exception as e:
            aggregated[sid] = {"error": str(e)}
    return jsonify(aggregated), 200


@app.route("/health", methods=["GET"])
def health():
    with status_lock:
        return jsonify(secondary_status), 200


def heartbeat_loop():
    while True:
        with secondaries_lock:
            targets = dict(secondaries)
        for sid, url in targets.items():
            try:
                resp = requests.get(f"{url.rstrip('/')}/health", timeout=REPLICATE_TIMEOUT_SEC)
                with status_lock:
                    st = secondary_status.setdefault(sid, {})
                    st["last_seen"] = time.time()
                    st["misses"] = 0
                    st["status"] = "Healthy" if resp.status_code == 200 else "Suspected"
            except Exception:
                with status_lock:
                    st = secondary_status.setdefault(sid, {})
                    st["misses"] = st.get("misses", 0) + 1
                    if st["misses"] >= HEARTBEAT_THRESHOLD:
                        st["status"] = "Unhealthy"
                    else:
                        st["status"] = "Suspected"
            # Re-enqueue missing entries for reliability
            with master_lock, pending_lock:
                q = pending_per_secondary.setdefault(sid, OrderedDict())
                for e in master_log:
                    if e["id"] not in q:
                        q[e["id"]] = e
        time.sleep(HEARTBEAT_INTERVAL)


def worker_supervisor():
    while True:
        with secondaries_lock:
            for sid, url in secondaries.items():
                start_delivery_worker_if_needed(sid, url)
        time.sleep(2)


def reenqueue_loop():
    while True:
        with secondaries_lock:
            targets = dict(secondaries)
        with master_lock, pending_lock:
            for sid in targets.keys():
                q = pending_per_secondary.setdefault(sid, OrderedDict())
                for e in master_log:
                    if e["id"] not in q:
                        q[e["id"]] = e
        time.sleep(RE_ENQUEUE_INTERVAL)


if __name__ == "__main__":
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=reenqueue_loop, daemon=True).start()
    threading.Thread(target=worker_supervisor, daemon=True).start()
    host = "0.0.0.0"
    port = int(os.environ.get("MASTER_PORT", 5000))
    app.run(host=host, port=port, threaded=True)
