from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str
    tool_use_id: str = None

    def __str__(self):
        id_tag = f" [{self.tool_use_id}]" if self.tool_use_id else ""
        return f"#<Message role={self.role}{id_tag} content={self.content[:61]}...>"

    def __repr__(self):
        return str(self)
