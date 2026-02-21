import os
import sys
import time
import datetime
import subprocess

# Determine and store the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add local lib to path for all dependencies
lib_path = os.path.join(PROJECT_ROOT, "lib")
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.append(lib_path)

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


from google import genai
import re
from dotenv import load_dotenv


# Load environment variables from consolidated satele.config
# Prioritize local brain copy to bypass root permission issues
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "satele.config")
if not os.path.exists(env_path):
    env_path = os.path.join(PROJECT_ROOT, "satele.config")

# Check /tmp as an emergency fallback
if not os.path.exists(env_path) or not os.access(env_path, os.R_OK):
    tmp_path = "/tmp/satele.config"
    if os.path.exists(tmp_path):
        env_path = tmp_path

if os.path.exists(env_path) and os.access(env_path, os.R_OK):
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
try:
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))
except (ValueError, TypeError):
    POLL_INTERVAL = 2
if POLL_INTERVAL < 0.5: POLL_INTERVAL = 0.5 # Safety minimum

# Initialize Gemini if key is available
client = None
gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if GOOGLE_API_KEY:
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        log(f"🧠 Using Gemini Model (genai SDK): {gemini_model_name}")
        log_brain = "🧠 AI Brain (Gemini v2) Active"
    except Exception as e:
        log(f"❌ Failed to init google-genai Client: {e}")
        client = None
        log_brain = "⚠️ Gemini SDK Init Failed"
else:
    client = None
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
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        return (result.stdout + result.stderr).strip() or "Success (No output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 180 seconds. The task might be too complex or Malgus is still thinking."
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
                    
                    # Extract ALL commands (look for python3 commands in backticks)
                    # Match both inline and multiline code blocks
                    all_matches = re.finditer(r'`(python3\s+[^`]+)`', content, re.MULTILINE)
                    commands = []
                    for match in all_matches:
                        cmd_text = match.group(1).strip()
                        # Ensure absolute paths for .agent/skills
                        if ".agent/skills/" in cmd_text:
                            cmd_text = cmd_text.replace(".agent/skills/", os.path.join(PROJECT_ROOT, ".agent/skills/"))
                        elif "brain/" in cmd_text:
                            cmd_text = cmd_text.replace("brain/", os.path.join(PROJECT_ROOT, "brain/"))
                        commands.append(cmd_text)
                    
                    if desc and commands:
                        skills_context += f"- {name}: {desc}\n"
                        for c in commands:
                            skills_context += f"  COMMAND: {c}\n"
                        found_any = True
                        log(f"📦 Loaded skill: {name} ({len(commands)} commands)")
    except Exception as e:
        log(f"Error loading skills: {e}")
    
    if found_any:
        log("✅ Loaded Skills Context with absolute paths.")
    return skills_context if found_any else ""

