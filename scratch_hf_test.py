import os, requests

key = ""
for line in open("C:\\Hecos\\hecos\\.env"):
    if "HUGGINGFACE_API_KEY_1" in line:
        key = line.split("=", 1)[1].strip()
        break
print(f"HF Key starts with: {key[:5]}... (len: {len(key)})")

models = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "prompthero/openjourney",
    "runwayml/stable-diffusion-v1-5"
]

for m in models:
    url = f"https://api-inference.huggingface.co/models/{m}"
    h = {"Authorization": f"Bearer {key}"}
    r = requests.post(url, headers=h, json={"inputs": "a cat"})
    print(f"{m}: HTTP {r.status_code}")
    if r.status_code != 200:
        print("  ", r.text[:100])
