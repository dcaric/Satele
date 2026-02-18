import os
import requests
import sys
import json
import re

def load_config():
    config = {
        "MALGUS_URL": "http://localhost:8080",
        "MALGUS_KEY": "malgusZiost90"
    }
    # Check common config locations
    config_paths = [
        "satele.config",
        "brain/satele.config",
        "/Users/dcaric/Working/ml/AntigravityMessages/satele.config",
        "/Users/dcaric/Working/ml/AntigravityMessages/brain/satele.config"
    ]
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, val = line.strip().split("=", 1)
                            if key in config:
                                config[key] = val
            except Exception:
                pass
    return config

def talk_to_malgus(message, session_id="satele_bridge"):
    config = load_config()
    malgus_url = os.getenv("MALGUS_URL", config["MALGUS_URL"])
    malgus_key = os.getenv("MALGUS_KEY", config["MALGUS_KEY"])
    
    endpoint = f"{malgus_url}/chat"
    headers = {
        "x-malgus-key": malgus_key,
        "Content-Type": "application/json"
    }
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            # Malgus returns a dict with a 'response' key
            resp_text = result.get("response", "No response from Malgus.")
            print(resp_text)
        else:
            print(f"Error from Malgus (Status {response.status_code}): {response.text}")
    except requests.exceptions.Timeout:
        print("Error: Malgus timed out. He might be busy processing a complex task.")
    except Exception as e:
        print(f"Error connecting to Malgus at {malgus_url}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 malgus_client.py \"your message\" [session_id]")
        sys.exit(1)
        
    user_msg = sys.argv[1]
    session = sys.argv[2] if len(sys.argv) > 2 else "satele_bridge"
    talk_to_malgus(user_msg, session)

