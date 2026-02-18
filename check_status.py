import os
import subprocess
import requests
import json

def get_status():
    print("📊 Satele System Internal Status:")
    
    # Check processes using ps -ax
    try:
        proc = subprocess.run(['ps', '-ax'], capture_output=True, text=True)
        ps_output = proc.stdout
        
        main_py = "Python server/main.py" in ps_output or "server/main.py" in ps_output
        bridge_js = "whatsapp_bridge.js" in ps_output
        monitor_py = "monitor.py" in ps_output
        
        print(f"🔹 FastAPI: {'RUNNING' if main_py else 'STOPPED'}")
        print(f"🔹 WhatsApp Bridge: {'RUNNING' if bridge_js else 'STOPPED'}")
        print(f"🔹 AI Monitor: {'RUNNING' if monitor_py else 'STOPPED'}")
    except Exception as e:
        print(f"⚠️ Process check error: {e}")

    # Check config
    config_path = os.path.join(os.getcwd(), "satele.config")
    try:
        with open(config_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                if "AI_PROVIDER" in line: print(line.strip())
                if "OLLAMA_MODEL" in line: print(line.strip())
                if "BOT_TRIGGER" in line: print(line.strip())
    except Exception as e:
        print(f"⚠️ Config read error: {e}")

    # Check Ollama
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            print("🦙 Ollama: ONLINE")
        else:
            print(f"🦙 Ollama: ERROR {resp.status_code}")
    except:
        print("🦙 Ollama: OFFLINE")

if __name__ == "__main__":
    get_status()
