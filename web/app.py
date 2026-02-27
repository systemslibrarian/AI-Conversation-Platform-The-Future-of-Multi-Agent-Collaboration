"""
Streamlit Web UI for AI Conversation Platform v5.0
Secure: path validation and input sanitization, mypy-friendly.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Bleach stubs may be missing in some environments; ignore import typing error.
import bleach  # type: ignore[import-untyped]
import streamlit as st

from core.config import config


def sanitize_input_text(s: Optional[str]) -> str:
    """Sanitize user-provided text (strip markup/control chars)."""
    if not s:
        return ""
    cleaned = bleach.clean(s, tags=[], attributes={}, strip=True)
    return "".join(ch for ch in cleaned if ch.isprintable()).strip()


def validate_db_path(db_file: str) -> Path:
    """
    Validate database file path.
    - Only files inside config.DATA_DIR are allowed.
    - Bare filenames are resolved into DATA_DIR.
    - .db extension required (case-insensitive).
    """
    if not db_file:
        raise ValueError("Empty database filename provided")
    db_file = sanitize_input_text(db_file)

    allowed_dir = Path(config.DATA_DIR).resolve()
    allowed_dir.mkdir(exist_ok=True, parents=True)

    candidate = Path(db_file)
    if candidate.name == db_file and not candidate.is_absolute():
        db_path = (allowed_dir / candidate).resolve()
    else:
        try:
            db_path = candidate.resolve()
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid path: {e}") from e

    try:
        db_path.relative_to(allowed_dir)
    except ValueError:
        # Special-case default filename: place it under DATA_DIR if referenced
        if db_path.name == config.DEFAULT_CONVERSATION_FILE:
            db_path = (allowed_dir / config.DEFAULT_CONVERSATION_FILE).resolve()
            try:
                db_path.relative_to(allowed_dir)
            except ValueError:
                raise ValueError("Database path must be within DATA_DIR") from None
        else:
            raise ValueError("Database path must be within DATA_DIR") from None

    if db_path.suffix.lower() != ".db":
        raise ValueError("Database file must have .db extension")

    return db_path


def load_conversation(
    db_path: Path,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Load messages and metadata from a sqlite DB. Return (None, None) if missing."""
    if not db_path.exists():
        return None, None

    try:
        conn = sqlite3.connect(f"file:{str(db_path)}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(str(db_path))

    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('messages','metadata')"
        )
        found = {row["name"] for row in cur.fetchall()}
        if "messages" not in found:
            return None, None

        try:
            rows = conn.execute("SELECT * FROM messages ORDER BY id").fetchall()
        except sqlite3.OperationalError:
            return None, None

        messages: List[Dict[str, Any]] = []
        for row in rows:
            m: Dict[str, Any] = dict(row)
            m.setdefault("content", "")
            m.setdefault("sender", "Unknown")
            m.setdefault("timestamp", "")
            raw_meta = m.get("metadata", "{}")
            if isinstance(raw_meta, (str, bytes)):
                try:
                    parsed = json.loads(raw_meta) if raw_meta else {}
                except Exception:
                    parsed = {}
            elif isinstance(raw_meta, dict):
                parsed = raw_meta
            else:
                parsed = {}
            m["metadata"] = parsed
            messages.append(m)

        metadata: Dict[str, Any] = {}
        if "metadata" in found:
            try:
                meta_rows = conn.execute("SELECT key, value FROM metadata").fetchall()
                for row in meta_rows:
                    k = row["key"]
                    v = row["value"]
                    if isinstance(v, (str, bytes)):
                        try:
                            metadata[k] = json.loads(v)
                        except Exception:
                            metadata[k] = v
                    else:
                        metadata[k] = v
            except sqlite3.OperationalError:
                metadata = {}
        return messages, metadata
    finally:
        conn.close()


