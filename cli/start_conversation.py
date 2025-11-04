"""Interactive AI-to-AI Conversation Starter v5.0 - ASYNC EDITION with CLI Support"""

import argparse
import asyncio
import sys
from typing import Optional, Tuple

from agents import (
    create_agent,
    detect_configured_agents,
    get_agent_info,
    list_available_agents,
)
from core.common import setup_logging
from core.config import config
from core.metrics import (
    decrement_conversations,
    increment_conversations,
    start_metrics_server,
)
from core.queue import create_queue
from core.tracing import setup_tracing


class ConversationStarter:
    """Interactive conversation starter with async support and CLI flags"""

    def __init__(self, args: Optional[argparse.Namespace] = None):
        self.available_agents = detect_configured_agents()
        self.conversation_file = (
            args.db if args and args.db else config.DEFAULT_CONVERSATION_FILE
        )
        self.args = args

    def _print_banner(self):
        print("=" * 80)
        print("AI-TO-AI CONVERSATION PLATFORM v5.0")
        print("=" * 80)
        print()

    def _check_configuration(self) -> bool:
        if not self.available_agents:
            print("No AI agents configured!")
            print("\nAdd API keys to .env file:")
            print("  ANTHROPIC_API_KEY=your_key")
            print("  OPENAI_API_KEY=your_key")
            print("  GOOGLE_API_KEY=your_key")
            print("  XAI_API_KEY=your_key")
            print("  PERPLEXITY_API_KEY=your_key")
            return False

        if len(self.available_agents) < 2 and not (
            self.args and self.args.agent1 and self.args.agent2
        ):
            print(f"Only {len(self.available_agents)} agent configured")

        return True

    def _show_available_agents(self):
        print("AVAILABLE AGENTS:")
        print("-" * 80)

        for agent_type in sorted(self.available_agents):
            info = get_agent_info(agent_type)
            agent_class = info["class"]
            print(f"  {agent_class.PROVIDER_NAME} ({agent_type})")

        print()

        unavailable = set(list_available_agents()) - set(self.available_agents)
        if unavailable:
            print("UNAVAILABLE AGENTS:")
            print("-" * 80)
            for agent_type in sorted(unavailable):
                info = get_agent_info(agent_type)
                print(f"  {info['class'].PROVIDER_NAME} - Set {info['env_key']}")
            print()

    def _select_agent(
        self, position: str, cli_agent: Optional[str] = None
    ) -> Tuple[str, str]:
        """Select agent interactively or from CLI"""

        # If CLI argument provided, use it
        if cli_agent:
            agent_type = cli_agent.lower()
            if agent_type not in self.available_agents:
                print(f"{position} agent '{cli_agent}' is not configured.")
                sys.exit(1)
            return agent_type, None

        print(f"\nSelect {position} agent:")
        for i, a in enumerate(sorted(self.available_agents), 1):
            print(f"{i}. {a}")

        while True:
            choice = input("Enter number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(self.available_agents):
                selected = sorted(self.available_agents)[int(choice) - 1]
                return selected, None
            print("Invalid choice. Try again.")

    def _get_topic(self) -> str:
        if self.args and self.args.topic:
            return self.args.topic
        return (
            input("\nConversation topic (or press Enter for general): ").strip()
            or "general"
        )

    def _get_max_turns(self) -> int:
        if self.args and self.args.turns:
            return self.args.turns
        while True:
            turns = input("\nMaximum turns per agent (default 50): ").strip()
            if not turns:
                return 50
            if turns.isdigit() and int(turns) > 0:
                return int(turns)
            print("Please enter a positive integer.")

    def _print_summary(
        self,
        agent1_type: str,
        agent1_model: Optional[str],
        agent2_type: str,
        agent2_model: Optional[str],
        topic: str,
        max_turns: int,
    ):
        print("\n" + "=" * 80)
        print("CONVERSATION SETTINGS")
        print("=" * 80)
        print(f"Agent 1 : {agent1_type.upper()} ({agent1_model or 'default'})")
        print(f"Agent 2 : {agent2_type.upper()} ({agent2_model or 'default'})")
        print(f"Topic   : {topic}")
        print(f"Turns   : {max_turns}")
        print(f"DB file : {self.conversation_file}")
        print("=" * 80)

    async def run_conversation(
        self,
        agent1_type: str,
        agent1_model: Optional[str],
        agent2_type: str,
        agent2_model: Optional[str],
        topic: str,
        max_turns: int,
    ):
        logger = setup_logging()
        queue = create_queue(self.conversation_file, logger)

        agent1 = create_agent(
            agent_type=agent1_type,
            queue=queue,
            logger=logger,
            model=agent1_model,
            topic=topic,
            timeout=config.DEFAULT_TIMEOUT_MINUTES,
        )
        agent2 = create_agent(
            agent_type=agent2_type,
            queue=queue,
            logger=logger,
            model=agent2_model,
            topic=topic,
            timeout=config.DEFAULT_TIMEOUT_MINUTES,
        )

        increment_conversations()
        try:
            await asyncio.gather(
                agent1.run(max_turns=max_turns, partner_name=agent2.agent_name),
                agent2.run(max_turns=max_turns, partner_name=agent1.agent_name),
            )
        finally:
            decrement_conversations()

    async def run_interactive(self):
        self._print_banner()
        if not self._check_configuration():
            return

        self._show_available_agents()

        agent1_type, agent1_model = self._select_agent(
            "first", self.args.agent1 if self.args else None
        )
        agent2_type, agent2_model = self._select_agent(
            "second", self.args.agent2 if self.args else None
        )

        # Override models if provided via CLI
        if self.args and self.args.model1:
            agent1_model = self.args.model1
        if self.args and self.args.model2:
            agent2_model = self.args.model2

        if agent1_type == agent2_type and not (self.args and self.args.yes):
            print(f"\nBoth agents are {agent1_type}")
            response = input("Continue? (Y/n): ")
            if response.lower() == "n":
                return

        topic = self._get_topic()
        max_turns = self._get_max_turns()

        self._print_summary(
            agent1_type, agent1_model, agent2_type, agent2_model, topic, max_turns
        )

        if not (self.args and self.args.yes):
            response = input("\nStart conversation? (Y/n): ")
            if response.lower() == "n":
                return

        await self.run_conversation(
            agent1_type, agent1_model, agent2_type, agent2_model, topic, max_turns
        )


async def async_main(args: Optional[argparse.Namespace] = None):
    """Async main entry point"""
    start_metrics_server(config.PROMETHEUS_PORT)
    setup_tracing()

    starter = ConversationStarter(args)
    await starter.run_interactive()


def main():
    """Main entry point with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="AI-to-AI Conversation Platform v5.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  aic-start
  
  # Specify agents and auto-confirm
  aic-start --agent1 claude --agent2 chatgpt --yes
  
  # Full configuration via CLI
  aic-start --agent1 claude --model1 claude-sonnet-4-5-20250929 \\
            --agent2 chatgpt --model2 gpt-4o \\
            --topic "AI ethics" --turns 20 --yes
  
  # Custom database location
  aic-start --db ./conversations/my_chat.db
        """,
    )

    parser.add_argument(
        "--agent1",
        type=str,
        help="First agent (claude, chatgpt, gemini, grok, perplexity)",
    )
    parser.add_argument("--agent2", type=str, help="Second agent")
    parser.add_argument("--model1", type=str, help="Model for first agent")
    parser.add_argument("--model2", type=str, help="Model for second agent")
    parser.add_argument("--topic", type=str, help="Conversation topic")
    parser.add_argument("--turns", type=int, help="Maximum number of turns")
    parser.add_argument("--db", type=str, help="Database file path")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Auto-confirm all prompts"
    )

    args = parser.parse_args()

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
