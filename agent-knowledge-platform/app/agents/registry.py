"""Agent registry: dynamic loading and management of agents."""

import importlib
import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Dynamic agent registry that loads agents from YAML config files.

    Usage:
        registry = AgentRegistry()
        registry.load_from_directory("./agents_config")
        agent = registry.get("code_agent")
    """

    def __init__(self):
        self._agents: dict = {}

    def register(self, name: str, agent_class: type, config: dict) -> None:
        """Register an agent class with its configuration."""
        self._agents[name] = {
            "class": agent_class,
            "config": config,
            "instance": None,
        }
        logger.info(f"Registered agent: {name}")

    def get(self, name: str):
        """Get an agent instance by name (lazy initialization).

        Args:
            name: Agent name (e.g., 'code_agent')

        Returns:
            Agent instance or None if not found
        """
        entry = self._agents.get(name)
        if not entry:
            logger.warning(f"Agent '{name}' not found, falling back to general_agent")
            entry = self._agents.get("general_agent")
            if not entry:
                return None

        # Lazy instantiation
        if entry["instance"] is None:
            try:
                entry["instance"] = entry["class"](
                    llm=None,  # LLM is injected at runtime
                    tools=entry["config"].get("tools", []),
                    config=entry["config"],
                )
            except Exception as e:
                logger.error(f"Failed to instantiate agent '{name}': {e}")
                return None

        return entry["instance"]

    def list_agents(self) -> list:
        """List all registered agent names and their configs."""
        return [
            {
                "name": name,
                "display_name": entry["config"].get("display_name", name),
                "description": entry["config"].get("description", ""),
                "tools": entry["config"].get("tools", []),
            }
            for name, entry in self._agents.items()
        ]

    def load_from_directory(self, config_dir: str) -> None:
        """Load all agent configurations from a directory of YAML files.

        Each YAML file should contain:
            name: agent_name
            display_name: Human-readable name
            description: Agent description
            module: app.agents.code_agent
            class: CodeAgent
            llm_provider: deepseek
            llm_model: deepseek-chat
            system_prompt: |
                Your system prompt here...
            tools:
                - search_knowledge
                - run_code
        """
        config_path = Path(config_dir)
        if not config_path.exists():
            logger.warning(f"Agent config directory not found: {config_dir}")
            return

        for yaml_file in sorted(config_path.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                if not config or "name" not in config:
                    logger.warning(f"Skipping invalid config: {yaml_file}")
                    continue

                # Dynamic import of agent class
                module_path = config.get("module")
                class_name = config.get("class")

                if module_path and class_name:
                    module = importlib.import_module(module_path)
                    agent_class = getattr(module, class_name)
                    self.register(config["name"], agent_class, config)
                else:
                    # Register config-only agent (uses default LLM chain)
                    self.register(config["name"], None, config)
                    logger.info(f"Registered config-only agent: {config['name']}")

            except Exception as e:
                logger.error(f"Failed to load agent config {yaml_file}: {e}")


# Global registry instance
agent_registry = AgentRegistry()
