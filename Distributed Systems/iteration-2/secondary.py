# secondary.py
import os
import time
import logging
from flask import Flask, request, jsonify
import requests
import socket
import uuid
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [SECONDARY] %(levelname)s: %(message)s")

# In-memory storage:
# - map of id -> message (for dedup)
secondary_by_id = {}
# - ordered list of entries for returning in total order
secondary_log = []
log_lock = threading.Lock()

MASTER_URL = os.environ.get("MASTER_URL", "http://master:5000")  # master service url inside compose
PORT = int(os.environ.get("SECONDARY_PORT", 5001))
# Secondary ID precedence: env SECONDARY_ID -> hostname -> generated uuid
ID = os.environ.get("SECONDARY_ID") or socket.gethostname() or f"secondary-{str(uuid.uuid4())[:8]}"

# Delay (seconds) applied when replicating (to emulate lag)
# Use env SECONDARY_DELAY (single numeric value)
try:
    SLEEP_SEC = float(os.environ.get("SECONDARY_DELAY", "0"))
except Exception:
    SLEEP_SEC = 0.0

app.logger.info(f"Secondary {ID} starting with delay: {SLEEP_SEC}s")

def get_local_ip():
    # Works inside docker: returns container's IP on the app network
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"

def register_with_master():
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"
    payload = {"id": ID, "url": url}
    try:
        r = requests.post(f"{MASTER_URL.rstrip('/')}/register", json=payload, timeout=5)
        if r.status_code == 200:
            app.logger.info(f"Successfully registered with master: {payload}")
        else:
            app.logger.error(f"Failed to register with master: {r.status_code} {r.text}")
    except Exception as e:
        app.logger.exception(f"Exception when registering with master: {e}")
        raise

@app.route("/replicate", methods=["POST"])
def replicate():
    """
    Master -> POST /replicate  JSON: {"id": <seq>, "message": "...", "timestamp": ...}
    Secondary simulates delay SLEEP_SEC to emulate lagging replicas.
    Deduplicates by id and maintains total ordering by id.
    """
    data = request.get_json() or {}
    msg_id = data.get("id")
    message = data.get("message")
    timestamp = data.get("timestamp", None)

    if msg_id is None or message is None:
        return jsonify({"error": "invalid entry, id and message required"}), 400

    # Simulate apply delay (emulate lag)
    if SLEEP_SEC > 0:
        app.logger.info(f"[{ID}] Simulating apply delay of {SLEEP_SEC}s for id={msg_id}")
        time.sleep(SLEEP_SEC)

    with log_lock:
        if msg_id in secondary_by_id:
            app.logger.info(f"[{ID}] Duplicate id={msg_id} ignored")
        else:
            # Store by id for dedup, and append to log, then keep log sorted by id (total ordering)
            secondary_by_id[msg_id] = {"id": msg_id, "message": message, "timestamp": timestamp}
            secondary_log.append(secondary_by_id[msg_id])
            # Keep list sorted by id (since master assigns increasing ids)
            secondary_log.sort(key=lambda e: e["id"])
            app.logger.info(f"[{ID}] Applied id={msg_id}: {message}")

    return jsonify({"status": "ack", "id": msg_id}), 200


@app.route("/", methods=["GET"])
def get_messages():
    with log_lock:
        # Return the ordered list
        return jsonify({"messages": list(secondary_log)}), 200


def start_registration_background():
    # Try registering a few times (in case master not yet ready)
    def try_register():
        attempts = 0
        while True:
            try:
                register_with_master()
                return
            except Exception:
                attempts += 1
                wait = min(2 ** attempts, 30)
                app.logger.warning(f"[{ID}] Registration attempt {attempts} failed, retrying in {wait}s...")
                time.sleep(wait)
    t = threading.Thread(target=try_register, daemon=True)
    t.start()


if __name__ == "__main__":
    # Start registration background thread
    start_registration_background()
    app.run(host="0.0.0.0", port=PORT)
