import os
from fastapi import FastAPI, HTTPException, Header, Body
from dotenv import load_dotenv

load_dotenv()
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="Remote Bridge Server")

# Simple in-memory storage for tasks
# In a real app, you'd use Redis or a database
tasks_queue = []
results = {}

class Task(BaseModel):
    id: str
    instruction: str
    status: str = "pending"

class TaskCreate(BaseModel):
    instruction: str

# Security: In production, use proper OAuth2 or similar
BRIDGE_SECRET_KEY = "default-secret-key"

def verify_token(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    token = authorization.split(" ")[1]
    if token != BRIDGE_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

@app.get("/")
async def root():
    return {"status": "online", "message": "Antigravity Bridge Server is running"}

# --- Endpoints for the iPhone / Messaging Webhook ---

@app.post("/webhook/message")
async def handle_incoming_message(payload: dict):
    message_text = payload.get("text") or payload.get("Body")
    sender = payload.get("sender", "unknown")
    source = payload.get("source", "unknown")
    media_path = payload.get("mediaPath")
    
    if not message_text and not media_path:
        return {"status": "ignored", "reason": "no text or media"}
    
    trigger = os.getenv("BOT_TRIGGER", "satele").lower()
    
    task_id = str(uuid.uuid4())
    new_task = {
        "id": task_id, 
        "instruction": message_text.replace(trigger, "").replace(trigger.upper(), "").replace(trigger.capitalize(), "").strip() if message_text else "[VOICE COMMAND]", 
        "sender": sender,
        "source": source,
        "media_path": media_path,
        "status": "pending"
    }
    tasks_queue.append(new_task)
    return {"status": "queued", "task_id": task_id}

# --- Endpoints for the Antigravity Bridge (Polling) ---

@app.get("/get-task")
async def get_task(authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    if not tasks_queue:
        return None
    task = tasks_queue.pop(0)
    task["status"] = "processing"
    # Store task metadata to know where to send results
    results[task["id"]] = {"sender": task.get("sender"), "source": task.get("source")}
    return task

@app.post("/report-result")
async def report_result(
    payload: dict = Body(...), 
    authorization: Optional[str] = Header(None)
):
    verify_token(authorization)
    task_id = payload.get("id")
    output = payload.get("output")
    
    meta = results.get(task_id, {})
    sender = meta.get("sender")
    source = meta.get("source")

    print(f"✅ Result for {task_id}: {output[:50]}...")

    # If from WhatsApp, push back to the Node.js bridge
    if source == "whatsapp" and sender:
        import requests
        try:
            # Check for File Upload Command
            if output.strip().startswith("UPLOAD:"):
                filepath = output.strip().split("UPLOAD:")[1].strip()
                resp = requests.post("http://localhost:8001/send-media", json={
                    "to": sender,
                    "filePath": filepath,
                    "caption": f"📄 Here is the file: {os.path.basename(filepath)}"
                })
                
                if resp.status_code != 200:
                    # Fallback message if file fails
                    try:
                        err_msg = resp.json().get('error', 'Unknown Error')
                    except:
                        err_msg = f"HTTP {resp.status_code}"
                    
                    requests.post("http://localhost:8001/send", json={
                         "to": sender,
                         "text": f"❌ Failed to send file: {err_msg}\n(Path: {filepath})"
                     })
            else:
                # Standard Text Reply
                requests.post("http://localhost:8001/send", json={
                    "to": sender,
                    "text": f"✅ Result:\n{output}"
                })
        except Exception as e:
            print(f"❌ Failed to process reply: {e}")
    
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
