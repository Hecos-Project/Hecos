"""
RAG Embedder Worker — subprocess isolato da Hecos.
Gira come processo figlio separato per evitare conflitti tra
onnxruntime e Playwright (Chromium) su Windows.

Protocollo JSON su stdin / stdout:
  [startup]   stdin  <- {"model_name": "BAAI/bge-small-en-v1.5"}
  [ready]     stdout -> {"status": "ready", "dim": 384}
  [request]   stdin  <- {"id": "uuid", "texts": ["testo1", "testo2"]}
  [response]  stdout -> {"id": "uuid", "vectors": [[0.1,...], [0.2,...]]}
  [error]     stdout -> {"id": "uuid", "error": "messaggio"}
"""

import sys
import os
import json

# ── Process title for Task Manager identification ─────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("hecos-rag-embedder")
except Exception:
    pass  # Non-Windows or ctypes unavailable
# ─────────────────────────────────────────────────────────────────────────────

# ── ONNX / Tokenizer thread safety ────────────────────────────────────────────
# Devono essere impostati PRIMA di qualsiasi import di fastembed / onnxruntime.
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
# ──────────────────────────────────────────────────────────────────────────────


def _write(obj: dict):
    """Scrive una risposta JSON su stdout e fa flush immediato."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    # ── 1. Leggi configurazione dalla prima riga di stdin ──────────────────
    try:
        config_line = sys.stdin.readline()
        if not config_line:
            _write({"status": "error", "error": "No config received on stdin"})
            sys.exit(1)
        config = json.loads(config_line.strip())
        model_name = config.get("model_name", "BAAI/bge-small-en-v1.5")
    except Exception as e:
        _write({"status": "error", "error": f"Config parse error: {e}"})
        sys.exit(1)

    # ── 2. Carica fastembed (ONNX model) ───────────────────────────────────
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name=model_name, threads=1)
        # Warm-up: embedding a dummy text forces the ONNX session to fully init.
        _dummy = list(model.embed(["warmup"]))
        dim = len(_dummy[0].tolist()) if _dummy else 384
    except Exception as e:
        _write({"status": "error", "error": f"Model load failed: {e}"})
        sys.exit(1)

    # ── 3. Segnala "pronto" al processo padre ──────────────────────────────
    _write({"status": "ready", "dim": dim})

    # ── 4. Loop principale: leggi richieste, rispondi con vettori ──────────
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        req_id = ""
        try:
            req = json.loads(raw_line)
            req_id = req.get("id", "")
            texts = req.get("texts", [])

            if not texts:
                _write({"id": req_id, "vectors": []})
                continue

            vectors = [v.tolist() for v in model.embed(texts)]
            _write({"id": req_id, "vectors": vectors})

        except json.JSONDecodeError as e:
            _write({"id": req_id, "error": f"JSON parse error: {e}"})
        except Exception as e:
            _write({"id": req_id, "error": str(e)})


if __name__ == "__main__":
    main()
