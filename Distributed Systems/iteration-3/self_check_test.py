import time
import requests
import subprocess
import json

MASTER = "http://localhost:5000"
S1 = "http://localhost:5001"
S2 = "http://localhost:5002"

def wait_until(url, key=None, timeout=60):
    start = time.time()
    while True:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                if key is None:
                    return r.json()
                j = r.json()
                if key in j:
                    return j
        except Exception:
            pass
        if time.time() - start > timeout:
            raise TimeoutError(f"Timeout waiting for {url}")
        time.sleep(0.5)

def print_header(msg):
    print("\n" + "="*80)
    print(msg)
    print("="*80)

def main():
    print_header("1) Waiting for MASTER and S1 to be alive")
    wait_until(f"{MASTER}/health")     # master
    wait_until(f"{S1}/health")         # S1

    print_header("2) Send Msg1 (W=1)")
    r1 = requests.post(MASTER, json={"message": "Msg1", "w": 1})
    print("Response:", r1.status_code, r1.json())

    print_header("3) Send Msg2 (W=2)")
    r2 = requests.post(MASTER, json={"message": "Msg2", "w": 2})
    print("Response:", r2.status_code, r2.json())

    print_header("4) Send Msg3 (W=3)  (expected: WAIT then FAIL because S2 not up yet)")
    r3 = requests.post(MASTER, json={"message": "Msg3", "w": 3})
    print("Response:", r3.status_code, r3.json())

    print_header("5) Send Msg4 (W=1)")
    r4 = requests.post(MASTER, json={"message": "Msg4", "w": 1})
    print("Response:", r4.status_code, r4.json())

    print_header("6) START S2 NOW")
    # start S2 manually, OR uncomment this to auto-start in docker:
    subprocess.Popen(["docker", "compose", "up", "-d", "secondary_slow"])

    print("Waiting for S2 to register with master...")
    wait_until(f"{S2}/health")

    print_header("7) Wait for backfill to complete on S2")
    # wait until S2 shows Msg1..Msg4
    start = time.time()
    expected = ["Msg1", "Msg2", "Msg3", "Msg4"]
    while True:
        try:
            r = requests.get(S2)
            if r.status_code == 200:
                data = r.json()
                msgs = [e["message"] for e in data["messages"]]
                print("S2 messages now:", msgs)
                if msgs == expected:
                    break
        except Exception:
            pass
        if time.time() - start > 120:
            raise TimeoutError("S2 did not catch up")
        time.sleep(1)

    print_header("SUCCESS — S2 has the full ordered log:")
    print(expected)

if __name__ == "__main__":
    main()
