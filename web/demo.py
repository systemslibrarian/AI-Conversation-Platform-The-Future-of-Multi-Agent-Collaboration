"""
Web Demo for AI Conversation Platform
Real-time AI-to-AI conversation viewer with SSE streaming.
"""

from __future__ import annotations

import asyncio
import json
import os

# ---------------------------------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------------------------------
import sys
import threading
import time
import uuid
from collections import defaultdict
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Optional

from flask import Flask, Response, jsonify, render_template, request

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents import create_agent, list_available_agents
from core.common import setup_logging
from core.config import config
from core.queue import SQLiteQueue

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(32)

# Active sessions: session_id -> session state dict
_sessions: Dict[str, Dict[str, Any]] = {}

# Rate limiting: IP -> list of request timestamps
_rate_limits: Dict[str, list] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 5  # max starts per IP per window
MAX_SESSIONS = 20  # Maximum concurrent sessions
SESSION_TTL = 600  # 10 minutes max session lifetime

# Agent display info
AGENT_DISPLAY = {
    "chatgpt": {"name": "ChatGPT", "icon": "🤖", "color": "#10a37f"},
    "claude": {"name": "Claude", "icon": "🟣", "color": "#7c3aed"},
    "gemini": {"name": "Gemini", "icon": "💎", "color": "#4285f4"},
    "grok": {"name": "Grok", "icon": "⚡", "color": "#1da1f2"},
    "perplexity": {"name": "Perplexity", "icon": "🔍", "color": "#20b2aa"},
}

