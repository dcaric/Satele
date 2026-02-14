import sqlite3
import os
import time
import requests

# Path to iMessage database
CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")
SERVER_URL = "http://localhost:8000/webhook/message"

def get_last_message_id(cursor):
    cursor.execute("SELECT MAX(ROWID) FROM message")
    return cursor.fetchone()[0]

def poll_messages():
    print("👀 Monitoring iMessage chat.db...")
    
    # Needs Full Disk Access on macOS to read chat.db
    if not os.path.exists(CHAT_DB):
        print(f"❌ Error: {CHAT_DB} not found. Ensure Terminal/IDE has Full Disk Access.")
        return

    conn = sqlite3.connect(CHAT_DB)
    cursor = conn.cursor()
    
    last_id = get_last_message_id(cursor)
    
    while True:
        try:
            # Query for new messages since last check
            # This query finds messages from a specific handle or containing '@antigravity'
            query = """
            SELECT message.ROWID, message.text, handle.id 
            FROM message 
            JOIN handle ON message.handle_id = handle.ROWID
            WHERE message.ROWID > ? 
            AND message.is_from_me = 0
            """
            cursor.execute(query, (last_id,))
            new_messages = cursor.fetchall()
            
            for row_id, text, sender in new_messages:
                last_id = row_id
                if text and "@antigravity" in text.lower():
                    print(f"📩 New Command from {sender}: {text}")
                    # Forward to our bridge server
                    requests.post(SERVER_URL, json={"text": text, "sender": sender})
            
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ iMessage Relay Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    poll_messages()