def export_to_json(
    messages: Optional[List[Dict[str, Any]]], metadata: Optional[Dict[str, Any]]
) -> str:
    data = {
        "metadata": metadata or {},
        "messages": messages or [],
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def safe_lower_contains(haystack: Optional[str], needle: Optional[str]) -> bool:
    if not haystack or not needle:
        return False
    return needle.lower() in haystack.lower()


def main() -> None:
    st.set_page_config(page_title="AI Conversation Platform", page_icon="🤖", layout="wide")
    st.title("🤖 AI Conversation Platform v5.0")
    st.markdown("---")

    with st.sidebar:
        st.header("Configuration")
        db_file_raw: str = st.text_input(
            "Database File",
            value=config.DEFAULT_CONVERSATION_FILE,
            help="Path to DB file (must be inside data dir or default)",
        )
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        st.markdown("---")
        st.markdown("### Metrics")
        st.markdown(f"[View Prometheus Metrics](http://localhost:{config.PROMETHEUS_PORT}/metrics)")
        st.markdown("---")
        st.markdown("### Security")
        st.caption("✓ Path validation enabled")
        st.caption("✓ Input sanitization active")

    db_file = sanitize_input_text(db_file_raw)
    try:
        db_path = validate_db_path(db_file)
    except ValueError as e:
        st.error(f"🔒 Security Error: {e}")
        st.info("Please use a valid database path within the data directory.")
        return

    messages, metadata = load_conversation(db_path)

    if messages is None:
        st.info(f"No conversation found at: {db_path}")
        st.markdown("### Getting Started")
        st.markdown(
            "1. Run a conversation using the CLI:\n```bash\naic-start\n```\n2. The conversation will be saved to the database\n3. Refresh this page to see the conversation"
        )
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_turns = metadata.get("total_turns") if metadata and "total_turns" in metadata else 0
        try:
            st.metric("Total Turns", int(total_turns) if total_turns is not None else 0)
        except Exception:
            st.metric("Total Turns", total_turns)
    with col2:
        total_tokens = (
            metadata.get("total_tokens") if metadata and "total_tokens" in metadata else 0
        )
        try:
            st.metric("Total Tokens", int(total_tokens) if total_tokens is not None else 0)
        except Exception:
            st.metric("Total Tokens", total_tokens)
    with col3:
        terminated_val = metadata.get("terminated") if metadata else None
        status = "Terminated" if str(terminated_val) in ("1", "true", "True") else "Active"
        st.metric("Status", status)
    with col4:
        reason = metadata.get("termination_reason", "N/A") if metadata else "N/A"
        if reason and reason != "null":
            st.metric("End Reason", reason)

    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        search_raw = st.text_input("🔍 Search messages", "")
        search = sanitize_input_text(search_raw)
    with col2:
        senders = sorted({(msg.get("sender") or "Unknown") for msg in messages})
        sender_filter = st.selectbox("Filter by sender", ["All"] + senders)

    if st.button("📥 Export to JSON"):
        json_data = export_to_json(messages, metadata)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name=f"conversation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    st.markdown("---")
    st.header("Conversation")
    filtered_messages = list(messages)

    if sender_filter != "All":
        filtered_messages = [
            m for m in filtered_messages if (m.get("sender") or "Unknown") == sender_filter
        ]
    if search:
        filtered_messages = [
            m for m in filtered_messages if safe_lower_contains(m.get("content", ""), search)
        ]

    for msg in filtered_messages:
        with st.container():
            c1, c2 = st.columns([1, 20])
            with c1:
                emoji_map = {
                    "Claude": "🔵",
                    "ChatGPT": "🟢",
                    "Gemini": "🟣",
                    "Grok": "🟡",
                    "Perplexity": "🔴",
                }
                st.markdown(f"### {emoji_map.get((msg.get('sender') or ''), '⚪')}")
            with c2:
                timestamp = (msg.get("timestamp") or "")[:19]
                st.markdown(f"**{msg.get('sender', 'Unknown')}** • {timestamp}")
                content = sanitize_input_text(msg.get("content", ""))
                content = content.replace("\n", "  \n")
                st.markdown(content)
                meta = msg.get("metadata", {}) or {}
                if meta:
                    with st.expander("Show details"):
                        cols = st.columns(4)
                        with cols[0]:
                            st.metric("Turn", meta.get("turn", "N/A"))
                        with cols[1]:
                            st.metric("Tokens", meta.get("tokens", "N/A"))
                        with cols[2]:
                            rt = meta.get("response_time", "N/A")
                            st.metric(
                                "Response Time",
                                f"{rt}s" if rt not in (None, "N/A") else "N/A",
                            )
                        with cols[3]:
                            st.metric("Model", meta.get("model", "N/A"))
            st.markdown("---")

    st.markdown("---")
    st.markdown(
        f"**Total Messages:** {len(filtered_messages)} of {len(messages)} | **Database:** {db_path}"
    )


if __name__ == "__main__":
    main()
