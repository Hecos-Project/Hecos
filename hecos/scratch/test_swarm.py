import requests, json, sys

BASE = "http://localhost:7801"

try:
    s = requests.post(f"{BASE}/API/GetNewSession", json={}, timeout=5)
    sid = s.json().get("session_id", "")
    print("Session:", sid[:20] + "..." if sid else "NONE")
except Exception as e:
    print("Cannot connect:", e); sys.exit(1)

# Raw ListModels response
for label, payload in [
    ("default", {"session_id": sid, "path": "", "depth": 2}),
    ("LoRA",    {"session_id": sid, "path": "", "depth": 2, "subtype": "LoRA"}),
]:
    r = requests.post(f"{BASE}/API/ListModels", json=payload, timeout=10)
    data = r.json()
    files = data.get("files", [])
    print(f"\n=== {label} ({len(files)} items) ===")
    for f in files[:5]:
        print(json.dumps(f, indent=2))
    if not files:
        print("(empty) — all keys:", list(data.keys()))
