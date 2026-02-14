import os
import time
import requests
import subprocess
import json
from datetime import datetime

# Configuration
# REMOTE_BRIDGE_URL should be the full URL to your FastAPI server (e.g. via Ngrok)
BASE_URL = os.getenv("REMOTE_BRIDGE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("BRIDGE_SECRET_KEY", "default-secret-key")

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def execute_agent_task(instruction):
    """
    Agentic Shell Proxy: Translates English to Shell or runs direct commands.
    """
    log(f"🧠 Processing: {instruction}")
    
    # 1. Handle Direct Shell Commands
    if instruction.lower().startswith("sh:"):
        cmd = instruction[3:].strip()
        return run_shell(cmd)

    # 2. Smart Mapping (A simple dictionary for common aliases)
    # This is just a 'speed dial'. The goal is to move towards LLM interpretation.
    aliases = {
        "disk usage": "df -h /",
        "disk space": "df -h /",
        "top processes": "ps -Ao pid,pcpu,comm -r | head -n 6",
        "list files": "ls -F",
        "who am i": "whoami",
        "uptime": "uptime",
        "temp": "sysctl -n machdep.cpu.brand_string && osascript -e 'set temp to do shell script \"smc -k TC0P -r | sed \\\"s/.*]  \\(.*\\) (bytes.*/\\1/\\\"\"' 2>/dev/null || echo 'SMC tool not installed'",
    }

    # 3. Dynamic Lookup
    cmd = aliases.get(instruction.lower().strip())
    if cmd:
        return f"Executing shortcut: {cmd}\n---\n{run_shell(cmd)}"

    # 4. Fallback: For a Senior Dev, we'll try to run the instruction directly 
    # as a command if it looks like one, or acknowledge we need more logic.
    return (f"I received: '{instruction}'.\n"
            "Tip: Use 'sh: <command>' for direct access.\n"
            "I'm learning more shortcuts! You can add them to bridge.py logic.")

def run_shell(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        return f"{output}\n{error}".strip()
    except Exception as e:
        return f"Execution Error: {str(e)}"

def sync_loop():
    """
    Main loop that polls the server for messages.
    """
    log("🚀 Remote Bridge Active: Listening for iPhone commands...")
    
    while True:
        try:
            # 1. Poll for a new command
            response = requests.get(
                f"{BASE_URL}/get-task", 
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and "id" in data:
                    task_id = data.get("id")
                    instruction = data.get("instruction")
                    
                    log(f"📩 Received Instruction: {instruction}")
                    
                    # 2. Execute the task
                    result = execute_agent_task(instruction)
                    
                    # 3. Report result back
                    requests.post(
                        f"{BASE_URL}/report-result",
                        json={"id": task_id, "output": result},
                        headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
                    )
                    log(f"✅ Task {task_id} completed and reported.")
            
            elif response.status_code != 204: # 204 No Content is expected when no task
                log(f"⚠️ Server returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            log("❌ Connection Error: Is the FastAPI server running?")
        except Exception as e:
            log(f"⚠️ Bridge Error: {e}")
            
        time.sleep(5) # Poll every 5 seconds

if __name__ == "__main__":
    sync_loop()
