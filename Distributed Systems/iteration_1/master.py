# master.py
import os
import time
import logging
from flask import Flask, request, jsonify
import requests
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [MASTER] %(levelname)s: %(message)s")

# In-memory log at master
master_log = []

# Registered secondaries: list of dicts {"id": id, "url": "http://ip:port"}
secondaries = {}
secondaries_lock = threading.Lock()

# Configs
REPLICATE_TIMEOUT_SEC = float(os.environ.get("REPLICATE_TIMEOUT_SEC", "0"))

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
    return jsonify({"status": "registered"}), 200

'''
@app.route("/unregister", methods=["POST"])
def unregister_secondary():
    data = request.get_json() or {}
    sid = data.get("id")
    if not sid:
        return jsonify({"error": "id required"}), 400
    with secondaries_lock:
        secondaries.pop(sid, None)
    app.logger.info(f"Unregistered secondary {sid}")
    return jsonify({"status": "unregistered"}), 200
'''
    
@app.route("/append", methods=["POST"])
def append_message():
    """
    Client -> POST /append  JSON: {"message": "..."}
    Master appends to master_log, then replicates to all known secondaries.
    It waits for ACKs from all secondaries (blocking replication).
    """
    data = request.get_json() or {}
    message = data.get("message")
    if message is None:
        return jsonify({"error": "message required"}), 400

    entry = {"message": message, "timestamp": time.time()}
    master_log.append(entry)
    app.logger.info(f"Appended to master log: {entry}")

    # Copy current secondaries
    with secondaries_lock:
        targets = dict(secondaries)

    # Replicate to each secondary, blocking until ACK or timeout
    results = {}
    for sid, url in targets.items():
        replicate_url = f"{url.rstrip('/')}/replicate"
        try:
            app.logger.info(f"Replicating to {sid} at {replicate_url}")
            r = requests.post(replicate_url, json=entry, timeout=REPLICATE_TIMEOUT_SEC)
            if r.status_code == 200:
                results[sid] = {"status": "ack"}
                app.logger.info(f"Received ACK from {sid}")
            else:
                results[sid] = {"status": "error", "code": r.status_code, "body": r.text}
                app.logger.error(f"Non-200 from {sid}: {r.status_code} {r.text}")
                # For this exercise (perfect link), we consider this a failure but proceed.
        except requests.RequestException as e:
            results[sid] = {"status": "error", "error": str(e)}
            app.logger.error(f"Failed to replicate to {sid}: {e}")
            # In real system, we'd retry or mark it down.

    # Blocking semantics: only return success when all acked.
    not_acked = [s for s, res in results.items() if res.get("status") != "ack"]
    if not_acked:
        return jsonify({"status": "partial_failure", "failed": not_acked, "details": results}), 500

    return jsonify({"status": "ok", "replicated_to": list(results.keys())}), 200

@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify({"messages": master_log}), 200

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("MASTER_PORT", 5000))
    app.run(host=host, port=port)
