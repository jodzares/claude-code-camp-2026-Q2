from .tool import Tool
from .errors import UnknownToolError


class Registry:
    def __init__(self, context):
        self.context = context

    def tool(self, name, description, parameters=None):
        def decorator(fn):
            t = Tool(name, description, parameters or {}, fn)
            self.context.register_tool(t)
            return fn
        return decorator

    def dispatch(self, name, args=None):
        tool = self.context.tools.get(name)
        if tool is None:
            raise UnknownToolError(f"No tool registered as '{name}'")
        # Ruby converts string keys to symbol keys here (`transform_keys(&:to_sym)`)
        # because its block syntax only accepts symbol keyword args. Python dict
        # keys are always strings already, so no conversion is needed.
        return tool.block(**(args or {}))