def ai_interpret(instruction, media_path=None):
    """
    [v2.2] Uses Gemini or Ollama to translate natural language into a bash command.
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
    5. FOCUS ON RELEVANCE: Generate commands ONLY for the current instruction. Do NOT include other skills (like trading monitor or status checks) unless explicitly asked in the instruction.
    6. IGNORE IRRELEVANT LOGS: If "Previous Relevant Context" contains unrelated tasks (like trading), ignore them. Only use context that helps fulfill the CURRENT instruction.
    7. UTILITY COMMANDS: 
       - If asked for "current path" or "where am I", use `pwd`.
       - If asked for "time", use `date`.
       - If asked for "who am I", use `whoami`.
       - For general questions about your status, name, or what you are doing, use an `echo` command with a helpful, personable response. Your name is {os.getenv('BOT_TRIGGER', 'Satele').capitalize()}. (Example: `echo "Hello! I am {os.getenv('BOT_TRIGGER', 'Satele').capitalize()}, your AI assistant. I'm currently monitoring your system and ready to help!"`).
    8. SKILLS TAKE PRECEDENCE: If a command is listed in "AVAILABLE SKILLS" that matches the user's intent, YOU MUST USE THAT EXACT COMMAND WITH ALL PROVIDED ARGUMENTS/PATHS.
    7. NO HALLUCINATION: If the user asks for Gmail and the command provided is `python3 .../gmail_tool.py`, DO NOT output `gmail_tool.py` or `Gmail Search`.
    8. RESULTS AS COMMANDS: If the user asks to "Summarize", "Analyze", or asks for **specific details/info/numbers** from a source (like an email), use the command that fetches the FULL content (e.g., `python3 .../gmail_tool.py fetch_full ...`).
    9. NO PLACEHOLDERS: NEVER use generic or placeholder emails like 'your-email@gmail.com' in Gmail commands. If the user didn't specify a sender, OMIT the "sender" field entirely.
    10. PRECISION: Respect numerical quantities. If the user asks for "the last one", use `limit: 1`. If "last 3", use `limit: 3`. Do NOT return more data than requested.
    11. CONTENT FILTERING: If the user asks for a specific section/line/data point from an email (like "Final Equity" or "Total Capital"), add a "filter" parameter to fetch_full with the key term (e.g., `"filter": "final equity"`). This prevents dumping entire emails.
    12. STATUS CONTEXT: If you need to mention where you are or what you are doing, you can combine commands like `echo "I'm working in $(pwd) and ready for tasks."`
    13. ATTACHMENT MODE: If user asks for a result "as an attachment", "as a file", "as a document", or asks for a "log" or "report" of a search/command, you MUST run the command, redirect output (`>`) to a temp file in `/tmp/`, and THEN use `UPLOAD:`. Example: `find . -name "*pattern*" > /tmp/search_log.txt && echo "UPLOAD:/tmp/search_log.txt"`.
    14. NO TOOL UPLOADING: NEVER use `UPLOAD:` on scripts located in `.agent/skills/`. If the user asks for a "result" or "help", they want the OUTPUT of the script, not the script file itself.
    
    CRITICAL FILE HANDLING RULES:
    - If saving a file: `mv {media_path} <destination>`
    - To send a file: `UPLOAD:<filename>`
    - NEVER use `UPLOAD:` on a directory (like `UPLOAD:.` or `UPLOAD:/path/to/folder`). It MUST be a single file.
    - If a user asks to "send/summarize" something that a SKILL already handles, DO NOT add extra `UPLOAD:` commands. Trust the skill script to produce the correct output.
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
            if client and (is_audio or is_visual):
                # Upload to Gemini so it has visual/audio context
                media_file = client.files.upload(path=media_path)
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
        try:
            # Send everything to Gemini
            total_prompt = [prompt_text] + content_parts
            response = client.models.generate_content(
                model=gemini_model_name,
                contents=total_prompt
            )
            
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
    Second pass: Performs specific data extraction or analysis on the tool output.
    """
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    log(f"🧠 Reasoning Pass ({provider.upper()}): Extracting answer...")

    # Prune output if it's too long
    if len(tool_output) > 12000:
        tool_output = tool_output[:12000] + "...(truncated)..."

    # Aggressive extraction prompt
    extraction_prompt = f"""
    [DATA]
    {tool_output}
    
    [INSTRUCTION]
    {instruction}
    
    [RULES]
    1. EXTRAC T the exact answer from the [DATA] above.
    2. If a specific number or status is requested (like equity, balance, or capital), provide ONLY that number/sentence.
    3. NO summaries. NO "Here is your data". NO market analysis.
    4. If the information isn't in the DATA, say "Not found in data."
    
    ANSWER (ONE SHORT SENTENCE):"""

    try:
        if provider == "ollama":
            import requests
            model_name = os.getenv("OLLAMA_MODEL", "gemma:2b")
            payload = {
                "model": model_name,
                "prompt": extraction_prompt,
                "stream": False,
                "options": {"num_predict": 100} # Cap response length
            }
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
            res_text = resp.json().get("response", "Error").strip()
        else:
            if not client:
                return f"⚠️ Analysis requires key. Raw:\n{tool_output}"
            response = client.models.generate_content(
                model=gemini_model_name,
                contents=extraction_prompt
            )
            res_text = response.text.strip()

        # Final Guard: If the AI was still too chatty, force it down
        if len(res_text) > 400:
            res_text = res_text[:400] + "..."
            
        return f"[v2.2] {res_text}"

    except Exception as e:
        log(f"Reasoning Error: {e}")
        return f"[Error] {tool_output[:500]}..."

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
                if os.path.isdir(raw_path):
                    msg = f"⚠️ Satele Error: '{raw_path}' is a directory. I cannot upload folders, only individual files."
                    log(msg)
                    full_output.append(msg)
                    continue
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
                
                # Filter UPLOAD lines from 'out' to prevent invalid ones from leaking through
                lines = out.split("\n")
                clean_lines = []
                for line in lines:
                    if line.strip().startswith("UPLOAD:"):
                        potential_path = line.strip().split(":", 1)[1].strip()
                        if os.path.isfile(potential_path):
                            return f"UPLOAD: {potential_path}"
                        else:
                            # Log warning but skip adding the line
                            msg = f"⚠️ Satele skipped upload of '{potential_path}' (not a file)."
                            log(msg)
                            clean_lines.append(msg)
                    else:
                        clean_lines.append(line)
                out = "\n".join(clean_lines)
            
            full_output.append(out)
            
        combined_result = "\n".join(full_output)
        
        # 🧠 COGNITIVE PASS: If the user asked for summary/analysis/specific detail AND we have data
        import re
        analysis_keywords = [r"\bsummarize\b", r"\banalyze\b", r"\bextract\b", r"\bwhat\b", r"\bhow\b", r"\bfeedback\b", r"\bstatus\b", r"\bis\b", r"\bequity\b", r"\bbalance\b", r"\btotal\b", r"\bworth\b"]
        should_reason = any(re.search(k, instruction.lower()) for k in analysis_keywords)

        if should_reason and len(combined_result) > 20:
            # Check for data markers (case-insensitive) or substantial text
            res_lower = combined_result.lower()
            if "email id:" in res_lower or "subject:" in res_lower or "from:" in res_lower or len(combined_result) > 600:
                combined_result = ai_reason(instruction, combined_result)

        # Prevent huge payloads
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
                        elif instruction and re.search(r"(?i)\b(restart|reboot)\b", instruction):
                            log("♻️ Internal Restart Triggered.")
                            result = "♻️ **Restarting Satele.** I will be back in a moment..."
                            # Send response BEFORE killing ourselves
                            requests.post(
                                f"{BASE_URL}/report-result",
                                json={"id": task_id, "output": result},
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                                timeout=5
                            )
                            # Actual restart via background one-liner to ensure reliability
                            satele_path = os.path.join(PROJECT_ROOT, "satele")
                            os.system(f"nohup bash -c 'sleep 2; \"{satele_path}\" stop; \"{satele_path}\" start' > /dev/null 2>&1 &")
                            task_processed = True
                        elif instruction and re.search(r"(?i)\b(git pull|update|pull changes)\b", instruction):
                            log("📥 Internal Git Pull Triggered.")
                            satele_path = os.path.join(PROJECT_ROOT, "satele")
                            out = run_shell(f"\"{satele_path}\" gitpull")
                            result = f"📥 **System Update:**\n{out}"
                            requests.post(
                                f"{BASE_URL}/report-result",
                                json={"id": task_id, "output": result},
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                                timeout=5
                            )
                            task_processed = True
                        elif instruction and re.search(r"(?i)(status|alive)", instruction):
                            log("📊 Internal Status Check Triggered.")
                            satele_path = os.path.join(PROJECT_ROOT, "satele")
                            out = run_shell(f"\"{satele_path}\" status")
                            result = f"📊 **System Status:**\n{out}"
                            requests.post(
                                f"{BASE_URL}/report-result",
                                json={"id": task_id, "output": result},
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                                timeout=5
                            )
                            task_processed = True
                        elif instruction and re.search(r"(?i)\b(run command|execute command)\b", instruction):
                            log("🏃 Direct Run Command Triggered.")
                            # Extract command after 'run command' or 'execute command' (handles '-' or ':')
                            clean_cmd = re.sub(r"(?i)\b(run command|execute command)\s*([-:]\s*)?", "", instruction).strip()
                            
                            if clean_cmd.startswith("satele "):
                                sub_cmd = clean_cmd[7:].strip()
                                log(f"🏃 Running Satele sub-command: {sub_cmd}")
                                satele_path = os.path.join(PROJECT_ROOT, "satele")
                                out = run_shell(f"\"{satele_path}\" {sub_cmd}")
                                result = f"🧾 **Satele Printout ({sub_cmd}):**\n{out}"
                            elif clean_cmd:
                                log(f"🏃 Running Shell command: {clean_cmd}")
                                out = run_shell(clean_cmd)
                                result = f"📑 **Shell Execution:**\n{out}"
                            else:
                                result = "⚠️ No command specified. Try 'run command - satele help'."

                            requests.post(
                                f"{BASE_URL}/report-result",
                                json={"id": task_id, "output": result},
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                                timeout=5
                            )
                            task_processed = True
                        elif instruction and re.search(r"(?i)send me printout", instruction):
                            log("📄 Printout request triggered.")
                            # Clean up the instruction to get the actual command
                            # Handles "send me printout - satele help", "send me printout satele help", etc.
                            clean_cmd = re.sub(r"(?i)send me printout\s*([-:]\s*)?", "", instruction).strip()
                            
                            if clean_cmd.startswith("satele "):
                                sub_cmd = clean_cmd[7:].strip()
                                log(f"🏃 Running Satele sub-command: {sub_cmd}")
                                satele_path = os.path.join(PROJECT_ROOT, "satele")
                                out = run_shell(f"\"{satele_path}\" {sub_cmd}")
                                result = f"🧾 **Satele Printout ({sub_cmd}):**\n{out}"
                            elif clean_cmd:
                                log(f"🏃 Running Shell command: {clean_cmd}")
                                out = run_shell(clean_cmd)
                                result = f"📑 **Shell Printout:**\n{out}"
                            else:
                                result = "⚠️ No command specified for printout. Try 'send me printout - satele help'."

                            requests.post(
                                f"{BASE_URL}/report-result",
                                json={"id": task_id, "output": result},
                                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                                timeout=5
                            )
                            task_processed = True
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

            # Consistent sleep regardless of task processing to prevent network flood
            time.sleep(POLL_INTERVAL)

                
        except Exception as e:
            log(f"❌ Monitor Loop Error: {e}")
            import traceback
            log(traceback.format_exc())
            time.sleep(5)

if __name__ == "__main__":
    monitor_loop()
