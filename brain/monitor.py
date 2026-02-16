import os
import time
import subprocess
import requests
import json
import platform
import google.generativeai as genai
import re
from dotenv import load_dotenv

# Load environment variables from specific config file
# Using satele_brain.env to avoid MacOS 'Operation not permitted' on .env
env_name = "satele_brain.env"
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), env_name)
load_dotenv(env_path)

try:
    from memory import Memory
    brain_memory = Memory()
except Exception as e:
    print(f"⚠️ Memory Init Warning: {e}")
    brain_memory = None

# Determine and store the project root (where monitor.py is located)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Move back to project root so commands execute in correct context
# but only if we are in the 'brain' subdirectory
if os.path.basename(os.getcwd()) == "brain":
    os.chdir("..")
    log(f"🏠 Set Project Root: {os.getcwd()}")

# Environment variables loaded at top level

def log(msg):
    print(f"[Monitor] {msg}", flush=True)

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

log(f"🌍 Startup Environment: Provider={os.getenv('AI_PROVIDER')} | Bot={os.getenv('BOT_TRIGGER')}")

def run_shell(cmd):
    try:
        # Prevent dangerous or interactive commands
        if any(bad in cmd for bad in ["> /dev/sda", "rm -rf /", "mkfs"]):
            return "Error: Dangerous command blocked."
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return (result.stdout + result.stderr).strip() or "Success (No output)"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def get_skills_context(instruction=None):
    """
    Get relevant skills using semantic search.
    If instruction is provided, returns top 5 most relevant skills.
    Otherwise, returns all skills (for backward compatibility).
    """
    from skill_indexer import get_skill_indexer
    
    try:
        indexer = get_skill_indexer(PROJECT_ROOT)
        
        if instruction:
            # Semantic search for relevant skills
            return indexer.search_skills(instruction, top_k=5)
        else:
            # Return all skills (fallback)
            return indexer.get_all_skills()
    except Exception as e:
        log(f"⚠️ Skill indexer error: {e}")
        # Fallback to old method if indexer fails
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
                    
                    # Extract script usage and convert to absolute path
                    script_usage = ""
                    match = re.search(r'`((?:python3|bash) .agent/skills/([^`]+))`', content)
                    if match:
                        full_cmd = match.group(1)
                        # Extract the command prefix (python3 or bash)
                        cmd_parts = full_cmd.split(' ', 1)
                        cmd_prefix = cmd_parts[0]
                        rel_path = f".agent/skills/{match.group(2)}"
                        abs_path = os.path.join(PROJECT_ROOT, rel_path)
                        script_usage = f"{cmd_prefix} {abs_path}"
                    
                    if desc:
                        skills_context += f"- {name}: {desc}\n"
                        if script_usage:
                            skills_context += f"  COMMAND: {script_usage}\n"
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
    
    CRITICAL FILE HANDLING RULES:
    1. If the user sends a file/image and says 'save it' or similar:
       - THE SOURCE IS: '{media_path}'
       - THE DESTINATION IS: Whatever path the user mentioned (e.g {example_dest}).
       - COMMAND MUST BE: `mv {media_path} <destination>`
    
    2. NEVER SWAP THE DIRECTION. The file at {media_path} is the one you must move.
    3. Use absolute paths for targets outside of your current folder. If referring to your current location (CWD), use `.` or relative paths.
    4. Respond ONLY with safe bash commands, ONE PER LINE. No explanation.
    5. YOUR CURRENT LOCATION (CWD): {os.getcwd()}
    6. FOR GUI APPS (Calculator, Chrome), use `sh: open -a "App Name"`. Do NOT use this for measurement or speed tests.
    7. TO SEND FILES: If the user mentions a specific file (e.g., 'send me html.zip'), use `UPLOAD:<filename>`. Only use search if the user is ambiguous (e.g., 'send me the latest image').
    8. TO FIND LATEST FILE: Use `echo "UPLOAD:$(find . -maxdepth 1 -type f -not -path '*/.*' -exec stat -f "%m %N" {{}} + | sort -rn | head -1 | cut -d' ' -f2- | xargs realpath)"`
    9. VERIFY BEFORE SENDING: Avoid `UPLOAD` on directories. If a search finds a directory, it will fail.
    10. PRESERVE PATH CASE EXACTLY. Do NOT lowercase project names or folder names.
    11. SKILLS TAKE PRECEDENCE: If a command is listed in "AVAILABLE SKILLS" that matches the user's intent, YOU MUST USE THAT COMMAND.
    12. NO DIRECTORY UPLOADS: You cannot use UPLOAD on a directory. For a folder, use `ls -F <path>` or `zip -r folder.zip <path> && echo "UPLOAD:$(realpath folder.zip)"`.
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
                # Split case-insensitively but preserve path casing
                parts = cmd.split(":", 1)
                raw_path = parts[1].strip()
                
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
                    raw_path = os.path.abspath(os.path.join(os.getcwd(), raw_path))
                    log(f"📂 Converting relative path -> '{raw_path}'")

                # --- RECURSIVE CASE CORRECTION ---
                # Fixed: Handle deep paths like /users/dcaric/antigravitymessages/media/x
                def resolve_case_insensitive(path):
                    if os.path.exists(path): return path
                    
                    parts = path.lstrip(os.path.sep).split(os.path.sep)
                    current = os.path.sep if path.startswith(os.path.sep) else ""
                    
                    for part in parts:
                        if not part: continue
                        found = False
                        # Check exist with current casing
                        attempt = os.path.join(current, part)
                        if os.path.exists(attempt):
                            current = attempt
                            found = True
                        else:
                            # Search parent for a case-insensitive match
                            if os.path.exists(current) and os.path.isdir(current):
                                try:
                                    for item in os.listdir(current):
                                        if item.lower() == part.lower():
                                            current = os.path.join(current, item)
                                            found = True
                                            break
                                except: pass
                        
                        if not found:
                             return path # Give up, return original
                    return current

                raw_path = resolve_case_insensitive(raw_path)
                log(f"🔗 Final Resolved Path: {raw_path}")
                
                return f"UPLOAD: {raw_path}"
            
            # Intercept 'cd' to persist directory changes in the Python process
            if cmd.strip().startswith("cd"):
                try:
                    # Parse path
                    parts = cmd.strip().split(maxsplit=1)
                    if len(parts) == 1:
                        target = os.path.expanduser("~")
                    else:
                        target = parts[1].strip()
                        # Clean quotes
                        if (target.startswith('"') and target.endswith('"')) or \
                           (target.startswith("'") and target.endswith("'")):
                            target = target[1:-1]

                        # Clean artifacts like "CWD:" or "Directory"
                        if target.upper().startswith("CWD:"):
                             target = target[4:].strip()
                        
                        # --- DOCKER PATH CORRECTION ---
                        # If user types 'cd home' or 'cd host' inside docker, force it to /host_home
                        if os.path.exists("/host_home"):
                            if target.lower() in ["home", "host", "~", "users"]:
                                target = "/host_home"
                            elif target.lower() == "root":
                                target = "/"
                            else:
                                # Try to resolve relative to current dir first, then host_home
                                try_local = os.path.abspath(os.path.join(os.getcwd(), target))
                                try_host = os.path.abspath(os.path.join("/host_home", target))
                                
                                if os.path.isdir(try_local):
                                    target = try_local
                                elif os.path.isdir(try_host):
                                    target = try_host
                                else:
                                     target = os.path.expanduser(target)
                        else:
                             target = os.path.expanduser(target)
                    
                    os.chdir(target)
                    out = f"📂 Directory changed to: {os.getcwd()}"
                    if os.path.exists("/host_home") and os.getcwd().startswith("/host_home"):
                         out += " (On Host System)"
                    log(f"✅ Persistent CD: {os.getcwd()}")
                except Exception as e:
                     out = f"❌ CD Failed: {e}"
                
                # Save CWD for persistence across restarts
                try:
                    with open(os.path.join(os.path.dirname(__file__), ".satele_cwd"), "w") as f:
                        f.write(os.getcwd())
                except: pass

            else:
                # Clean up sloppy AI prefixes
                if cmd.lower().startswith("sh:"):
                    cmd = cmd[3:].strip()
                
                log(f"➡️ Running: {cmd}")
                out = run_shell(cmd)
                
                # Check if the command output contains UPLOAD directive (Scan all lines)
                target_upload_path = None
                for line in out.splitlines():
                    if line.strip().upper().startswith("UPLOAD:"):
                        target_upload_path = line.strip().split(":", 1)[1].strip()
                        break
                
                if target_upload_path:
                    log(f"📤 Upload detected in command output: {target_upload_path}")
                    # Validate that the path is a file (not a directory)
                    if os.path.isdir(target_upload_path):
                        log(f"⚠️ UPLOAD failed: {target_upload_path} is a directory.")
                        return f"❌ Cannot upload a directory: {target_upload_path}\nUse 'ls' to see contents or zip it first."
                    if not os.path.isfile(target_upload_path):
                        log(f"⚠️ UPLOAD failed: {target_upload_path} does not exist or is not a file.")
                        # If the path looks like an error message, return the whole output
                        if " " in target_upload_path and len(target_upload_path) > 50:
                             return out.strip()
                        return f"❌ File not found: {target_upload_path}\n(Full output was: {out.strip()})"
                    
                    # Return the UPLOAD directive for the bridge
                    return f"UPLOAD: {target_upload_path}"
            
            full_output.append(f"> {cmd}\n{out}")
            
        combined_result = "\n\n".join(full_output)
        
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
            log("🔍 Polling for tasks...")
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
                
                log(f"📥 New Task [{task_id}]: {instruction}")
                
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
