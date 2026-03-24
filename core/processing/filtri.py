import re
import json
import unicodedata

# Cache per non leggere il disco a ogni frase
_config_cache = None

def carica_config_filtri():
    global _config_cache
    if _config_cache is None:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                full_config = json.load(f)
                _config_cache = full_config.get("filtri", {
                    "rimuovi_asterischi": True,
                    "rimuovi_parentesi_tonde": True,
                    "rimuovi_parentesi_quadre": False,
                    "sostituzioni_personalizzate": {}
                })
        except Exception as e:
            return {}
    return _config_cache

def reset_cache():
    """Svuota la cache per forzare una ricarica al prossimo utilizzo, utile dopo la modifica da pannello."""
    global _config_cache
    _config_cache = None

def rimuovi_emoji(testo):
    """
    Rimuove le emoji e altri caratteri speciali non supportati dalla sintesi vocale.
    """
    # Filtra i caratteri non stampabili e le emoji
    # Mantiene solo lettere, numeri, punteggiatura base e spazi
    pattern = re.compile(r'[^\x00-\x7F\u00C0-\u017F\s\.,!?;:\'"\(\)\[\]\{\}]')
    testo_pulito = pattern.sub('', testo)
    return testo_pulito

def pulisci_per_voce(testo):
    if not testo:
        return ""

    conf = carica_config_filtri()

    # 0. Rimuovi emoji e caratteri speciali (NUOVO)
    testo = rimuovi_emoji(testo)

    # 1. Sostituzioni personalizzate
    sostituzioni = conf.get("sostituzioni_personalizzate", {})
    for target, sostituto in sostituzioni.items():
        testo = testo.replace(target, sostituto)

    # 2. Rimuove testo tra asterischi
    if conf.get("rimuovi_asterischi", True):
        testo = re.sub(r"\*.*?\*", "", testo)

    # 3. Rimuove testo tra parentesi tonde
    if conf.get("rimuovi_parentesi_tonde", True):
        testo = re.sub(r"\(.*?\)", "", testo)

    # 4. Gestione parentesi quadre
    if conf.get("rimuovi_parentesi_quadre", False):
        testo = re.sub(r"\[.*?\]", "", testo)
    else:
        testo = testo.replace("[", "").replace("]", "")

    # 5. Rimuove markdown (grassetto, corsivo)
    if conf.get("rimuovi_markdown", True):
        testo = re.sub(r'\*\*.*?\*\*', '', testo)
        testo = re.sub(r'__.*?__', '', testo)
        testo = re.sub(r'\*.*?\*', '', testo)

    # 6. Pulizia spazi doppi
    testo = re.sub(r'\s+', ' ', testo).strip()

    return testo