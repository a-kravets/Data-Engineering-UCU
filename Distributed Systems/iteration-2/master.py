# master.py
import os
import time
import logging
from flask import Flask, request, jsonify
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [MASTER] %(levelname)s: %(message)s")

# In-memory ordered log at master. Each entry: {"id": int, "message": str, "timestamp": float}
master_log = []
master_lock = threading.Lock()

# Registered secondaries: map id -> url
secondaries = {}
secondaries_lock = threading.Lock()

# Configs
# Per-secondary request timeout (seconds)
REPLICATE_TIMEOUT_SEC = float(os.environ.get("REPLICATE_TIMEOUT_SEC", "5.0"))
# How many worker threads for parallel replication
MAX_WORKERS = int(os.environ.get("MASTER_MAX_WORKERS", "16"))

# Monotonic sequence counter for total ordering
# Currently is not used
_seq_lock = threading.Lock()
_seq = 0


def next_seq():
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq


@app.route("/register", methods=["POST"])
def register_secondary():
    """
    Secondary calls POST /register with JSON {"id": "...", "url": "http://ip:port"}
    """
    data = request.get_json() or {}
    sid = data.get("id")
    url = data.get("url")
    if not sid or not url:
        return jsonify({"error": "id and url required"}), 400

    with secondaries_lock:
        secondaries[sid] = url
    app.logger.info(f"Registered secondary {sid} -> {url}")
    return jsonify({"status": "registered", "secondaries": list(secondaries.keys())}), 200


def replicate_to_secondary(sid, url, entry):
    """
    Send replicate request to one secondary. Returns tuple (sid, ok(boolean), details)
    """
    replicate_url = f"{url.rstrip('/')}/replicate"
    try:
        app.logger.debug(f"Sending replicate to {sid} @ {replicate_url}")
        r = requests.post(replicate_url, json=entry, timeout=REPLICATE_TIMEOUT_SEC)
        if r.status_code == 200:
            return sid, True, None
        else:
            return sid, False, {"status_code": r.status_code, "body": r.text}
    except requests.RequestException as e:
        return sid, False, {"error": str(e)}


