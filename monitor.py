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
    Your job is to translate the natural language instruction (which might be in the audio) into macOS bash commands.
    
    Rules:
    1. Respond with safe bash commands, ONE PER LINE. No compilation, no markdown, no explanation, NO HTML (<br> etc).
    2. If it's a complex task, break it down into multiple lines.
    3. If the user asks for a file (e.g. 'send me satele.log'), output EXACTLY: `UPLOAD: satele.log`. Do not try to be smart with paths.
    4. If you can't hear anything or it's unsafe, respond with 'UNSUPPORTED'.
    5. CWD: {cwd}
    """.format(cwd=os.getcwd())
    
    try:
        # Send everything to Gemini
        total_prompt = [prompt] + content_parts
        response = model.generate_content(total_prompt)
        text_response = response.text.replace('`', '').strip()
        
        # Handle cases where Gemini puts <br> instead of newline
        text_response = text_response.replace('<br>', '\n').replace('<br/>', '\n')
        
        # Ensure we don't have empty lines
        commands = [line.strip() for line in text_response.split('\n') if line.strip()]
        return commands
    except Exception as e:
        log(f"AI Interpretation Error: {e}")
        return None

def process_instruction(instruction, media_path=None):
    log(f"📩 Processing: {instruction} (Media: {media_path is not None})")
    
    # 1. Direct Shell Access (Text only - supports multi-command with ;)
    if not media_path and instruction.lower().startswith("sh:"):
        cmd = instruction[3:].strip()
        return f"Executing Raw: {cmd}\n---\n{run_shell(cmd)}"

    # 2. AI Interpretation (Text or Voice) -> Returns LIST of commands
    command_list = ai_interpret(instruction, media_path)
    
    if command_list and command_list[0] != "UNSUPPORTED":
        full_output = []
        log(f"🤖 AI suggested plan: {command_list}")
        
        for cmd in command_list:
            # Skip comments or empty lines
            if not cmd or cmd.startswith("#"): continue
            
            # FILE UPLOAD INTERCEPT
            if cmd.startswith("UPLOAD:"):
                raw_path = cmd.split("UPLOAD:")[1].strip()
                
                # Expand wildcards first
                if "*" in raw_path or "?" in raw_path:
                    import glob
                    matches = glob.glob(raw_path) if os.path.isabs(raw_path) else glob.glob(os.path.join(os.getcwd(), raw_path))
                    if matches:
                        # Pick the newest file
                        matches.sort(key=os.path.getmtime, reverse=True)
                        raw_path = matches[0]
                        log(f"🌟 Expanded wildcard '{cmd}' -> '{raw_path}'")
                    else:
                        log(f"⚠️ Wildcard '{raw_path}' found no matches.")

                # Auto-expand relative paths
                if not os.path.isabs(raw_path):
                    abs_path = os.path.abspath(os.path.join(os.getcwd(), raw_path))
                    log(f"📂 Converting relative path -> '{abs_path}'")
                    return f"UPLOAD: {abs_path}"
                else:
                    return f"UPLOAD: {raw_path}"
            
            log(f"➡️ Running: {cmd}")
            out = run_shell(cmd)
            full_output.append(f"> {cmd}\n{out}")
            
        return "\n\n".join(full_output)
    
    # 3. Fallback
    return f"I received: '{instruction}'. I couldn't safely translate this commands. Try 'sh: <command>'."

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
                
                # Satele Logic: If the user says "use gravity", we let the Antigravity Agent handle it.
                if "use gravity" in instruction.lower():
                    log(f"🧠 Handoff: '{instruction}' -> Letting Antigravity Agent handle this.")
                    continue

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
