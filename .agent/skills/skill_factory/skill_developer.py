import os
import sys
import json
import re
import subprocess
import shutil
import tempfile
from datetime import datetime
import google.generativeai as genai_legacy # For fallback
from google import genai

# Load Config
def get_config():
    config = {}
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = current_dir
    
    # Climb up to find satele.config
    while project_root != "/":
        if os.path.exists(os.path.join(project_root, "satele.config")):
            break
        project_root = os.path.dirname(project_root)
    
    # If not found, use a fallback (4 levels up from current file in .agent/skills/skill_factory/)
    if project_root == "/":
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    paths = ["satele.config", "brain/satele.config"]
    for p in paths:
        full_p = os.path.join(project_root, p)
        if os.path.exists(full_p):
            try:
                with open(full_p, "r") as f:
                    for line in f:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            config[k] = v
            except: pass
    
    # Add local lib to path for google-genai
    lib_path = os.path.join(project_root, "lib")
    if os.path.exists(lib_path) and lib_path not in sys.path:
        sys.path.append(lib_path)
        
    return config, project_root

def log(msg):
    print(f"🏗️ [Skill Factory] {msg}", flush=True)

def generate_skill_content(description, api_key, model_name):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are Satele's Brain. You are designing a NEW skill for yourself.
    
    SKILL DESCRIPTION: {description}
    
    RULES FOR OUTPUT:
    1. Respond ONLY with a valid JSON object. No other text or markdown outside the JSON.
    2. The JSON object must have three keys: 'python_code', 'skill_md', and 'suggested_folder_name'.
    3. 'suggested_folder_name': Create a short, descriptive folder name (lowercase, underscores).
    4. 'python_code': The full Python script. 
       - CRITICAL: DO NOT use APIs that require an API Key or registration (like Spoonacular, OpenWeatherMap, etc.). 
       - If the task requires specialized info (like recipes), the script can use the AI's internal knowledge to 'generate' the result or use a public, keyless URL/Scraper.
       - Use 'urllib' (native) for web requests. Handle SSL certificates safely.
    5. 'skill_md': The full SKILL.md content. Include a '## Tools' section.
    6. Ensure the logic matches the DESCRIPTION exactly.
    """
    
    EXAMPLE_STRUCTURE = """
    {
      "suggested_folder_name": "weather_checker",
      "python_code": "import os\\nimport sys\\n...",
      "skill_md": "---\\nname: Weather Checker\\ndescription: ...\\n---\\n..."
    }
    """
    
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    text = response.text
    
    # Extract JSON with improved robustness
    try:
        # 1. Look for ```json ... ``` block
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if not json_match:
            # 2. Look for any {...} structure
            json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        
        if json_match:
            # Use strict=False to handle potential invalid control characters/escapes
            return json.loads(json_match.group(1), strict=False)
        else:
            raise Exception("No JSON found in Gemini response")
            
    except Exception as e:
        log(f"⚠️ JSON Parse Error: {e}")
        # Final fallback: desperate attempt to clean common Gemini JSON artifacts
        try:
            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text, strict=False)
        except:
            raise Exception(f"Failed to parse Gemini response as JSON. Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 skill_developer.py \"description\"")
        return

    description = sys.argv[1]
    config, project_root = get_config()
    
    api_key = config.get("GOOGLE_API_KEY")
    if not api_key:
        log("❌ GOOGLE_API_KEY not found in config.")
        return

    model_name = config.get("GEMINI_MODEL", "gemini-2.0-flash")
    
    log(f"Designing skill: '{description}'...")
    
    try:
        skill_data = generate_skill_content(description, api_key, model_name)
        folder_name = skill_data.get("suggested_folder_name", "new_skill_" + datetime.now().strftime("%H%M%S"))
        python_code = skill_data["python_code"]
        skill_md = skill_data["skill_md"]
        
        # 1. Create Sandbox
        sandbox_dir = tempfile.mkdtemp()
        log(f"Created sandbox: {sandbox_dir}")
        
        script_filename = folder_name + ".py"
        script_path = os.path.join(sandbox_dir, script_filename)
        
        with open(script_path, "w") as f:
            f.write(python_code)
            
        # 2. Test Execution
        log("Running test execution...")
        try:
            # Use current python interpreter (venv)
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                log("✅ Test execution successful!")
                log(f"Test Output: {result.stdout.strip()}")
            else:
                log(f"❌ Test execution failed with return code {result.returncode}")
                # Combine stdout and stderr for better error reporting
                error_msg = (result.stdout + "\n" + result.stderr).strip()
                log(f"Error Details: {error_msg}")
                print(f"❌ **Skill Design Failed:** The generated code did not pass the test execution.")
                return # Stop deployment on failure
        except Exception as e:
            log(f"❌ Sandbox error: {e}")
            return

        # 3. Deploy
        prod_skills_dir = os.path.join(project_root, ".agent", "skills", folder_name)
        if os.path.exists(prod_skills_dir):
            log(f"⚠️ Skill '{folder_name}' already exists. Aborting deployment to prevent overwrite.")
            print(f"❌ **Skill Design Canceled:** A skill named '{folder_name}' already exists. Please choose a different name or ask to 'Update' specifically (Update logic coming soon).")
            return

        os.makedirs(prod_skills_dir, exist_ok=True)
        
        # Update SKILL.md with absolute paths before writing
        final_script_path = os.path.join(prod_skills_dir, script_filename)
        skill_md = skill_md.replace(".agent/skills/SKILL_NAME/FILE_NAME.py", f".agent/skills/{folder_name}/{script_filename}")
        
        with open(os.path.join(prod_skills_dir, "SKILL.md"), "w") as f:
            f.write(skill_md)
            
        with open(final_script_path, "w") as f:
            f.write(python_code)
            
        log(f"🚀 Skill deployed to: {prod_skills_dir}")
        print(f"\n✅ **New Capability Added: {folder_name}**")
        print(f"I have successfully designed and tested the '{folder_name}' skill.")
        print(f"I will now restart to fully index this new power.")
        
        # 4. Git Push (Optional/Proactive)
        try:
            os.chdir(project_root)
            os.system(f"git add .agent/skills/{folder_name}/")
            os.system(f'git commit -m "Auto-designed skill: {folder_name}"')
            log("Git commit complete.")
        except: pass

        # 5. Trigger Restart
        # os.system("./satele restart") 
        # Better to let the monitor handle the restart if it sees this message?
        # Or just run it here.
        log("Triggering Satele restart...")
        os.system("nohup bash -c 'sleep 2; ./satele restart' > /dev/null 2>&1 &")

    except Exception as e:
        log(f"❌ Failed to design skill: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