# Env-var names for demo keys
AGENT_ENV_KEYS = {
    "chatgpt": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "grok": "XAI_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}

DEMO_MAX_TURNS = 6  # Limit demo conversations


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    """Add security headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    return response


# ---------------------------------------------------------------------------
# Rate limiting & session cleanup helpers
# ---------------------------------------------------------------------------
def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is within rate limits, False if exceeded."""
    now = time.time()
    # Prune old entries
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_limits[ip].append(now)
    return True


def _cleanup_stale_sessions():
    """Remove sessions older than SESSION_TTL."""
    now = time.time()
    stale = [sid for sid, s in _sessions.items() if now - s.get("started_at", now) > SESSION_TTL]
    for sid in stale:
        session = _sessions.pop(sid, None)
        if session:
            session["stop_requested"] = True


# ---------------------------------------------------------------------------
# Streaming Queue Wrapper
# ---------------------------------------------------------------------------
class StreamingQueue:
    """
    Wraps SQLiteQueue and mirrors every add_message call into a
    thread-safe Python Queue so the SSE endpoint can stream them.
    """

    def __init__(self, sqlite_queue: SQLiteQueue, event_queue: Queue):
        self._sq = sqlite_queue
        self._eq = event_queue

    # --- delegate everything to the real queue ---------------------------------
    async def add_message(self, sender: str, content: str, metadata: Optional[Dict] = None) -> Dict:
        result = await self._sq.add_message(sender, content, metadata)
        # Push an event for the SSE stream
        self._eq.put(
            {
                "type": "message",
                "sender": sender,
                "content": content,
                "metadata": metadata or {},
                "timestamp": result.get("timestamp", ""),
            }
        )
        return result

    async def get_context(self, max_messages: int = 10):
        return await self._sq.get_context(max_messages)

    async def get_last_sender(self):
        return await self._sq.get_last_sender()

    async def is_terminated(self):
        return await self._sq.is_terminated()

    async def mark_terminated(self, reason: str):
        await self._sq.mark_terminated(reason)
        self._eq.put({"type": "terminated", "reason": reason})

    async def get_termination_reason(self):
        return await self._sq.get_termination_reason()

    async def load(self):
        return await self._sq.load()


# ---------------------------------------------------------------------------
# Conversation runner (runs in background thread)
# ---------------------------------------------------------------------------


def _run_conversation(session_id: str, session: Dict[str, Any]):
    """Run the async conversation loop inside a new event loop on a thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_async_conversation(session_id, session))
    except Exception as exc:
        session["event_queue"].put({"type": "error", "message": str(exc)})
    finally:
        session["event_queue"].put({"type": "done"})
        loop.close()


async def _async_conversation(session_id: str, session: Dict[str, Any]):
    """The actual async conversation between two agents."""
    agent1_type = session["agent1"]
    agent2_type = session["agent2"]
    topic = session["topic"]
    max_turns = session["max_turns"]
    api_keys = session["api_keys"]
    event_queue: Queue = session["event_queue"]
    delay = session.get("delay", 2.0)

    logger = setup_logging(f"demo_{session_id}")

    # Create DB in a temp location
    data_dir = Path(config.DATA_DIR)
    data_dir.mkdir(exist_ok=True, parents=True)
    db_path = data_dir / f"demo_{session_id}.db"

    sq = SQLiteQueue(db_path, logger)
    queue = StreamingQueue(sq, event_queue)

    # Resolve API keys: user-supplied > environment variable
    def resolve_key(agent_type: str) -> str:
        user_key = api_keys.get(agent_type, "").strip()
        if user_key:
            return user_key
        env_var = AGENT_ENV_KEYS.get(agent_type, "")
        env_key = os.getenv(env_var, "")
        if env_key:
            return env_key
        # For gemini, also check GEMINI_API_KEY
        if agent_type == "gemini":
            alt = os.getenv("GEMINI_API_KEY", "")
            if alt:
                return alt
        raise ValueError(
            f"No API key for {agent_type}. "
            f"Please provide your own {AGENT_ENV_KEYS.get(agent_type, '')} key."
        )

    try:
        key1 = resolve_key(agent1_type)
        key2 = resolve_key(agent2_type)
    except ValueError as e:
        event_queue.put({"type": "error", "message": str(e)})
        return

    agent1 = create_agent(
        agent_type=agent1_type,
        queue=queue,
        logger=logger,
        topic=topic,
        timeout=config.DEFAULT_TIMEOUT_MINUTES,
        api_key=key1,
    )
    agent2 = create_agent(
        agent_type=agent2_type,
        queue=queue,
        logger=logger,
        topic=topic,
        timeout=config.DEFAULT_TIMEOUT_MINUTES,
        api_key=key2,
    )

    event_queue.put(
        {
            "type": "status",
            "message": f'Starting conversation between {agent1.agent_name} and {agent2.agent_name} on "{topic}"...',
        }
    )

    # Seed the conversation — agent1 goes first
    event_queue.put({"type": "thinking", "agent": agent1.agent_name})

    agent1.start_time = __import__("datetime").datetime.now()
    agent2.start_time = __import__("datetime").datetime.now()

    # Turn-based loop (sequential, not concurrent gather)
    agents = [agent1, agent2]
    names = [agent1.agent_name, agent2.agent_name]

    for turn in range(max_turns):
        if session.get("stop_requested"):
            event_queue.put({"type": "terminated", "reason": "stopped_by_user"})
            return

        current = agents[turn % 2]
        _ = names[(turn + 1) % 2]

        event_queue.put({"type": "thinking", "agent": current.agent_name})

        # check termination
        if await queue.is_terminated():
            break

        try:
            content, tokens, response_time = await current.generate_response()
        except Exception as exc:
            event_queue.put({"type": "error", "message": f"{current.agent_name} error: {exc}"})
            break

        # Check similarity
        if current._check_similarity(content):
            await queue.mark_terminated("repetition_detected")
            break

        current.recent_responses.append(content)

        from dataclasses import asdict

        from agents.base import TurnMetadata

        meta = TurnMetadata(
            model=current.model,
            tokens=tokens,
            response_time=round(response_time, 2),
            turn=turn + 1,
        )
        await queue.add_message(current.agent_name, content, asdict(meta))
        current.turn_count += 1

        # Check termination signals in content
        if term_reason := current._check_termination_signals(content):
            await queue.mark_terminated(term_reason)
            break

        # Deliberate delay so viewers can follow
        await asyncio.sleep(delay)

    # If we finished normally
    if not await queue.is_terminated():
        await queue.mark_terminated("max_turns_reached")

    # Clean up temp db
    try:
        db_path.unlink(missing_ok=True)
        lock_path = Path(f"{db_path}.lock")
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Serve the demo page."""
    # Determine which agents have demo keys available
    demo_agents = {}
    for agent_type in list_available_agents():
        env_var = AGENT_ENV_KEYS.get(agent_type, "")
        has_key = bool(os.getenv(env_var, ""))
        # Check alt key for gemini
        if not has_key and agent_type == "gemini":
            has_key = bool(os.getenv("GEMINI_API_KEY", ""))
        demo_agents[agent_type] = {
            "name": AGENT_DISPLAY.get(agent_type, {}).get("name", agent_type),
            "icon": AGENT_DISPLAY.get(agent_type, {}).get("icon", "🤖"),
            "color": AGENT_DISPLAY.get(agent_type, {}).get("color", "#666"),
            "has_demo_key": has_key,
        }
    return render_template("demo.html", agents=demo_agents, max_turns=DEMO_MAX_TURNS)


@app.route("/api/start", methods=["POST"])
def start_conversation():
    """Start a new AI-to-AI conversation."""
    # Rate limiting
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify(
            {"error": "Rate limit exceeded. Please wait before starting another conversation."}
        ), 429

    # Enforce max concurrent sessions (clean stale first)
    _cleanup_stale_sessions()
    if len(_sessions) >= MAX_SESSIONS:
        return jsonify({"error": "Server is at capacity. Please try again later."}), 503

    data = request.get_json(force=True)

    agent1 = data.get("agent1", "").strip().lower()
    agent2 = data.get("agent2", "").strip().lower()
    topic = data.get("topic", "").strip() or "general"
    api_keys = data.get("api_keys", {})
    max_turns = min(int(data.get("max_turns", DEMO_MAX_TURNS)), DEMO_MAX_TURNS * 2)
    delay = max(0.5, min(float(data.get("delay", 2.0)), 10.0))

    available = list_available_agents()
    if agent1 not in available:
        return jsonify({"error": f"Unknown agent: {agent1}"}), 400
    if agent2 not in available:
        return jsonify({"error": f"Unknown agent: {agent2}"}), 400

    # Check that we have keys for both agents
    for ag in [agent1, agent2]:
        user_key = api_keys.get(ag, "").strip()
        env_var = AGENT_ENV_KEYS.get(ag, "")
        has_env = bool(os.getenv(env_var, ""))
        if not has_env and ag == "gemini":
            has_env = bool(os.getenv("GEMINI_API_KEY", ""))
        if not user_key and not has_env:
            name = AGENT_DISPLAY.get(ag, {}).get("name", ag)
            return jsonify(
                {"error": f"No API key for {name}. Please enter your {env_var} key."}
            ), 400

    # Sanitise topic
    if len(topic) > 500:
        topic = topic[:500]

    session_id = uuid.uuid4().hex[:12]
    event_queue: Queue = Queue(maxsize=200)

    session = {
        "agent1": agent1,
        "agent2": agent2,
        "topic": topic,
        "max_turns": max_turns,
        "api_keys": api_keys,
        "event_queue": event_queue,
        "delay": delay,
        "stop_requested": False,
        "started_at": time.time(),
    }
    _sessions[session_id] = session

    thread = threading.Thread(
        target=_run_conversation,
        args=(session_id, session),
        daemon=True,
    )
    thread.start()
    session["thread"] = thread

    return jsonify({"session_id": session_id})


@app.route("/api/stream/<session_id>")
def stream(session_id: str):
    """SSE endpoint — streams conversation events to the browser."""
    session = _sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    def generate():
        eq: Queue = session["event_queue"]
        while True:
            try:
                event = eq.get(timeout=60)
            except Empty:
                # Send keepalive
                yield 'data: {"type": "keepalive"}\n\n'
                continue

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in ("done", "error"):
                # Clean up session after a short delay
                def cleanup():
                    time.sleep(5)
                    _sessions.pop(session_id, None)

                threading.Thread(target=cleanup, daemon=True).start()
                break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/stop/<session_id>", methods=["POST"])
def stop_conversation(session_id: str):
    """Request a running conversation to stop."""
    session = _sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    session["stop_requested"] = True
    return jsonify({"status": "stopping"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("DEMO_PORT", "5000"))
    print(f"\n{'=' * 60}")
    print("  AI Conversation Platform — Web Demo")
    print(f"  http://localhost:{port}")
    print(f"{'=' * 60}\n")
    host = os.getenv("DEMO_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False, threaded=True)
