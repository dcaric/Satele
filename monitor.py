import os
import time
import subprocess
import requests
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configuration
BASE_URL = os.getenv("REMOTE_BRIDGE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("BRIDGE_SECRET_KEY", "default-secret-key")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini if key is available
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
    log_brain = "🧠 AI Brain (Gemini) Active"
else:
    model = None
    log_brain = "⚠️ No GOOGLE_API_KEY found. Falling back to simple shell mapping."

def log(msg):
    print(f"[Monitor] {msg}")

def run_shell(cmd):
    try:
        # Prevent dangerous or interactive commands
        if any(bad in cmd for bad in ["> /dev/sda", "rm -rf /", "mkfs"]):
            return "Error: Dangerous command blocked."
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return (result.stdout + result.stderr).strip() or "Success (No output)"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def ai_interpret(instruction, media_path=None):
    """
    Uses Gemini to translate natural language (or voice) into a safe shell command.
    """
    if not model:
        # Simple fallback
        if "disk" in instruction.lower(): return "df -h /"
        return None

    # Load audio if present
    content_parts = [f"System Instruction: Translate to 1 safe macOS bash command.\nUser Input: {instruction}"]
    
    if media_path and os.path.exists(media_path):
        log(f"🎤 Uploading audio for analysis: {media_path}")
        try:
            # For Gemini 1.5/2.0+ we usually upload the file or pass raw bytes
            audio_file = genai.upload_file(path=media_path)
            content_parts.append(audio_file)
        except Exception as e:
            log(f"Audio upload error: {e}")

    prompt = """
    You are an AI bridge between a Senior Developer's iPhone and their MacBook terminal.
    Your job is to translate the natural language instruction (which might be in the audio) into exactly one safe macOS bash command.
    
    Rules:
    1. Respond ONLY with the command. No explanation.
    2. If it's a question about the system, find a command to answer it.
    3. If you can't hear anything or it's unsafe, respond with 'UNSUPPORTED'.
    4. CWD: {cwd}
    """.format(cwd=os.getcwd())
    
    try:
        # Send everything to Gemini
        total_prompt = [prompt] + content_parts
        response = model.generate_content(total_prompt)
        return response.text.replace('`', '').strip()
    except Exception as e:
        log(f"AI Interpretation Error: {e}")
        return None

def process_instruction(instruction, media_path=None):
    log(f"📩 Processing: {instruction} (Media: {media_path is not None})")
    
    # 1. Direct Shell Access (Text only)
    if not media_path and instruction.lower().startswith("sh:"):
        cmd = instruction[3:].strip()
        return f"Executing Raw: {cmd}\n---\n{run_shell(cmd)}"

    # 2. AI Interpretation (Text or Voice)
    suggested_cmd = ai_interpret(instruction, media_path)
    
    if suggested_cmd and suggested_cmd != "UNSUPPORTED":
        log(f"🤖 AI suggested command: {suggested_cmd}")
        output = run_shell(suggested_cmd)
        return f"🤖 AI interpreted as: `{suggested_cmd}`\n---\n{output}"
    
    # 3. Fallback to conversation logic
    return f"I received: '{instruction}'. I couldn't safely translate this to a command. Try 'sh: <command>'. Or check if GOOGLE_API_KEY is set."

def monitor_loop():
    log(f"🚀 Autonomous Monitoring Started... ({log_brain})")
    while True:
        try:
            response = requests.get(
                f"{BASE_URL}/get-task", 
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=5
            )
            
            if response.status_code == 200:
                task = response.json()
                task_id = task['id']
                instruction = task['instruction']
                media_path = task.get('media_path')
                
                result = process_instruction(instruction, media_path)
                
                requests.post(
                    f"{BASE_URL}/report-result",
                    json={"id": task_id, "output": result},
                    headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                    timeout=5
                )
                log(f"✅ Result sent for {task_id}")
                
        except Exception:
            pass
            
        time.sleep(5)

if __name__ == "__main__":
    monitor_loop()
