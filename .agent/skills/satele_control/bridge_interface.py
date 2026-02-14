import os
import requests
import sys
import json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("REMOTE_BRIDGE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("BRIDGE_SECRET_KEY", "default-secret-key")

def check_task():
    try:
        response = requests.get(
            f"{BASE_URL}/get-task", 
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )
        if response.status_code == 200:
            task = response.json()
            if task:
                print(json.dumps(task))
            else:
                print("null")
        else:
            print("null")
    except Exception as e:
        print(f"Error: {e}")

def reply_task(task_id, message):
    try:
        response = requests.post(
            f"{BASE_URL}/report-result",
            json={"id": task_id, "output": message},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )
        if response.status_code == 200:
            print("Reply Sent")
        else:
            print(f"Failed: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: check | reply <id> <msg>")
        sys.exit(1)
        
    cmd = sys.argv[1]
    
    if cmd == "check":
        check_task()
    elif cmd == "reply":
        if len(sys.argv) < 4:
            print("Usage: reply <id> <msg>")
            sys.exit(1)
        task_id = sys.argv[2]
        message = " ".join(sys.argv[3:])
        reply_task(task_id, message)
