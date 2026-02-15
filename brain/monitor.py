import os
import time
import subprocess
import requests
import json
import platform
import google.generativeai as genai
from dotenv import load_dotenv

try:
    from memory import Memory
    brain_memory = Memory()
except Exception as e:
    print(f"⚠️ Memory Init Warning: {e}")
    brain_memory = None

# Move back to project root so commands execute in correct context
# but only if we are in the 'brain' subdirectory
if os.path.basename(os.getcwd()) == "brain":
    os.chdir("..")
    print(f"[Monitor] Moved to root: {os.getcwd()}")

# Load environment variables from .env
# This will now load from brain/.env because dotenv search logic? 
# No, let's be explicit.
load_dotenv("brain/.env")

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
    
    username = os.getenv("USER", "User")
    home_dir = os.path.expanduser("~")
    
    # Context Retrieval
    context_str = ""
    if brain_memory:
        try:
            hits = brain_memory.recall(instruction, n_results=3)
            if hits:
                context_str = "\n\n🧠 Previous Relevant Context:\n" + "\n".join(hits)
        except Exception as e:
            log(f"Context error: {e}")
    
    prompt_text = f"""
    You are an AI bridge. You translate natural language to safe bash commands.
    
    ENVIRONMENT CONTEXT:
    - You are running inside a Linux Container.
    - The User's HOST Home Directory is mounted at: /host_home
    - Downloads: /host_home/Downloads
    - Documents: /host_home/Documents
    - If user asks for "Downloads", use `/host_home/Downloads`.
    
    CRITICAL FILE HANDLING RULES:
    1. If the user sends a file/image and says 'save it' or similar:
       - THE SOURCE IS: '{media_path}'
       - THE DESTINATION IS: Whatever path the user mentioned (e.g /host_home/Downloads).
       - COMMAND MUST BE: `mv {media_path} <destination>`
    
    2. NEVER SWAP THE DIRECTION. The file at {media_path} is the one you must move.
    3. Use absolute paths.
    4. Respond ONLY with safe bash commands, ONE PER LINE. No explanation.
    5. CWD: {os.getcwd()} | Home: {home_dir} | Host Home: /host_home
    {context_str}
    """
    
    content_parts = [f"INSTRUCTION: {instruction}"]
    
    if media_path and os.path.exists(media_path):
        ext = os.path.splitext(media_path)[1].lower()
        is_audio = ext in ['.ogg', '.mp3', '.wav', '.m4a']
        is_visual = ext in ['.jpg', '.jpeg', '.png', '.webp']
        
        log(f"📂 Processing Media: {media_path}")

        try:
            if model and (is_audio or is_visual):
                # Upload to Gemini so it has visual/audio context
                media_file = genai.upload_file(path=media_path)
                content_parts.append(media_file)
        except Exception as e:
            log(f"Media upload error: {e}")
    
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    current_model = os.getenv("OLLAMA_MODEL", "gemma:2b") if provider == "ollama" else "gemini"
    system_os = platform.system()
    
    
    text_response = ""
    
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
            
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            if not ollama_host.startswith("http"): ollama_host = f"http://{ollama_host}"

            resp = requests.post(f"{ollama_host}/api/chat", json=payload, timeout=30)
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

    # Memory Storage
    if brain_memory and text_response:
        try:
            brain_memory.remember(instruction, "user", {"cwd": os.getcwd()})
            brain_memory.remember(text_response, "ai", {"cwd": os.getcwd()})
        except Exception as e:
            log(f"Memory Save Error: {e}")

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
    # 3. Fallback
    error_detail = ""
    if command_list is None: error_detail = " (AI returned None - Check API Key/Model/Logs)"
    return f"I received: '{instruction}'. I couldn't safely translate this commands{error_detail}. Try 'sh: <command>'.\n[INTERNAL DEBUG]: Check /tmp/satele_dcaric.log"

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
