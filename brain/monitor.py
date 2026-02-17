import os
import time
import datetime
import subprocess
import requests
import json
import platform

# Compatibility for Python < 3.10
try:
    import importlib.metadata as metadata
    if not hasattr(metadata, "packages_distributions"):
        def packages_distributions():
            return {}
        metadata.packages_distributions = packages_distributions
except ImportError:
    pass

def log(msg):
    print(f"[Monitor] {msg}", flush=True)

import google.generativeai as genai
import re
from dotenv import load_dotenv


# Determine and store the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from consolidated satele.config
# Prioritize local brain copy to bypass root permission issues
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "satele.config")
if not os.path.exists(env_path):
    env_path = os.path.join(PROJECT_ROOT, "satele.config")

if os.path.exists(env_path):
    load_dotenv(env_path)
    log(f"📝 Config loaded from: {env_path}")
else:
    log(f"⚠️ Primary config not found or inaccessible: {env_path}")
    # Fallback to current environment if config is missing
    load_dotenv() 

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
    log(f"🏠 Set Project Root: {os.getcwd()}")

# Environment variables loaded at top level


# Configuration
BASE_URL = os.getenv("REMOTE_BRIDGE_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("BRIDGE_SECRET_KEY", "default-secret-key")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))

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

log(f"🌍 Startup Environment: Provider={os.getenv('AI_PROVIDER')} | Bot={os.getenv('BOT_TRIGGER')}")

def run_shell(cmd):
    try:
        # Prevent dangerous or interactive commands
        if any(bad in cmd for bad in ["> /dev/sda", "rm -rf /", "mkfs"]):
            return "Error: Dangerous command blocked."
            
        # Ensure we use the same python interpreter as the monitor (venv)
        import sys
        if cmd.strip().startswith("python3"):
            cmd = cmd.replace("python3", sys.executable, 1)
        elif cmd.strip().startswith("python"):
            cmd = cmd.replace("python", sys.executable, 1)
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return (result.stdout + result.stderr).strip() or "Success (No output)"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def get_skills_context(instruction=None):
    # Temporarily bypass indexer due to slow model download
    return get_skills_context_legacy()

def get_skills_context_legacy():
    """Legacy skill loading (fallback if indexer fails)"""
    skills_dir = os.path.join(PROJECT_ROOT, ".agent", "skills")

    if not os.path.exists(skills_dir):
        log(f"⚠️ Skills directory not found: {skills_dir}")
        return ""
    
    skills_context = "\n🚀 AVAILABLE SKILLS & CUSTOM SCRIPTS:\n"
    found_any = False
    
    try:
        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
            if os.path.exists(skill_path):
                with open(skill_path, "r") as f:
                    content = f.read()
                    desc = ""
                    name = skill_name
                    # Extract metadata from YAML-ish frontmatter
                    for line in content.split("\n"):
                        if line.startswith("description:"):
                            desc = line.replace("description:", "").strip()
                        if line.startswith("name:"):
                            name = line.replace("name:", "").strip()
                    
                    # Extract ALL commands (support python3, bash, or direct shell commands like ls, find, cat, head, realpath)
                    all_matches = re.finditer(r'`((?:python3|bash|ls|find|cat|head|realpath) [^`]+)`', content)
                    commands = []
                    for match in all_matches:
                        cmd_text = match.group(1)
                        # Ensure absolute paths
                        if ".agent/skills/" in cmd_text:
                            cmd_text = re.sub(r'\.?agent/skills/', os.path.join(PROJECT_ROOT, ".agent/skills/"), cmd_text)
                        elif "brain/" in cmd_text:
                            cmd_text = re.sub(r'\.?brain/', os.path.join(PROJECT_ROOT, "brain/"), cmd_text)
                        commands.append(cmd_text)
                    
                    if desc and commands:
                        skills_context += f"- {name}: {desc}\n"
                        for c in commands:
                            skills_context += f"  COMMAND: {c}\n"
                        found_any = True
    except Exception as e:
        log(f"Error loading skills: {e}")
    
    if found_any:
        log("✅ Loaded Skills Context with absolute paths.")
    return skills_context if found_any else ""

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
    
    
    # Dynamic Environment Detection
    is_docker = os.path.exists("/host_home")
    if is_docker:
        env_context = """
    ENVIRONMENT CONTEXT:
    - You are strictly running inside a Docker Container.
    - INTERNAL CONTAINER ROOT: /app (Do not use this unless explicitly asked for internal files)
    - REAL USER FILES ARE MOUNTED AT: /host_home
    - USER HOME: /host_home
    - DOWNLOADS: /host_home/Downloads
    - DOCUMENTS: /host_home/Documents
    
    CRITICAL: 
    - When user says "home" or "cd ~", you MUST use `/host_home`.
    - When user asks for "current path", show both internal (`/app`) and external (`/host_home`) if relevant.
    - IGNORE /root or /app/home.
    """
        example_dest = "/host_home/Downloads"
    else:
        env_context = f"""
    ENVIRONMENT CONTEXT:
    - You are running natively on {platform.system()}.
    - User Home: {home_dir}
    - Downloads: {home_dir}/Downloads"""
        example_dest = f"{home_dir}/Downloads"
    
    # Get relevant skills using semantic search
    skills_str = get_skills_context(instruction)

    prompt_text = f"""
    You are an AI bridge. You translate natural language to safe bash commands.
    {env_context}
    {skills_str}
    
    CRITICAL RULES:
    1. Respond ONLY with safe bash commands, ONE PER LINE. No explanation. No markdown.
    2. USE ABSOLUTE PATHS for all scripts and tools mentioned in "AVAILABLE SKILLS".
    3. YOUR CURRENT LOCATION (CWD): {os.getcwd()}
    4. PRESERVE PATH CASE EXACTLY.
    5. UTILITY COMMANDS: 
       - If asked for "current path" or "where am I", use `pwd`.
       - If asked for "time", use `date`.
       - If asked for "who am I", use `whoami`.
    6. SKILLS TAKE PRECEDENCE: If a command is listed in "AVAILABLE SKILLS" that matches the user's intent, YOU MUST USE THAT EXACT COMMAND WITH ALL PROVIDED ARGUMENTS/PATHS.
    7. NO HALLUCINATION: If the user asks for Gmail and the command provided is `python3 .../gmail_tool.py`, DO NOT output `gmail_tool.py` or `Gmail Search`.
    8. RESULTS AS COMMANDS: If the user asks to "Summarize" or "Analyze", use the command that fetches the FULL content (e.g., `python3 .../gmail_tool.py fetch_full ...`).
    9. NO PLACEHOLDERS: NEVER use generic or placeholder emails like 'your-email@gmail.com' in Gmail commands. If the user didn't specify a sender, OMIT the "sender" field entirely.
    10. PRECISION: Respect numerical quantities. If the user asks for "the last one", use `limit: 1`. If "last 3", use `limit: 3`. Do NOT return more data than requested.
    
    CRITICAL FILE HANDLING RULES:
    - If saving a file: `mv {media_path} <destination>`
    - To send a file: `UPLOAD:<filename>`
    - To find latest file: `echo "UPLOAD:$(find . -maxdepth 1 -type f -not -path '*/.*' -exec stat -f "%m %N" {{}} + | sort -rn | head -1 | cut -d' ' -f2- | xargs realpath)"`
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
    
    log(f"🧠 AI Provider: {provider} | Model: {current_model}")
    
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
            log(f"Ollama Connection Error: {e}. Falling back to Cloud Gemini...")
            # Fallback to Gemini handled below
            provider = "gemini" 
    
    if provider == "gemini" or not text_response: # Fallback or direct Gemini
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
            log(f"❌ Gemini Error: {e}")
            if hasattr(e, 'message'): log(f"❌ Gemini Details: {e.message}")
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

def ai_reason(instruction, tool_output):
    """
    Second pass: Performs analysis/summarization on the raw tool output using the active provider.
    """
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    
    # Prune output if it's too long for the model
    if len(tool_output) > 15000:
        tool_output = tool_output[:15000] + "...(truncated for analysis)..."

    log(f"🧠 Reasoning Pass ({provider.upper()}): Analyzing output...")
    
    prompt = f"Analyze this data and answer: {instruction}\n\nDATA:\n{tool_output}"
    
    try:
        if provider == "ollama":
            import requests
            model_name = os.getenv("OLLAMA_MODEL", "gemma:2b")
            # Minimal reasoning prompt for smaller local models
            sys_msg = "You are a concise analyst. Summarize the provided data to answer the user request."
            payload = {
                "model": model_name,
                "prompt": f"{sys_msg}\n\n{prompt}",
                "stream": False
            }
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
            return resp.json().get("response", "Error: No response from Ollama").strip()
        else:
            if not GOOGLE_API_KEY:
                return f"⚠️ Summary requires GOOGLE_API_KEY. Raw output:\n{tool_output}"
            response = model.generate_content(f"Summarize/Analyze to answer: {instruction}\n\nDATA:\n{tool_output}")
            return response.text.strip()
    except Exception as e:
        log(f"Reasoning Error: {e}")
        return tool_output

def process_instruction(instruction, media_path=None):
    log(f"📩 Processing: {instruction} (Media: {media_path is not None})")
    
    # 1. Direct Shell Access (Text only - supports multi-command with ;)
    if not media_path and instruction.lower().startswith("sh:"):
        cmd = instruction[3:].strip()
        out = run_shell(cmd)
        if out.strip().upper().startswith("UPLOAD:"):
            return out.strip()
        return f"Executing Raw: {cmd}\n---\n{out}"

    # 2. AI Interpretation (Text or Voice) -> Returns LIST of commands
    command_list = ai_interpret(instruction, media_path)
    
    if command_list and command_list[0] != "UNSUPPORTED":
        full_output = []
        log(f"🤖 AI suggested plan: {command_list}")
        
        for cmd in command_list:
            # Skip comments or empty lines
            if not cmd or cmd.startswith("#"): continue
            
            # FILE UPLOAD INTERCEPT
            if cmd.upper().startswith("UPLOAD:"):
                # ... [UPLOAD logic remains same] ...
                parts = cmd.split(":", 1)
                raw_path = parts[1].strip()
                if "*" in raw_path or "?" in raw_path:
                    import glob
                    matches = glob.glob(raw_path) if os.path.isabs(raw_path) else glob.glob(os.path.join(os.getcwd(), raw_path))
                    if matches:
                        matches.sort(key=os.path.getmtime, reverse=True)
                        raw_path = matches[0]
                if not os.path.isabs(raw_path):
                    raw_path = os.path.abspath(os.path.join(os.getcwd(), raw_path))
                
                def resolve_case_insensitive(path):
                    if os.path.exists(path): return path
                    parts = path.lstrip(os.path.sep).split(os.path.sep)
                    current = os.path.sep if path.startswith(os.path.sep) else ""
                    for part in parts:
                        if not part: continue
                        attempt = os.path.join(current, part)
                        if os.path.exists(attempt): current = attempt
                        else:
                            if os.path.exists(current) and os.path.isdir(current):
                                try:
                                    for item in os.listdir(current):
                                        if item.lower() == part.lower():
                                            current = os.path.join(current, item); break
                                except: pass
                    return current
                raw_path = resolve_case_insensitive(raw_path)
                return f"UPLOAD: {raw_path}"
            
            # Intercept 'cd'
            if cmd.strip().startswith("cd"):
                try:
                    parts = cmd.strip().split(maxsplit=1)
                    target = os.path.expanduser("~") if len(parts) == 1 else parts[1].strip()
                    if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
                        target = target[1:-1]
                    if target.upper().startswith("CWD:"): target = target[4:].strip()
                    os.chdir(target)
                    out = f"📂 Directory changed to: {os.getcwd()}"
                    log(f"✅ Persistent CD: {os.getcwd()}")
                except Exception as e: out = f"❌ CD Failed: {e}"
            else:
                if cmd.lower().startswith("sh:"): cmd = cmd[3:].strip()
                log(f"➡️ Running: {cmd}")
                out = run_shell(cmd)
                
                # Check for UPLOAD in output
                target_upload_path = None
                for line in out.splitlines():
                    if line.strip().startswith("UPLOAD:"):
                        target_upload_path = line.strip().split(":", 1)[1].strip()
                        break
                if target_upload_path: return f"UPLOAD: {target_upload_path}"
            
            full_output.append(out)
            
        combined_result = "\n".join(full_output)
        
        # 🧠 COGNITIVE PASS: If the user asked for summary/analysis AND we have data
        analysis_keywords = ["summarize", "analyze", "explain", "feedback", "what", "check", "report"]
        if any(k in instruction.lower() for k in analysis_keywords) and len(combined_result) > 20:
            # Check for data markers (case-insensitive) or substantial text
            res_lower = combined_result.lower()
            if "email id:" in res_lower or "subject:" in res_lower or "from:" in res_lower or len(combined_result) > 800:
                combined_result = ai_reason(instruction, combined_result)

        # Prevent huge payloads
        MAX_CHARS = 5000
        if len(combined_result) > MAX_CHARS:
            combined_result = combined_result[:MAX_CHARS] + f"\n\n... (Result truncated at {MAX_CHARS} characters) ..."
            
        return combined_result
        
        # Prevent huge payloads that crash the bridge/WhatsApp
        MAX_CHARS = 5000
        if len(combined_result) > MAX_CHARS:
            log(f"✂️ Truncating result (Length: {len(combined_result)})")
            combined_result = combined_result[:MAX_CHARS] + f"\n\n... (Result truncated at {MAX_CHARS} characters) ..."
            
        return combined_result
    
    # 3. Fallback
    # 3. Fallback
    error_detail = ""
    if command_list is None: error_detail = " (AI returned None - Check API Key/Model/Logs)"
    return f"I received: '{instruction}'. I couldn't safely translate this commands{error_detail}. Try 'sh: <command>'.\n[INTERNAL DEBUG]: Check /tmp/satele_dcaric.log"

def monitor_loop():
    log(f"🚀 Autonomous Monitoring Started... ({log_brain})")
    
    # RESTORE SESSION
    try:
        cwd_file = os.path.join(os.path.dirname(__file__), ".satele_cwd")
        if os.path.exists(cwd_file):
            with open(cwd_file, "r") as f:
                last_wd = f.read().strip()
                if os.path.isdir(last_wd):
                    os.chdir(last_wd)
                    log(f"🔄 Restored Session CWD: {last_wd}")
    except Exception as e:
        log(f"⚠️ Failed to restore session: {e}")

    while True:
        try:
            # now = datetime.datetime.now().strftime("%H:%M:%S")
            # log(f"[{now}] 🔍 Checking for tasks...")
            response = requests.get(
                f"{BASE_URL}/get-task", 
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=5
            )
            
            task_processed = False
            if response.status_code == 200:
                task = response.json()
                if task:
                    task_id = task.get('id')
                    instruction = task.get('instruction')
                    media_path = task.get('media_path')
                    
                    if task_id:
                        log(f"📥 New Task [{task_id}]: {instruction}")
                        
                        # Satele Logic: If the user says "use gravity", we let the Antigravity Agent handle it.
                        if instruction and "use gravity" in instruction.lower():
                            log(f"🧠 Handoff: '{instruction}' -> Letting Antigravity Agent handle this.")
                        else:
                            result = process_instruction(instruction, media_path)
                            
                            requests.post(
                                f"{BASE_URL}/report-result",
                                json={"id": task_id, "output": result},
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                                timeout=5
                            )
                            log(f"✅ Result sent for {task_id}")
                        task_processed = True
            else:
                log(f"⚠️ Server returned status {response.status_code}.")

            if not task_processed:
                time.sleep(POLL_INTERVAL)

                
        except Exception as e:
            log(f"❌ Monitor Loop Error: {e}")
            import traceback
            log(traceback.format_exc())
            time.sleep(5)

if __name__ == "__main__":
    monitor_loop()
