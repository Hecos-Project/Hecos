import abc

class BaseLegacyPlugin(abc.ABC):
    """
    Base class for Legacy plugins (text-tag based).
    Each legacy plugin must inherit from this class and implement
    the process_tag() and get_commands() methods.
    """
    
    def __init__(self, tag: str, description: str):
        self.tag = tag.upper()
        self.description = description

    @abc.abstractmethod
    def process_tag(self, command: str) -> str:
        """
        Executes the action associated with the text command (e.g., 'open:calc').
        Returns a response string on the outcome.
        """
        pass

    @abc.abstractmethod
    def get_commands(self) -> dict:
        """
        Returns a dictionary { "example_command": "explanation" }
        to populate the LLM system prompt.
        """
        pass

    def info(self) -> dict:
        """
        Returns standardized information for the registry.
        """
        return {
            "tag": self.tag,
            "desc": self.description,
            "commands": self.get_commands(),
            "is_legacy": True
        }

    def status(self) -> str:
        return "ONLINE"
