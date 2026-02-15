import os
import time
import subprocess
import requests
import json
import platform
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def log(msg):
    print(f"[Monitor] {msg}")

# Configuration
BASE_URL = os.getenv("REMOTE_BRIDGE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("BRIDGE_SECRET_KEY", "default-secret-key")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini if key is available
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    model = genai.GenerativeModel(gemini_model_name)
    log(f"🧠 Using Gemini Model: {gemini_model_name}")
    log_brain = "🧠 AI Brain (Gemini) Active"
else:
    model = None
    log_brain = "⚠️ No GOOGLE_API_KEY found. Falling back to simple shell mapping."

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
    Uses Gemini or Ollama to translate natural language (or voice) into a safe shell command.
    """
    # Load audio if present (Gemini only supports this via API, Ollama likely plain text)
    # We prepare content_parts but might not use it for Ollama
    
    content_parts = [f"System Instruction: Translate to 1 safe macOS bash command.\nUser Input: {instruction}"]
    
    if media_path and os.path.exists(media_path):
        log(f"🎤 Uploading audio for analysis: {media_path}")
        try:
            if model: # Only try uploading if Gemini is configured?
                # For Gemini 1.5/2.0+ we usually upload the file or pass raw bytes
                audio_file = genai.upload_file(path=media_path)
                content_parts.append(audio_file)
        except Exception as e:
            log(f"Audio upload error: {e}")

    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    current_model = os.getenv("OLLAMA_MODEL", "gemma:2b") if provider == "ollama" else "gemini"
    system_os = platform.system()
    
    username = os.getenv("USER", "User")
    
    prompt_text = """
    You are an AI bridge between a Senior Developer's iPhone and their {os_name} terminal.
    Your job is to translate the natural language instruction (which might be in the audio) into safe {os_name} bash commands.
    
    Rules:
    1. Respond with safe bash commands, ONE PER LINE. No compilation, no markdown, no explanation, NO HTML (<br> etc).
    2. If it's a complex task, break it down into multiple lines.
    3. Use `UPLOAD: <filepath>` ONLY when the user explicitly asks to download/get a specific file. NEVER use `UPLOAD:` for directories or lists of files (use `ls` instead).
    4. If you can't hear anything or it's unsafe, respond with 'UNSUPPORTED'.
    5. Tip: For zipping, use wildcards: `zip archive.zip *.json *.log`. Avoid `find ... -print0` pipes as they can fail on some shells.
    6. Tip: To chain commands, use separate lines or `&&`. To send the zip after creation, add a new line: `UPLOAD: archive.zip`.
    7. CWD: {cwd}
    8. System Info: OS ({os_name}), AI ({provider} - {model}), User ({user})
    """.format(cwd=os.getcwd(), provider=provider, model=current_model, os_name=system_os, user=username)
    
    if provider == "ollama":
        try:
            model_name = current_model
            log(f"🦙 Using Ollama Model: {model_name}")
            
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": instruction}
                ],
                "stream": False
            }
            
            resp = requests.post("http://localhost:11434/api/chat", json=payload, timeout=30)
            if resp.status_code == 200:
                text_response = resp.json().get("message", {}).get("content", "").strip()
            else:
                log(f"Ollama Error: {resp.status_code} - {resp.text}")
                return None

        except Exception as e:
            log(f"Ollama Connection Error: {e}")
            return None
    
    else: # Default Gemini
        if not model:
            # simple fallback if gemini not configured
            if "disk" in instruction.lower(): return ["df -h"]
            return None
            
        try:
            # Send everything to Gemini
            total_prompt = [prompt_text] + content_parts
            response = model.generate_content(total_prompt)
            
            # 📊 Token Tracking
            try:
                usage = response.usage_metadata
                if usage:
                    t_in = usage.prompt_token_count
                    t_out = usage.candidates_token_count
                    t_total = usage.total_token_count
                    
                    usage_file = "token_usage.json"
                    data = {"total": 0, "in": 0, "out": 0}
                    
                    if os.path.exists(usage_file):
                        with open(usage_file, "r") as f:
                            try: data = json.load(f)
                            except: pass
                    
                    data["total"] += t_total
                    data["in"] += t_in
                    data["out"] += t_out
                    
                    with open(usage_file, "w") as f:
                        json.dump(data, f)
            except Exception as e:
                log(f"Token tracking error: {e}")

            text_response = response.text.replace('`', '').strip()
        except Exception as e:
            log(f"Gemini Error: {e}")
            return None

    # Common Cleanup (for both providers)
    if not text_response: return []
    
    # Handle cases where AI puts <br> instead of newline
    text_response = text_response.replace('<br>', '\n').replace('<br/>', '\n')

    # clean markdown code blocks
    lines = text_response.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Remove markdown fences
        if line.startswith("```"): continue
        # Remove single backticks
        line = line.replace("`", "")
        # Remove "bash" or "sh" if it's the only content (common artifact)
        if line.lower() in ["bash", "sh", "shell", "zsh"]: continue
        
        if line:
            cleaned_lines.append(line)
            
    return cleaned_lines

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
