import subprocess
import os
import winsound
import json
import time
import keyboard 

sta_parlando = False

def parla(testo):
    global sta_parlando
    if not testo: return
    
    # 1. Caricamento configurazione completa
    try:
        with open('config.json', 'r') as f:
            full_conf = json.load(f)
            c = full_conf.get('voce', {})
            
            # Mappatura parametri Piper
            # Invertiamo la velocità: UI 2.0 (veloce) -> Piper 0.5 (durata dimezzata)
            length_scale = 1.0 / max(0.1, c.get('speed', 1.0))
            # Noise Scale (0.0 - 1.0): Controlla la variabilità dell'intonazione
            noise_scale = c.get('noise_scale', 0.667)
            # Noise W (0.0 - 1.0): Controlla la stabilità dei fonemi
            noise_w = c.get('noise_w', 0.8)
            # Sentence Silence: Secondi di pausa tra i punti fermi
            sentence_silence = c.get('sentence_silence', 0.2)
            
    except Exception as e:
        print(f"[VOICE] Configuration error: {e}")
        length_scale, noise_scale, noise_w, sentence_silence = 1.0, 0.667, 0.8, 0.2

    sta_parlando = True
    
    try:
        # Recupera di nuovo o usa la config precedente
        with open('config.json', 'r') as f:
            c_voce = json.load(f).get('voce', {})
    except Exception:
        c_voce = {}
        
    try:
        testo_pulito = testo.replace('"', '').replace('\n', ' ')
        piper_path = c_voce.get('piper_path', r"C:\piper\piper.exe")
        model_path = c_voce.get('modello_onnx', r"C:\piper\en_US-lessac-medium.onnx")
        
        # 2. Comando completo con tutti i flag possibili
        comando = [
            piper_path, "-m", model_path,
            "--length_scale", str(length_scale),
            "--noise_scale", str(noise_scale),
            "--noise_w", str(noise_w),
            "--sentence_silence", str(sentence_silence),
            "-f", "risposta.wav"
        ]
        
        proc = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        proc.communicate(input=testo_pulito)
        
        if os.path.exists("risposta.wav"):
            winsound.PlaySound("risposta.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
            
            # Calcolo durata dinamica basato sulla velocità reale
            durata_stimata = (len(testo_pulito) / 15) * length_scale + sentence_silence
            inizio = time.time()

            while (time.time() - inizio) < durata_stimata:
                if keyboard.is_pressed('esc'):
                    ferma_voce()
                    break
                time.sleep(0.05)
                
    except Exception as e:
        print(f"[VOICE] Piper execution error: {e}")
    finally:
        sta_parlando = False

def ferma_voce():
    global sta_parlando
    winsound.PlaySound(None, winsound.SND_PURGE)
    sta_parlando = False