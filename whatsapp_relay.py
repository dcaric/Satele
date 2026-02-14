import os
import subprocess
import time
import json
import requests

# Configuration
SERVER_URL = "http://localhost:8000/webhook/message"

def listen_whatsapp():
    """
    Uses a small AppleScript loop to check for the most recent 
    WhatsApp notification or window title change.
    
    NOTE: For a more robust solution as a Senior Dev, 
    we could compile a small Swift binary using `NSUserNotificationCenter` 
    monitoring or Accessibility APIs.
    """
    print("🟢 WhatsApp Relay Active: Watching for messages...")
    
    last_processed_msg = ""

    # This AppleScript tries to read the 'last message' from the WhatsApp UI 
    # via Accessibility. It requires 'Accessibility' permissions for the Terminal.
    script = '''
    tell application "System Events"
        tell process "WhatsApp"
            try
                -- This path varies slightly by WA version, but usually:
                -- List 1 is the chat list, UI Element 1 of the selected row is the text
                set latestMsg to value of static text 1 of UI element 1 of row 1 of table 1 of scroll area 1 of split group 1 of window 1
                return latestMsg
            on error
                return ""
            end try
        end tell
    end tell
    '''

    while True:
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            current_msg = result.stdout.strip()
            
            # Check if it's a new command directed at us
            if current_msg and current_msg != last_processed_msg:
                if "@antigravity" in current_msg.lower():
                    print(f"📩 WhatsApp Command Detected: {current_msg}")
                    requests.post(SERVER_URL, json={"text": current_msg, "sender": "WhatsApp-User"})
                    last_processed_msg = current_msg
            
            time.sleep(3) # Check every 3 seconds
        except Exception as e:
            print(f"⚠️ WhatsApp Relay Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    listen_whatsapp()
