"""Interactive AI-to-AI Conversation Starter v5.0 - ASYNC EDITION with CLI Support"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Tuple, Optional

from agents import create_agent, detect_configured_agents, get_agent_info, list_available_agents
from core.config import config
from core.common import setup_logging
from core.queue import create_queue
from core.metrics import start_metrics_server, increment_conversations, decrement_conversations
from core.tracing import setup_tracing


class ConversationStarter:
    """Interactive conversation starter with async support and CLI flags"""

    def __init__(self, args: Optional[argparse.Namespace] = None):
        self.available_agents = detect_configured_agents()
        self.conversation_file = args.db if args and args.db else config.DEFAULT_CONVERSATION_FILE
        self.args = args

    def _print_banner(self):
        print("=" * 80)
        print("AI-TO-AI CONVERSATION PLATFORM v5.0")
        print("=" * 80)
        print()

    def _check_configuration(self) -> bool:
        if not self.available_agents:
            print("❌ No AI agents configured!")
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
            print(f"⚠️  Only {len(self.available_agents)} agent configured")

        return True

    def _show_available_agents(self):
        print("AVAILABLE AGENTS:")
        print("-" * 80)

        for agent_type in sorted(self.available_agents):
            info = get_agent_info(agent_type)
            agent_class = info["class"]
            print(f"  ✅ {agent_class.PROVIDER_NAME} ({agent_type})")  # type: ignore[attr-defined]

        print()

        unavailable = set(list_available_agents()) - set(self.available_agents)
        if unavailable:
            print("UNAVAILABLE AGENTS:")
            print("-" * 80)
            for agent_type in sorted(unavailable):
                info = get_agent_info(agent_type)
                print(f"  ❌ {info['class'].PROVIDER_NAME} - Set {info['env_key']}")  # type: ignore[attr-defined]
            print()

    def _select_agent(self, position: str, cli_agent: Optional[str] = None) -> Tuple[str, str]:
        """Select agent interactively or from CLI"""

        # If CLI argument provided, use it
        if cli_agent:
            agent_type = cli_agent.lower()
            if agent_type not in self.available_agents:
                print(f"❌ Agent '{cli_agent}' not configured or invalid")
                sys.exit(1)
            info = get_agent_info(agent_type)
            return agent_type, info["models"][0]  # type: ignore[index]

        # Interactive selection
        print(f"\nSelect {position} agent:")
        print("-" * 40)

        agent_list = sorted(self.available_agents)
        for i, agent_type in enumerate(agent_list, 1):
            info = get_agent_info(agent_type)
            print(f"  {i}. {info['class'].PROVIDER_NAME}")  # type: ignore[attr-defined]

        while True:
            try:
                choice = input(f"\nEnter (1-{len(agent_list)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(agent_list):
                    agent_type = agent_list[idx]
                    break
            except (ValueError, KeyboardInterrupt):
                print("\nCancelled.")
                sys.exit(0)

        info = get_agent_info(agent_type)
        default_model = info["models"][0]  # type: ignore[index]

        # plain string (no f-string needed)
        print("\nAvailable models:")
        models_list: list = info["models"]  # type: ignore[assignment]
        for i, model in enumerate(models_list, 1):
            print(f"  {i}. {model}")

        response = input(f"\nUse default ({default_model})? (Y/n): ")
        if response.lower() == "n":
            while True:
                try:
                    choice = input(f"Enter (1-{len(info['models'])}): ").strip()  # type: ignore[arg-type]
                    idx = int(choice) - 1
                    if 0 <= idx < len(info["models"]):  # type: ignore[arg-type]
                        model = info["models"][idx]  # type: ignore[index]
                        break
                except Exception:
                    model = default_model
                    break
        else:
            model = default_model

        return agent_type, model  # type: ignore[return-value]

    def _get_topic(self) -> str:
        """Get topic from CLI or interactively"""
        if self.args and self.args.topic:
            return str(self.args.topic)

        print("\nConversation topic:")
        print("-" * 40)
        topic = input("Enter topic (or Enter for general): ").strip()
        return topic or "general"

    def _get_max_turns(self) -> int:
        """Get max turns from CLI or interactively"""
        if self.args and self.args.turns:
            return int(self.args.turns)

        print("\nMax turns:")
        print("-" * 40)
        response = input(f"Enter (default {config.DEFAULT_MAX_TURNS}): ").strip()

        if not response:
            return config.DEFAULT_MAX_TURNS

        try:
            turns = int(response)
            if 1 <= turns <= 1000:
                return turns
        except Exception:
            pass

        return config.DEFAULT_MAX_TURNS

    def _print_summary(
        self, agent1_type, agent1_model, agent2_type, agent2_model, topic, max_turns
    ):
        info1 = get_agent_info(agent1_type)
        info2 = get_agent_info(agent2_type)

        print("\n" + "=" * 80)
        print("CONFIGURATION")
        print("=" * 80)
        print(f"\nAgent 1: {info1['class'].PROVIDER_NAME}")  # type: ignore[attr-defined]
        print(f"  Model: {agent1_model}")
        print(f"\nAgent 2: {info2['class'].PROVIDER_NAME}")  # type: ignore[attr-defined]
        print(f"  Model: {agent2_model}")
        print(f"\nTopic: {topic}")
        print(f"Max Turns: {max_turns}")
        print(f"Database: {self.conversation_file}")
        print(f"Metrics: http://localhost:{config.PROMETHEUS_PORT}/metrics")

    async def _run_agent(
        self,
        agent_type: str,
        model: str,
        db_path: Path,
        partner_type: str,
        topic: str,
        max_turns: int,
    ):
        """Run a single agent"""
        logger = setup_logging(f"{agent_type}_agent", config.DEFAULT_LOG_DIR)

        # Create queue
        use_redis = config.USE_REDIS
        queue = create_queue(str(db_path) if not use_redis else config.REDIS_URL, logger, use_redis)

        # Get partner name
        partner_info = get_agent_info(partner_type)
        partner_name = partner_info["class"].PROVIDER_NAME  # type: ignore[attr-defined]

        # Create agent
        agent = create_agent(
            agent_type=agent_type,
            queue=queue,
            logger=logger,
            model=model,
            topic=topic,
            timeout=config.DEFAULT_TIMEOUT_MINUTES,
        )

        # Run agent
        await agent.run(max_turns, partner_name)

    async def run_conversation(
        self,
        agent1_type: str,
        agent1_model: str,
        agent2_type: str,
        agent2_model: str,
        topic: str,
        max_turns: int,
    ):
        """Run both agents concurrently"""
        db_path = Path(self.conversation_file)

        # Remove existing database
        if db_path.exists() and not config.USE_REDIS:
            db_path.unlink()
            lock_file = Path(f"{db_path}.lock")
            if lock_file.exists():
                lock_file.unlink()

        print("\n" + "=" * 80)
        print("STARTING CONVERSATION")
        print("=" * 80)
        print()

        # --- NEW: deterministic opener seed so only agent1 replies first ---
        try:
            from core.common import setup_logging as _setup_logging
            from core.queue import create_queue as _create_queue
            from agents import get_agent_info as _get_agent_info

            logger_seed = _setup_logging("seed", config.DEFAULT_LOG_DIR)

            queue_seed = _create_queue(
                str(db_path) if not config.USE_REDIS else config.REDIS_URL,
                logger_seed,
                config.USE_REDIS,
            )

            # Make agent2 the "last sender" so agent1 goes first
            agent2_provider = _get_agent_info(agent2_type)["class"].PROVIDER_NAME  # type: ignore[attr-defined]
            seed_text = f"[init] topic: {topic or 'general'}'"
            await queue_seed.add_message(agent2_provider, seed_text, {"system": True})
        except Exception:
            # Non-fatal: continue even if seeding fails
            pass
        # --- END NEW ---

        # Increment active conversation counter and then run agents
        increment_conversations()

        try:
            # Run both agents concurrently
            await asyncio.gather(
                self._run_agent(agent1_type, agent1_model, db_path, agent2_type, topic, max_turns),
                self._run_agent(agent2_type, agent2_model, db_path, agent1_type, topic, max_turns),
            )

            print("\n" + "=" * 80)
            print("CONVERSATION COMPLETE")
            print("=" * 80)
            if not config.USE_REDIS:
                print(f"\nDatabase: {db_path}")
            print(f"Metrics: http://localhost:{config.PROMETHEUS_PORT}/metrics")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            decrement_conversations()

    async def run_interactive(self):
        """Run interactive mode"""
        self._print_banner()

        if not self._check_configuration():
            sys.exit(1)

        self._show_available_agents()

        # Get agents (from CLI or interactive)
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
            print(f"\n⚠️  Both agents are {agent1_type}")
            response = input("Continue? (Y/n): ")
            if response.lower() == "n":
                return

        topic = self._get_topic()
        max_turns = self._get_max_turns()

        self._print_summary(agent1_type, agent1_model, agent2_type, agent2_model, topic, max_turns)

        if not (self.args and self.args.yes):
            response = input("\nStart conversation? (Y/n): ")
            if response.lower() == "n":
                return

        await self.run_conversation(
            agent1_type, agent1_model, agent2_type, agent2_model, topic, max_turns
        )


async def async_main(args: Optional[argparse.Namespace] = None):
    """Async main entry point"""
    # Setup metrics and tracing
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
        "--agent1", type=str, help="First agent (claude, chatgpt, gemini, grok, perplexity)"
    )
    parser.add_argument("--agent2", type=str, help="Second agent")
    parser.add_argument("--model1", type=str, help="Model for first agent")
    parser.add_argument("--model2", type=str, help="Model for second agent")
    parser.add_argument("--topic", type=str, help="Conversation topic")
    parser.add_argument("--turns", type=int, help="Maximum number of turns")
    parser.add_argument("--db", type=str, help="Database file path")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm all prompts")

    args = parser.parse_args()

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()