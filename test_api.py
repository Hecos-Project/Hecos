import requests
import json
import sys

with open("test_api_out_utf8.txt", "w", encoding="utf-8") as f:
    def test_pollinations():
        try:
            url = 'https://image.pollinations.ai/prompt/cat?width=1024&height=1024&nologo=true'
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=15)
            f.write(f"Pollinations Status: {r.status_code}\n")
            if r.status_code != 200:
                f.write(f"Pollinations Body: {r.text[:500]}\n")
        except Exception as e:
            f.write(f"Pollinations Error: {e}\n")

    def test_groq():
        try:
            key = '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'
            url = 'https://api.groq.com/openai/v1/models'
            r = requests.get(url, headers={'Authorization': f'Bearer {key}'}, timeout=15)
            f.write(f"Groq Status: {r.status_code}\n")
            if r.status_code != 200:
                f.write(f"Groq Body: {r.text[:500]}\n")
        except Exception as e:
            f.write(f"Groq Error: {e}\n")

    test_pollinations()
    test_groq()
