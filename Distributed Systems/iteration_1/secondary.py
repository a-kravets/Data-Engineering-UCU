# secondary.py
import os
import time
import logging
from flask import Flask, request, jsonify
import requests
import socket
import uuid
import threading
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [SECONDARY] %(levelname)s: %(message)s")

secondary_log = []
log_lock = threading.Lock()

MASTER_URL = os.environ.get("MASTER_URL", "http://master:5000")  # master service url inside compose
PORT = int(os.environ.get("SECONDARY_PORT", 5001))
ID = os.environ.get("SECONDARY_ID") or f"secondary-{str(uuid.uuid4())[:8]}"

SECONDARY_ID = socket.gethostname()
SLEEP_SEC = float(os.environ.get("SECONDARY_DELAYS", "0")) #delay_mapping.get(SECONDARY_ID, 0)
app.logger.info(f"Secondary {SECONDARY_ID} starting with delay: {SLEEP_SEC}s")


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

@app.route("/replicate", methods=["POST"])
def replicate():
    """
    Master -> POST /replicate  JSON: {"message": "...", "timestamp": ...}
    Secondary should simulate a delay (SLEEP_SEC) to demonstrate blocking.
    """
    data = request.get_json() or {}
    # simulate delay (to test blocking)
    if SLEEP_SEC > 0:
        app.logger.info(f"Simulating apply delay of {SLEEP_SEC}s")
        print(f"Sleeping for {SLEEP_SEC} seconds")
        time.sleep(SLEEP_SEC)
        print("Done sleeping")

    with log_lock:
        secondary_log.append(data)
    app.logger.info(f"Replicated entry applied: {data}")
    return jsonify({"status": "ack"}), 200

@app.route("/", methods=["GET"])
def get_messages():
    with log_lock:
        return jsonify({"messages": list(secondary_log)}), 200

def start_registration_background():
    # Try registering a few times (in case master not yet ready)
    def try_register():
        attempts = 0
        while attempts < 20:
            try:
                register_with_master()
                return
            except Exception:
                attempts += 1
                time.sleep(1)
    t = threading.Thread(target=try_register, daemon=True)
    t.start()

if __name__ == "__main__":
    # Register with master asynchronously (so we can start even if master is slightly slow)
    start_registration_background()
    app.run(host="0.0.0.0", port=PORT)
