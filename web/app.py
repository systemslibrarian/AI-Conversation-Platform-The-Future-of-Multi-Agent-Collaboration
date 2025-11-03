"""
Streamlit Web UI for AI Conversation Platform v5.0
With enhanced security: path validation and input sanitization
"""

import streamlit as st
import sqlite3
from pathlib import Path
import json
import bleach
from datetime import datetime

from core.config import config


def validate_db_path(db_file: str) -> Path:
    """Validate and secure database file path"""
    # Get allowed directory from config
    allowed_dir = Path(config.DATA_DIR).resolve()
    allowed_dir.mkdir(exist_ok=True, parents=True)
    
    # Resolve the requested path
    try:
        db_path = Path(db_file).resolve()
    except (ValueError, OSError) as e:
        raise ValueError(f"Invalid path: {e}")
    
    # Check if path is within allowed directory and has .db extension
    try:
        db_path.relative_to(allowed_dir)
    except ValueError:
        # If not in data dir, check if it's the default file in current dir
        if db_path.name == config.DEFAULT_CONVERSATION_FILE:
            db_path = Path(config.DEFAULT_CONVERSATION_FILE).resolve()
        else:
            raise ValueError("Database path must be within DATA_DIR")
    
    # Verify extension
    if db_path.suffix != ".db":
        raise ValueError("Database file must have .db extension")
    
    return db_path


def load_conversation(db_path: Path):
    """Load conversation from database"""
    if not db_path.exists():
        return None, None
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        # Load messages
        rows = conn.execute("SELECT * FROM messages ORDER BY id").fetchall()
        messages = [dict(row) for row in rows]
        
        # Parse metadata
        for msg in messages:
            try:
                msg["metadata"] = json.loads(msg.get("metadata", "{}"))
            except (json.JSONDecodeError, ValueError, TypeError):  # FIXED: Specific exceptions
                msg["metadata"] = {}
        
        # Load metadata
        meta_rows = conn.execute("SELECT key, value FROM metadata").fetchall()
        metadata = {row["key"]: row["value"] for row in meta_rows}
        
        return messages, metadata
    finally:
        conn.close()


def export_to_json(messages, metadata):
    """Export conversation to JSON"""
    data = {
        "metadata": metadata,
        "messages": messages,
        "exported_at": datetime.now().isoformat()
    }
    return json.dumps(data, indent=2)


def main():
    st.set_page_config(
        page_title="AI Conversation Platform",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 AI Conversation Platform v5.0")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        db_file = st.text_input(
            "Database File",
            value=config.DEFAULT_CONVERSATION_FILE,
            help="Enter path to database file (must be in data directory or default location)"
        )
        
        if st.button("🔄 Refresh", use_container_width=True):  # FIXED: Use the button return value
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Metrics")
        st.markdown(f"[View Prometheus Metrics](http://localhost:{config.PROMETHEUS_PORT}/metrics)")
        
        st.markdown("---")
        st.markdown("### Security")
        st.caption("✓ Path validation enabled")
        st.caption("✓ Input sanitization active")
    
    # Main content
    try:
        db_path = validate_db_path(db_file)
    except ValueError as e:
        st.error(f"🔒 Security Error: {e}")
        st.info("Please use a valid database path within the data directory.")
        return
    
    messages, metadata = load_conversation(db_path)
    
    if messages is None:
        st.info(f"No conversation found at: {db_file}")
        st.markdown("### Getting Started")
        st.markdown("""
        1. Run a conversation using the CLI:
```bash
           aic-start
```
        2. The conversation will be saved to the database
        3. Refresh this page to see the conversation
        """)
        return
    
    # Display metadata
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Turns", metadata.get("total_turns", 0))
    with col2:
        st.metric("Total Tokens", metadata.get("total_tokens", 0))
    with col3:
        status = "Terminated" if metadata.get("terminated") == "1" else "Active"
        st.metric("Status", status)
    with col4:
        reason = metadata.get("termination_reason", "N/A")
        if reason and reason != "null":
            st.metric("End Reason", reason)
    
    st.markdown("---")
    
    # Filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search messages", "")
    with col2:
        sender_filter = st.selectbox(
            "Filter by sender",
            ["All"] + sorted(set(msg["sender"] for msg in messages))
        )
    
    # Export button
    if st.button("📥 Export to JSON"):
        json_data = export_to_json(messages, metadata)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    st.markdown("---")
    
    # Display messages
    st.header("Conversation")
    
    filtered_messages = messages
    
    # Apply filters
    if sender_filter != "All":
        filtered_messages = [m for m in filtered_messages if m["sender"] == sender_filter]
    
    if search:
        filtered_messages = [
            m for m in filtered_messages
            if search.lower() in m["content"].lower()
        ]
    
    # Display each message
    for msg in filtered_messages:
        with st.container():
            col1, col2 = st.columns([1, 20])
            
            with col1:
                # Emoji based on sender
                emoji_map = {
                    "Claude": "🔵",
                    "ChatGPT": "🟢",
                    "Gemini": "🟣",
                    "Grok": "🟡",
                    "Perplexity": "🔴",
                }
                st.markdown(f"### {emoji_map.get(msg['sender'], '⚪')}")
            
            with col2:
                st.markdown(f"**{msg['sender']}** • {msg['timestamp'][:19]}")
                
                # Sanitize content display (prevent XSS)
                content = bleach.clean(msg["content"], tags=[], attributes={})
                st.markdown(content)
                
                # Show metadata in expander
                meta = msg.get("metadata", {})
                if meta:
                    with st.expander("Show details"):
                        cols = st.columns(4)
                        with cols[0]:
                            st.metric("Turn", meta.get("turn", "N/A"))
                        with cols[1]:
                            st.metric("Tokens", meta.get("tokens", "N/A"))
                        with cols[2]:
                            st.metric("Response Time", f"{meta.get('response_time', 'N/A')}s")
                        with cols[3]:
                            st.metric("Model", meta.get("model", "N/A"))
            
            st.markdown("---")
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"**Total Messages:** {len(filtered_messages)} of {len(messages)} | "
        f"**Database:** {db_file}"
    )


if __name__ == "__main__":
    main()
