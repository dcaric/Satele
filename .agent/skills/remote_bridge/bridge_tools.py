import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = os.getenv("REMOTE_BRIDGE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("BRIDGE_SECRET_KEY", "default-secret-key")

def fetch_next_task():
    """
    Fetches the next pending message from the bridge server.
    Used by the Antigravity Agent to check for remote instructions.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/get-task", 
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json() # Returns {id, instruction, sender, source}
        return None
    except Exception as e:
        return {"error": str(e)}

def send_agent_reply(task_id, message):
    """
    Sends the Agent's reasoning or result back to WhatsApp.
    """
    try:
        requests.post(
            f"{BASE_URL}/report-result",
            json={"id": task_id, "output": message},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )
        return True
    except Exception as e:
        print(f"Error sending reply: {e}")
        return False

if __name__ == "__main__":
    # If run as a script, it just lists pending tasks
    task = fetch_next_task()
    if task:
        print(f"Pending Task: {task['instruction']}")
    else:
        print("No pending tasks.")
