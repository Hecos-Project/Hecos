"""Modulo principale del plugin Sistema."""
import sys
import subprocess
import os

import winsound
import time
import re
import datetime
import json
from core import logger

def info():
    """Manifest del plugin."""
    return {
        "tag": "SISTEMA",
        "desc": "Accesso Root: gestione terminale, reboot, diagnostica log, utilità di sistema.",
        "comandi": {
            "help": "Mostra i protocolli di sistema.",
            "riavvia": "Cold Reboot immediato del core.",
            "cmd:istruzione": "Esegue un comando shell (es: cmd:dir).",
            "terminale": "Apre una nuova finestra Prompt CMD.",
            "leggi log": "Legge gli ultimi eventi registrati nel sistema.",
            "errori": "Analizza solo gli ultimi crash o fallimenti.",
            "ora": "Restituisce l'ora corrente.",
            "apri:programma": "Apre un programma predefinito (notepad, chrome, visual studio, sillytavern).",
            "esplora:percorso": "Apre una cartella in Explorer (es. esplora:desktop, esplora:download).",
            "config:set:sezione,chiave,valore": "Aggiorna una voce del file config.json (uso attento)."
        },
        "esempio": "[SISTEMA: leggi log] o [SISTEMA: terminale] o [SISTEMA: ora]"
    }

def status():
    return "ONLINE (Shell & BlackBox Access Active)"

