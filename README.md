# 🪐 Satele: Antigravity Remote Bridge

Satele is an autonomous, multimodal bridge that allows you to control your Mac and interact with your code via **WhatsApp** and **Voice Commands**. It uses Gemini 3 Flash to translate your natural language into actionable terminal commands.

---

## 🚀 Quick Setup

### 1. Global Installation
Enable the `satele` command from any terminal folder:
```bash
echo "alias satele='/Users/dcaric/Working/ml/AntigravityMessages/satele'" >> ~/.zshrc && source ~/.zshrc
```

### 2. Configure Brain
Set your Gemini API Key (required for voice commands and background monitoring):
```bash
satele geminikey AIzaSy...
```

### 3. Connect Phone
Link your WhatsApp account (one-time setup):
```bash
satele whatsapp
```
*Go to WhatsApp > Settings > Linked Devices > Link a Device.*

### 4. Install Project Tools (Optional)
If you want to use the **Antigravity Agent** to control your project remotely, enable the plugin in your current workspace:
```bash
# First, install the skills globally (do this once)
mkdir -p ~/satele_global && cp -r .agent/* ~/satele_global/

# Then, link it to any new project
satele link
```

---

## 🛠️ Command Reference

| Command | Description |
| :--- | :--- |
| `satele start` | Starts all services (FastAPI, WhatsApp, AI Monitor) in the background. |
| `satele stop` | Terminates all running satele background processes. |
| `satele status` | Checks the health of the "Brain" components. |
| `satele name <name>` | Sets a custom wake-word (Default: `satele`). |
| `satele geminikey <key>` | Sets or updates your Google Gemini API Key. |
| `satele whatsapp` | Restarts the linking process to show the QR code. |
| `satele install` | Installs the connection skill to `~/satele_global`. |
| `satele link` | Enables `/satele` command in the current project by linking the global skill. |
| `satele kill` | Force kills all processes if `stop` fails. |

---

## 🎙️ User Guide

### 1. Simple Tasks (Background Brain)
The background monitor (`satele start`) handles quick system queries instantly.
- *"Satele, check my disk usage"*
- *"Satele, are there any errors in satele.log?"*
- *"Satele, list the 5 most CPU intensive processes"*

### 2. Advanced Development (Agent Brain)
To perform complex coding tasks, you must activate the **Antigravity Agent** inside your IDE.
1.  Run `satele link` in your project folder.
2.  Type `/satele` in the Antigravity chat window.
3.  Send a WhatsApp message with the phrase **"use gravity"**:
    - *"Satele, **use gravity** to refactor the login system"*
    - *"Satele, **use gravity** and check why the tests are failing"*

### 3. Direct Shell Access
If you need 100% precision, use the `sh:` prefix:
- `satele sh: ls -la`
- `satele sh: pwd`

### 4. Voice Commands
Simply record a **Voice Note** on WhatsApp. The Gemini brain will listen to it, understand your intent, and execute the command.
- *"Hey Satele, check if the server is still running on port 8000."*

---

## 🧠 Architecture
- **WhatsApp Bridge**: A Node.js service using Baileys to handle real-time messaging.
- **FastAPI Server**: Central gateway for task queuing and result relay.
- **AI Monitor**: A Python service that uses the **Gemini 3 Flash Preview** model to interpret commands.
- **Logs**: All activity is logged to `satele.log`.

---

## 🔐 Privacy & Security
- Your voice notes are temporarily stored in `media/` and wiped every time the system starts.
- The `.env` file is ignored by Git to keep your API keys safe.
