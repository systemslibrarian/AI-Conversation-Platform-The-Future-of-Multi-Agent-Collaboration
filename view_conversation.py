#!/usr/bin/env python3
"""View conversation messages from the SQLite database."""
import sqlite3
import sys
import json
from pathlib import Path


def view_conversation(db_path="shared_conversation.db", limit=None):
    """Extract and display conversation messages."""
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get message count
    cursor.execute("SELECT COUNT(*) FROM messages")
    total = cursor.fetchone()[0]
    
    if total == 0:
        print("No messages found in database.")
        conn.close()
        return

    # Get messages
    query = "SELECT id, sender, content, timestamp FROM messages ORDER BY id"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    messages = cursor.fetchall()
    
    print(f"\n{'='*80}")
    print(f"CONVERSATION MESSAGES ({len(messages)} of {total} total)")
    print(f"{'='*80}\n")
    
    for msg_id, sender, content, timestamp in messages:
        print(f"[{msg_id}] {sender} @ {timestamp}")
        print(f"{'-'*80}")
        print(content)
        print(f"{'='*80}\n")
    
    # Get termination info
    cursor.execute("SELECT value FROM metadata WHERE key = 'termination_reason'")
    result = cursor.fetchone()
    if result:
        print(f"✓ Conversation ended: {result[0]}\n")
    
    conn.close()


def view_summary(db_path="shared_conversation.db"):
    """Show conversation summary statistics."""
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Message count by sender
    cursor.execute("""
        SELECT sender, COUNT(*), SUM(LENGTH(content)) 
        FROM messages 
        GROUP BY sender
    """)
    stats = cursor.fetchall()
    
    print(f"\n{'='*80}")
    print("CONVERSATION SUMMARY")
    print(f"{'='*80}\n")
    
    total_messages = 0
    total_chars = 0
    for sender, count, chars in stats:
        total_messages += count
        total_chars += chars
        print(f"  {sender}: {count} messages, {chars:,} characters")
    
    print(f"\n  Total: {total_messages} messages, {total_chars:,} characters")
    
    # Termination reason
    cursor.execute("SELECT value FROM metadata WHERE key = 'termination_reason'")
    result = cursor.fetchone()
    if result:
        print(f"\n  Status: Ended ({result[0]})")
    else:
        print(f"\n  Status: In progress")
    
    print(f"\n{'='*80}\n")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "summary":
            view_summary()
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python view_conversation.py           # Show all messages")
            print("  python view_conversation.py summary   # Show summary stats")
            print("  python view_conversation.py 5         # Show first 5 messages")
        else:
            try:
                limit = int(sys.argv[1])
                view_conversation(limit=limit)
            except ValueError:
                print(f"Invalid argument: {sys.argv[1]}")
                print("Use 'help' for usage information")
    else:
        view_conversation()