def esegui(comando):
    """Esegue comandi shell o gestisce il ciclo vitale di Aura."""
    logger.debug("PLUGIN_SISTEMA", f"esegui() chiamato con comando: '{comando}'")
    
    cmd_originale = comando.strip()
    cmd = cmd_originale.lower()

    # --- 0. ORA ---
    if cmd == "ora":
        logger.debug("PLUGIN_SISTEMA", "Esecuzione comando 'ora'")
        ora = datetime.datetime.now().strftime("%H e %M")
        return f"Sono le ore {ora}."

    # --- 1. PROTOCOLLO RIAVVIO ---
    if any(x in cmd for x in ["riavvia", "reboot", "restart"]):
        logger.info("Inizializzazione Cold Reboot richiesta dall'Admin.")
        logger.debug("PLUGIN_SISTEMA", "Esecuzione reboot")
        print(f"\n\033[91m[SISTEMA] REBOOT IN CORSO. Bye Admin.\033[0m")
        sys.stdout.flush() 
        winsound.Beep(600, 150)
        winsound.Beep(400, 150)
        os._exit(0)
        return "Riavvio in corso..."

    # --- 2. LETTURA LOG E ERRORI ---
    if "log" in cmd or "errori" in cmd or "registro" in cmd:
        solo_err = "errori" in cmd or "crash" in cmd
        tipo = "degli ERRORI" if solo_err else "degli ultimi EVENTI"
        logger.info(f"Accesso al registro log: {tipo}")
        logger.debug("PLUGIN_SISTEMA", f"Lettura log, solo errori: {solo_err}")
        
        risultato_log = logger.leggi_log(n=8, solo_errori=solo_err)
        return f"Analisi {tipo} completata:\n{risultato_log}"

    # --- 3. APERTURA TERMINALE ESTERNO ---
    trigger_terminale = ["terminale", "console", "prompt", "apri cmd", "cmd"]
    if cmd == "cmd" or any(x in cmd for x in trigger_terminale):
        try:
            logger.info("Apertura istanza CMD esterna indipendente.")
            logger.debug("PLUGIN_SISTEMA", "Apertura terminale")
            subprocess.Popen("start cmd.exe", shell=True)
            return "Prompt dei comandi aperto in una nuova finestra, Admin."
        except Exception as e:
            logger.errore(f"Fallimento apertura terminale: {e}")
            logger.debug("PLUGIN_SISTEMA", f"Errore apertura terminale: {e}")
            return f"Errore critico apertura terminale: {e}"
        
    # --- 4. APRI PROGRAMMA ---
    if cmd.startswith("apri:"):
        prog = cmd_originale[5:].strip().lower()
        logger.debug("PLUGIN_SISTEMA", f"Apertura programma: {prog}")
        
        programmi = {
            "notepad": "notepad.exe",
            "chrome": "chrome.exe",
            "visual studio": r"C:\Program Files\Microsoft VS Code\Code.exe",
            "sillytavern": r"C:\SillyTavern\SillyTavern\Start.bat"
        }
        if prog in programmi:
            try:
                os.startfile(programmi[prog])
                logger.debug("PLUGIN_SISTEMA", f"Programma {prog} avviato")
                return f"Avvio {prog} in corso."
            except Exception as e:
                logger.errore(f"SISTEMA: errore apertura {prog}: {e}")
                logger.debug("PLUGIN_SISTEMA", f"Errore apertura {prog}: {e}")
                return f"Errore apertura {prog}: {e}"
        else:
            # Se non è nella lista, prova a interpretarlo come comando diretto
            try:
                os.startfile(prog + ".exe")
                logger.debug("PLUGIN_SISTEMA", f"Tentativo apertura diretto: {prog}.exe")
                return f"Avvio {prog} in corso."
            except:
                logger.debug("PLUGIN_SISTEMA", f"Programma {prog} non riconosciuto")
                return f"Programma '{prog}' non riconosciuto o non installato."

    # --- 5. ESPLORA CARTELLA ---
    if cmd.startswith("esplora:"):
        percorso = cmd_originale[8:].strip()
        logger.debug("PLUGIN_SISTEMA", f"Apertura cartella: {percorso}")
        
        mappa = {
            "desktop": os.path.expanduser("~\\Desktop"),
            "download": os.path.expanduser("~\\Downloads"),
            "documenti": os.path.expanduser("~\\Documents"),
            "core": os.path.join(os.getcwd(), "core"),
            "plugins": os.path.join(os.getcwd(), "plugins"),
            "memoria": os.path.join(os.getcwd(), "memoria"),
            "personalita": os.path.join(os.getcwd(), "personalita"),
            "logs": os.path.join(os.getcwd(), "logs")
        }
        path = mappa.get(percorso, percorso)
        if os.path.exists(path):
            os.startfile(path)
            logger.debug("PLUGIN_SISTEMA", f"Cartella {percorso} aperta")
            return f"Cartella {percorso} aperta in Explorer."
        else:
            logger.debug("PLUGIN_SISTEMA", f"Percorso {percorso} non trovato")
            return f"Percorso {percorso} non trovato."

    # --- 6. CONFIG: SET ---
    if cmd.startswith("config:set:"):
        args = cmd_originale[11:].strip().split(',')
        if len(args) == 3:
            sezione, chiave, valore = [x.strip() for x in args]
            logger.debug("PLUGIN_SISTEMA", f"Modifica config: {sezione}.{chiave} = {valore}")
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if sezione in data and chiave in data[sezione]:
                    vecchio = data[sezione][chiave]
                    if isinstance(vecchio, bool):
                        valore = valore.lower() in ('true', '1', 'yes')
                    elif isinstance(vecchio, int):
                        valore = int(valore)
                    elif isinstance(vecchio, float):
                        valore = float(valore)
                    data[sezione][chiave] = valore
                    with open('config.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    logger.debug("PLUGIN_SISTEMA", "Config aggiornato")
                    return f"Config aggiornato: {sezione}.{chiave} = {valore}"
                else:
                    logger.debug("PLUGIN_SISTEMA", f"Sezione o chiave non trovata")
                    return f"Sezione o chiave non trovata in config.json."
            except Exception as e:
                logger.debug("PLUGIN_SISTEMA", f"Errore aggiornamento config: {e}")
                return f"Errore aggiornamento config: {e}"
        else:
            return "Sintassi: config:set:sezione,chiave,valore"

    # --- 7. ESECUZIONE COMANDI SHELL (cmd:) ---
    if cmd.startswith("cmd:"):
        shell_cmd = cmd_originale[4:].strip()
        logger.debug("PLUGIN_SISTEMA", f"Comando shell: {shell_cmd}")
    else:
        shell_cmd = re.sub(r"^(comando_reale|sistema|cmd|esegui|shell)[:\s]+", "", cmd_originale, flags=re.IGNORECASE).strip()
        logger.debug("PLUGIN_SISTEMA", f"Comando shell (pulito): {shell_cmd}")

    if not shell_cmd or shell_cmd.lower() == "help":
        logger.debug("PLUGIN_SISTEMA", "Nessun comando valido, restituisco help")
        return "SISTEMA: Protocolli attivi. Usa 'leggi log', 'terminale', 'riavvia' o 'cmd:istruzione'."

    try:
        logger.info(f"Esecuzione comando shell: {shell_cmd}")
        logger.debug("PLUGIN_SISTEMA", f"Esecuzione subprocess: {shell_cmd}")
        output = subprocess.check_output(shell_cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=15)
        logger.debug("PLUGIN_SISTEMA", f"Output ricevuto: {len(output)} caratteri")
        return output if output.strip() else f"Comando eseguito con successo: {shell_cmd}"
    except subprocess.CalledProcessError as e:
        msg_err = f"Errore Shell: {e.output}"
        logger.errore(msg_err)
        logger.debug("PLUGIN_SISTEMA", f"Errore subprocess: {e}")
        return msg_err
    except Exception as e:
        logger.errore(f"Errore imprevisto shell: {e}")
        logger.debug("PLUGIN_SISTEMA", f"Eccezione: {e}")
        return f"Errore: {str(e)}"