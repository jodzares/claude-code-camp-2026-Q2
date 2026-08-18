from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    block: callable

    def __str__(self):
        return f"#<Tool name={self.name} description={self.description[:41]} params={list(self.parameters.keys())}>"

    def __repr__(self):
        return str(self)
