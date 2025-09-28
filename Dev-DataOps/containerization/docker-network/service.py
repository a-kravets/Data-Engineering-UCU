from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)

# in-memory store
store = []

PEER_URL = os.getenv("PEER_URL")      # e.g. "http://service_b:8000"

@app.route("/data", methods=["POST"])
def receive():
    data = request.get_json(force=True)
    store.append(data)
    return jsonify({"stored": data, "total_items": len(store)}), 201

@app.route("/data", methods=["GET"])
def list_data():
    return jsonify(store)

@app.route("/send", methods=["POST"])
def send():
    if not PEER_URL:
        return {"error": "PEER_URL not set"}, 400
    payload = request.get_json(silent=True) or {"msg": "hello from sender"}
    r = requests.post(f"{PEER_URL}/data", json=payload)
    return jsonify({"sent": payload, "peer_status": r.status_code, "peer_reply": r.json()})

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
