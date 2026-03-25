import abc

class BaseLegacyPlugin(abc.ABC):
    """
    Classe base per i plugin Legacy (basati su Tag testuali).
    Ogni plugin legacy deve ereditare da questa classe e implementare
    il metodo elabora_tag().
    """
    
    def __init__(self, tag: str, descrizione: str):
        self.tag = tag.upper()
        self.descrizione = descrizione

    @abc.abstractmethod
    def elabora_tag(self, comando: str) -> str:
        """
        Esegue l'azione associata al comando testuale (es. 'apri:calc').
        Ritorna una stringa di risposta sull'esito.
        """
        pass

    @abc.abstractmethod
    def ottieni_comandi(self) -> dict:
        """
        Ritorna un dizionario { "comando_esempio": "spiegazione" }
        per popolare il prompt di sistema del LLM.
        """
        pass

    def info(self) -> dict:
        """
        Ritorna le informazioni standardizzate per il registro.
        """
        return {
            "tag": self.tag,
            "desc": self.descrizione,
            "comandi": self.ottieni_comandi(),
            "is_legacy": True
        }

    def status(self) -> str:
        return "ONLINE"
