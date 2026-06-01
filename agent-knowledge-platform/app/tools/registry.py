"""Tool registry: dynamic discovery and management of tools."""

import importlib
import logging
from pathlib import Path
from typing import List, Optional

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for discovering and managing tools.

    Tools are auto-discovered from the app/tools/ directory.
    Any class that extends BaseTool is automatically registered.
    """

    def __init__(self):
        self._tools: dict = {}

    def register(self, tool_instance: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool_instance.name] = tool_instance
        logger.info(f"Registered tool: {tool_instance.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, agent_type: str = None) -> List[BaseTool]:
        """List all registered tools, optionally filtered by agent type."""
        tools = list(self._tools.values())
        if agent_type:
            tools = [t for t in tools if agent_type in getattr(t, "tags", [])]
        return tools

    def get_tools_by_names(self, names: List[str]) -> List[BaseTool]:
        """Get multiple tools by their names."""
        return [self._tools[name] for name in names if name in self._tools]

    def load_from_directory(self, tools_dir: str = None) -> None:
        """Auto-discover and load all tools from the tools directory.

        Scans for Python files containing BaseTool subclasses.
        """
        if tools_dir is None:
            tools_dir = str(Path(__file__).parent)

        tools_path = Path(tools_dir)

        for py_file in sorted(tools_path.glob("*.py")):
            # Skip base files and __init__
            if py_file.name.startswith(("_", "base", "registry")):
                continue

            module_name = f"app.tools.{py_file.stem}"

            try:
                module = importlib.import_module(module_name)

                # Find all BaseTool subclasses in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseTool)
                        and attr is not BaseTool
                    ):
                        try:
                            instance = attr()
                            self.register(instance)
                        except Exception as e:
                            logger.error(f"Failed to instantiate tool {attr_name}: {e}")

            except Exception as e:
                logger.error(f"Failed to load tools from {module_name}: {e}")


# Global registry instance
tool_registry = ToolRegistry()