@app.route("/", methods=["POST"])
def append_message():
    """
    Client -> POST /   JSON: {"message": "...", "w": <int>}
    w is the write concern (1 = master only, 2 = master + 1 secondary, etc.)
    Master appends message locally and then replicates to secondaries.
    Master returns only after receiving (w-1) ACKs from secondaries (or error if impossible).
    """
    data = request.get_json() or {}
    message = data.get("message")
    try:
        w = int(data.get("w", len(dict(secondaries)) + 1))  # default w = # secondary + 1
    except Exception:
        return jsonify({"error": "w must be integer >= 1"}), 400

    if message is None:
        return jsonify({"error": "message required"}), 400
    if w < 1:
        return jsonify({"error": "w must be >= 1"}), 400

    # Assign global sequence id and timestamp, append to master log
    # message_id = data.get("id")
    # if message_id is None:
    #    return jsonify({"error": "id required"}), 400
    seq_id = next_seq()
    entry = {"id": seq_id, "message": message, "timestamp": time.time()}

    with master_lock:
        # if we want to avoid duplicates in messages
        # if any(e["message"] == message for e in master_log):
        #     return jsonify({"status": "duplicate_skipped"}), 200
        master_log.append(entry)

    app.logger.info(f"Appended to master log id={seq_id}: {message} (w={w})")

    # If w == 1, we don't need any secondary ACKs (master-only write concern).
    # if w == 1:
    #    return jsonify({"status": "ok", "w": w, "entry": entry}), 200

    if w == 1:
        with secondaries_lock:
            targets = dict(secondaries)
        if targets:
            def replicate_bg(entry, targets):
                for sid, url in targets.items():
                    try:
                        replicate_to_secondary(sid, url, entry)
                    except Exception as e:
                        app.logger.warning(f"Background replication to {sid} failed: {e}")
            threading.Thread(target=replicate_bg, args=(entry, targets), daemon=True).start()
        return jsonify({"status": "ok", "w": w, "entry": entry}), 200

    # Determine how many secondary ACKs we need
    with secondaries_lock:
        targets = dict(secondaries)  # copy
    total_nodes = 1 + len(targets)  # master + secondaries
    if w > total_nodes:
        return jsonify({"error": f"w={w} too large for current cluster size {total_nodes}"}), 400

    required_acks = w - 1  # number of secondaries that must ACK

    # Parallel replication to secondaries.
    # We'll submit tasks in parallel and return as soon as required_acks are received (early exit).
    #results = {}
    #ack_count = 0
    #errors = {}

    if len(targets) == 0:
        # No secondaries available
        if required_acks > 0:
            return jsonify({"status": "failed", "reason": "no secondaries available", "required_acks": required_acks}), 500
        else:
            return jsonify({"status": "ok", "w": w, "entry": entry}), 200

    # -------------------------------------------------------------------------
    # Parallel replication with early return once required ACKs are received
    # -------------------------------------------------------------------------
    import concurrent.futures

    ack_count = 0
    results = {}
    errors = {}
    done_sids = set()

    def replicate_and_track(sid, url):
        sid_ret, ok, detail = replicate_to_secondary(sid, url, entry)
        return sid, ok, detail

    # Start replication threads
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(MAX_WORKERS, max(1, len(targets)))
    )
    future_to_sid = {
        executor.submit(replicate_and_track, sid, url): sid for sid, url in targets.items()
    }

    try:
        for fut in concurrent.futures.as_completed(future_to_sid):
            sid = future_to_sid[fut]
            try:
                sid_ret, ok, detail = fut.result()
            except Exception as e:
                ok = False
                detail = {"exception": str(e)}

            results[sid] = {"ack": ok, "detail": detail}

            if ok:
                ack_count += 1
                done_sids.add(sid)
                app.logger.info(f"ACK from {sid} ({ack_count}/{required_acks})")
            else:
                errors[sid] = detail
                app.logger.warning(f"Replication to {sid} failed: {detail}")

            # ✅ Early return once required ACKs reached
            if ack_count >= required_acks:
                app.logger.info(
                    f"Required ACKs ({required_acks}) reached — responding to client"
                )

                # Launch background thread to let remaining replicas finish
                pending = [
                    f for f in future_to_sid if f not in done_sids
                ]

                def background_wait(pending_futs):
                    for f in pending_futs:
                        try:
                            f.result(timeout=REPLICATE_TIMEOUT_SEC)
                        except Exception as e:
                            app.logger.warning(f"Background replication failed: {e}")

                threading.Thread(
                    target=background_wait, args=(pending,), daemon=True
                ).start()

                return jsonify({
                    "status": "ok",
                    "w": w,
                    "entry": entry,
                    "acks_received": ack_count,
                    "results": results
                }), 200

        # ---------------------------------------------------------------------
        # Not enough ACKs within timeout
        # ---------------------------------------------------------------------
        app.logger.error(f"Not enough ACKs ({ack_count}/{required_acks}) before timeout")
        return jsonify({
            "status": "partial_failure",
            "required_acks": required_acks,
            "acks_received": ack_count,
            "results": results,
            "errors": errors
        }), 500

    finally:
        executor.shutdown(wait=False)




    # Success
    return jsonify({"status": "ok", "w": w, "entry": entry, "acks_received": ack_count, "results": results}), 200


@app.route("/", methods=["GET"])
def get_messages():
    """
    Return master's authoritative log in total order.
    """
    with master_lock:
        return jsonify({"messages": list(master_log)}), 200


@app.route("/secondaries/messages", methods=["GET"])
def get_secondary_messages():
    """
    Proxy to all registered secondaries and fetch their messages (for inspection).
    """
    with secondaries_lock:
        targets = dict(secondaries)

    aggregated = {}
    for sid, url in targets.items():
        try:
            resp = requests.get(f"{url.rstrip('/')}/", timeout=REPLICATE_TIMEOUT_SEC)
            if resp.status_code == 200:
                aggregated[sid] = resp.json()
            else:
                aggregated[sid] = {"error": f"status {resp.status_code}", "body": resp.text}
        except Exception as e:
            aggregated[sid] = {"error": str(e)}
    return jsonify(aggregated), 200


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("MASTER_PORT", 5000))
    app.run(host=host, port=port, threaded=True)