"""
BaseAgent - v5.0 ASYNC EDITION with Security Hardening
- Full async/await support with run_in_executor helper for blocking APIs
- Integrated metrics and tracing
- Comprehensive error handling
- Circuit breaker pattern
- LLM Guard integration for prompt injection protection
"""

from abc import ABC
from typing import Tuple, Optional, Dict, List, Any, Callable
from collections import deque
from datetime import datetime
from dataclasses import dataclass, asdict
import time
import asyncio
import logging

from core.config import config
from core.queue import QueueInterface
from core.common import log_event, simple_similarity, add_jitter
from core.metrics import record_call, record_latency, record_error
from core.tracing import get_tracer


@dataclass
class TurnMetadata:
    """Metadata for a conversation turn"""

    model: str
    tokens: int
    response_time: float
    turn: int


class CircuitBreaker:
    """Circuit breaker pattern for API fault tolerance"""

    def __init__(
        self,
        logger: logging.Logger,
        provider_name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ):
        self.logger = logger
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == "OPEN" and self.last_failure_time:
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "HALF_OPEN"
                return False
            return True
        return False

    def record_success(self) -> None:
        """Record successful call"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold and self.state != "OPEN":
            self.state = "OPEN"
            log_event(
                self.logger,
                "circuit_breaker_opened",
                {
                    "agent": self.provider_name,
                    "timeout": self.timeout_seconds,
                    "failures": self.failure_count,
                },
            )


class BaseAgent(ABC):
    """Base class for AI agents with async support and security"""

    PROVIDER_NAME = "Base"
    DEFAULT_MODEL = ""

    def __init__(
        self,
        queue: QueueInterface,
        logger: logging.Logger,
        model: str,
        topic: str,
        timeout_minutes: int,
        agent_name: Optional[str] = None,
    ):
        self.queue = queue
        self.logger = logger
        self.model = model or self.DEFAULT_MODEL
        self.topic = topic
        self.timeout_minutes = timeout_minutes
        self.agent_name = agent_name or self.PROVIDER_NAME
        self.client: Optional[Any] = None

        # Circuit breaker with observability
        self.circuit_breaker = CircuitBreaker(logger=self.logger, provider_name=self.PROVIDER_NAME)

        # State tracking
        self.start_time: Optional[datetime] = None
        self.turn_count = 0
        self.consecutive_similar = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.recent_responses: deque[str] = deque(maxlen=5)

        # Tracer
        self.tracer = get_tracer()

        # LLM Guard (optional)
        self.llm_guard_enabled = config.ENABLE_LLM_GUARD
        if self.llm_guard_enabled:
            try:
                from llm_guard.input_scanners import PromptInjection
                from llm_guard.output_scanners import NoRefusal

                self.input_scanner = PromptInjection(threshold=0.5)
                self.output_scanner = NoRefusal(threshold=0.5)
            except ImportError:
                self.logger.warning("llm-guard not installed, security features disabled")
                self.llm_guard_enabled = False

        log_event(
            self.logger,
            "agent_initialized",
            {
                "agent": self.agent_name,
                "model": self.model,
                "topic": topic or "general",
                "security_enabled": self.llm_guard_enabled,
            },
        )

    # ---------- helpers -------------------------------------------------------

    async def _in_executor(self, fn: Callable, *args, **kwargs):
        """Run blocking function in a thread executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    def _scan_input(self, text: str) -> Tuple[str, bool]:
        """Scan input for prompt injection (returns sanitized text and is_valid flag)"""
        if not self.llm_guard_enabled:
            return text, True
        try:
            sanitized_prompt, is_valid, risk_score = self.input_scanner.scan("", text)
            if not is_valid:
                self.logger.warning(f"Prompt injection detected, risk score: {risk_score}")
            return sanitized_prompt, is_valid
        except Exception as e:
            self.logger.error(f"Input scanning failed: {e}")
            return text, True

    def _scan_output(self, text: str) -> str:
        """Scan output for issues"""
        if not self.llm_guard_enabled:
            return text
        try:
            sanitized_output, is_valid, risk_score = self.output_scanner.scan("", text)
            if not is_valid:
                self.logger.warning(f"Output scanning issue, risk score: {risk_score}")
            return str(sanitized_output)
        except Exception as e:
            self.logger.error(f"Output scanning failed: {e}")
            return text

    async def _is_timeout(self) -> bool:
        """Check if agent has exceeded timeout"""
        if not self.start_time:
            return False
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed > (self.timeout_minutes * 60)

    def _check_termination_signals(self, content: str) -> Optional[str]:
        """Check for conversation termination signals"""
        lower = content.lower()
        term_token = getattr(config, "TERMINATION_TOKEN", "[done]")
        if term_token.lower() in lower:
            return f"sentinel_phrase: {term_token}"

        for phrase in config.TOPIC_DRIFT_PHRASES:
            if phrase.lower() in lower:
                return f"sentinel_phrase: {phrase}"
        return None

    def _check_similarity(self, content: str) -> bool:
        """Detect repetitive responses"""
        if not self.recent_responses:
            return False
        sim = simple_similarity(content, self.recent_responses[-1])
        if sim > config.SIMILARITY_THRESHOLD:
            self.consecutive_similar += 1
            if self.consecutive_similar >= config.MAX_CONSECUTIVE_SIMILAR:
                return True
        else:
            self.consecutive_similar = 0
        return False

    async def _call_api(self, messages: List[Dict[str, str]]) -> Tuple[str, int]:
        """Call the AI API. Subclasses should implement this method."""
        raise NotImplementedError("_call_api must be implemented by subclasses")

    async def generate_response(self) -> Tuple[str, int, float]:
        """Generate response with error handling, metrics, and security"""
        start_time = time.time()

        if self.circuit_breaker.is_open():
            raise Exception(
                f"Circuit breaker OPEN. Retry in {int(self.circuit_breaker.timeout_seconds - (time.time() - (self.circuit_breaker.last_failure_time or 0)))}s"
            )

        with self.tracer.start_as_current_span(f"{self.PROVIDER_NAME}.generate"):
            try:
                messages = await self._build_messages()

                # Sanitize user input (last user message)
                if self.llm_guard_enabled and messages:
                    for i in range(len(messages) - 1, -1, -1):
                        if messages[i].get("role") == "user":
                            sanitized, is_valid = self._scan_input(messages[i]["content"])
                            if not is_valid:
                                self.logger.warning("Potentially malicious input detected")
                            messages[i]["content"] = sanitized
                            break

                content, tokens = await self._call_api(messages)
                content = self._scan_output(content)

                response_time = time.time() - start_time
                self.consecutive_errors = 0
                self.circuit_breaker.record_success()

                record_call(self.PROVIDER_NAME, self.model, "success")
                record_latency(self.PROVIDER_NAME, self.model, response_time)

                log_event(
                    self.logger,
                    "response_generated",
                    {
                        "agent": self.agent_name,
                        "tokens": tokens,
                        "response_time": round(response_time, 2),
                    },
                )
                return content, tokens, response_time

            except Exception as e:
                self.consecutive_errors += 1
                self.circuit_breaker.record_failure()

                error_str = str(e).lower()
                status = getattr(e, "status", None) or getattr(e, "status_code", None)
                is_rate_limit = (str(status) == "429") or ("rate_limit" in error_str)
                is_timeout = "timeout" in error_str or "timeout" in type(e).__name__.lower()

                error_type = (
                    "timeout" if is_timeout else ("rate_limit" if is_rate_limit else "api_error")
                )
                record_error(self.PROVIDER_NAME, error_type)
                record_call(self.PROVIDER_NAME, self.model, "error")

                log_event(
                    self.logger,
                    "api_error",
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "consecutive_errors": self.consecutive_errors,
                    },
                )
                raise

    async def _build_messages(self) -> List[Dict[str, str]]:
        """Build message context for API call."""
        messages: List[Dict[str, str]] = []
        context = await self.queue.get_context(config.MAX_CONTEXT_MSGS)
        for m in context:
            role = "assistant" if m["sender"] == self.agent_name else "user"
            messages.append({"role": role, "content": m["content"]})
        return messages

    def _build_system_prompt(self) -> str:
        topic = self.topic or "general"
        return f"You are {self.agent_name}. Topic: {topic}. Provide thoughtful, engaging responses."

    async def should_respond(self, partner_name: str) -> bool:
        if await self._is_timeout() or await self.queue.is_terminated():
            return False
        last_sender = await self.queue.get_last_sender()
        return not last_sender or last_sender == partner_name

    async def respond(self) -> None:
        print(f"\n{self.agent_name} thinking...")

        max_retries = 5
        backoff = config.INITIAL_BACKOFF

        for attempt in range(max_retries):
            try:
                content, tokens, response_time = await self.generate_response()

                if self._check_similarity(content):
                    await self.queue.mark_terminated("repetition_detected")
                    print("\n✓ Terminated: repetition detected")
                    return

                self.recent_responses.append(content)

                meta = TurnMetadata(
                    model=self.model,
                    tokens=tokens,
                    response_time=round(response_time, 2),
                    turn=self.turn_count + 1,
                )
                await self.queue.add_message(self.agent_name, content, asdict(meta))
                self.turn_count += 1

                preview = content[:500] + ("..." if len(content) > 500 else "")
                print(
                    f"\n{self.agent_name} (Turn {self.turn_count}):\n{'-' * 80}\n"
                    f"{preview}\n{'-' * 80}\n"
                    f"Tokens: {tokens} | Time: {response_time:.2f}s"
                )

                if term_reason := self._check_termination_signals(content):
                    await self.queue.mark_terminated(term_reason)
                    print(f"\n✓ Terminated: {term_reason}")
                    return
                return

            except Exception as e:
                error_str = str(e).lower()
                status = getattr(e, "status", None) or getattr(e, "status_code", None)
                is_timeout = "timeout" in error_str or "timeout" in type(e).__name__.lower()
                is_rate_limit = (str(status) == "429") or ("rate_limit" in error_str)

                # Check for non-retriable errors (configuration issues)
                if any(x in error_str for x in ["404", "not found", "invalid api key", "unauthorized", "403"]):
                    print(f"✗ Configuration Error: {str(e)}")
                    await self.queue.mark_terminated("configuration_error")
                    raise Exception(f"Configuration error: {str(e)}")

                # Handle rate limits and timeouts with retry
                if is_rate_limit or is_timeout:
                    wait_time = backoff
                    if is_rate_limit and hasattr(e, "headers") and isinstance(e.headers, dict):
                        try:
                            wait_time = float(e.headers.get("Retry-After", backoff))
                        except Exception:
                            pass

                    wait_time = add_jitter(wait_time)
                    print(
                        f"⚠ {'Timeout' if is_timeout else 'Rate limited'}. "
                        f"Retry {attempt + 1}/{max_retries} in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    backoff = min(backoff * config.BACKOFF_MULTIPLIER, config.MAX_BACKOFF)
                    continue

                elif "circuit breaker" in error_str:
                    print(f"⚠ Circuit breaker open: {error_str} — skipping this turn")
                    await asyncio.sleep(0)
                    return

                else:
                    print(f"✗ Error: {str(e)}")
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        await self.queue.mark_terminated("consecutive_errors")
                        raise
                    await asyncio.sleep(0.5)
                    return

        await self.queue.mark_terminated("too_many_retries")
        print("\n✗ Terminated: too many retries")

    async def run(self, max_turns: int, partner_name: str) -> None:
        self.start_time = datetime.now()

        print("=" * 80)
        print(f"{self.agent_name.upper()} AGENT v5.0")
        print(f"Model: {self.model}")
        print(f"Topic: {self.topic or '(general)'}")
        print(f"Max turns: {max_turns}")
        print("=" * 80)

        log_event(self.logger, "agent_started", {"agent": self.agent_name, "max_turns": max_turns})

        try:
            while self.turn_count < max_turns:
                if await self._is_timeout():
                    await self.queue.mark_terminated("timeout")
                    print(f"\n⏱ Timeout reached ({self.timeout_minutes} minutes)")
                    break

                if await self.queue.is_terminated():
                    reason = await self.queue.get_termination_reason()
                    print(f"\n✓ Conversation ended: {reason}")
                    break

                if await self.should_respond(partner_name):
                    await self.respond()
                else:
                    await asyncio.sleep(0.1)

            if self.turn_count >= max_turns:
                await self.queue.mark_terminated("max_turns_reached")
                print(f"\n✓ Max turns reached ({max_turns})")

        except KeyboardInterrupt:
            await self.queue.mark_terminated("user_interrupt")
            print("\n⚠ Stopped by user")

        except Exception as e:
            log_event(self.logger, "agent_error", {"agent": self.agent_name, "error": str(e)})
            print(f"\n✗ Fatal error: {e}")
            raise

        finally:
            await self.print_summary()

    async def print_summary(self) -> None:
        try:
            data = await self.queue.load()
            m = data["metadata"]

            print("\n" + "=" * 80)
            print("CONVERSATION SUMMARY")
            print("=" * 80)
            print(f"Total messages: {m.get('total_turns', 0)}")
            print(f"{self.agent_name}: {m.get(f'{self.agent_name.lower()}_turns', 0)}")
            print(f"Total tokens: {m.get('total_tokens', 'N/A')}")
            if m.get("termination_reason"):
                print(f"Ended: {m['termination_reason']}")
            print("=" * 80)

        except Exception as e:
            print(f"\n✗ Summary failed: {e}")
