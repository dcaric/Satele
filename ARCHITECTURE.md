# Satele Architecture

This document describes the technical architecture of Satele, a WhatsApp-based AI assistant with extensible skills.

## Table of Contents
- [Overview](#overview)
- [System Components](#system-components)
- [Skills System](#skills-system)
- [Data Flow](#data-flow)
- [Configuration](#configuration)
- [Extending Satele](#extending-satele)
- [Autonomous Evolution](#autonomous-evolution)
- [Remote Command Execution](#remote-command-execution)
- [Advanced File Management](#advanced-file-management)

---

## Overview

Satele is a multi-component system that enables AI-powered automation via WhatsApp. It consists of:

1. **WhatsApp Bridge** - FastAPI server handling WhatsApp Web integration
2. **AI Brain (Monitor)** - Python process that interprets commands and executes tasks
3. **Skills System** - Modular, extensible capabilities
4. **Memory System** - ChromaDB-based persistent context storage

```
┌─────────────┐
│   WhatsApp  │
│    User     │
└──────┬──────┘
       │
       ↓
┌─────────────────────┐
│  WhatsApp Bridge    │
│  (FastAPI Server)   │
│  Port: 8000         │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│   AI Brain          │
│   (monitor.py)      │
│   - Gemini/Ollama   │
│   - Skills Loader   │
│   - Memory System   │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│   Skills System     │
│   .agent/skills/    │
│   - speedtest       │
│   - satele_control  │
│   - (custom...)     │
└─────────────────────┘
```

---

## System Components

### 1. WhatsApp Bridge (`server/`)

**Purpose:** Connects WhatsApp Web to the AI brain.

**Technology:**
- FastAPI (Python web framework)
- whatsapp-web.js (Node.js WhatsApp client)
- QR code authentication

**Key Files:**
- `server/main.py` - FastAPI server
- `server/whatsapp_client.js` - WhatsApp Web integration

**Endpoints:**
- `POST /task` - Submit tasks to AI brain
- `GET /status` - Check system status
- `POST /upload` - Send files via WhatsApp

**Port:** 8000 (configurable via `REMOTE_BRIDGE_URL`)

### 2. AI Brain (`brain/monitor.py`)

**Purpose:** Core intelligence - interprets natural language and executes commands.

**AI Providers:**
- **Gemini** (default) - Google's Gemini 2.0 Flash
- **Ollama** (local) - Custom models like `satele-m3`

**Key Functions:**

```python
def ai_interpret(instruction, media_path=None)
    # Converts natural language to shell commands
    # Injects skills context into AI prompt
    # Returns list of commands to execute

def get_skills_context()
    # Scans .agent/skills/*/SKILL.md
    # Extracts skill metadata and commands
    # Returns formatted context for AI prompt

def process_instruction(instruction, media_path=None)
    # Main entry point for task processing
    # Executes commands and handles UPLOAD directives
```

**Command Execution Flow:**
1. Receive instruction from bridge
2. Load skills context
3. Query AI (Gemini/Ollama) for command interpretation
4. Execute commands via shell
5. Detect `UPLOAD:` output for file sending
6. Return results to bridge

### 3. Memory System (`brain/memory.py`)

**Purpose:** Persistent context storage for AI conversations.

**Technology:**
- ChromaDB (vector database)
- Embeddings for semantic search

**Features:**
- Stores user instructions and AI responses
- Semantic recall (finds relevant past context)
- Persistent across restarts

**Usage:**
```python
brain_memory.remember(instruction, "user", metadata)
brain_memory.recall(query, n_results=3)
```

### 4. Skills System (`.agent/skills/`)

**Purpose:** Modular, extensible capabilities for the AI.

**Structure:**
```
.agent/skills/
├── speedtest/
│   ├── SKILL.md              # Skill documentation
│   └── speedtest_capture.py  # Implementation
└── satele_control/
    ├── SKILL.md
    └── (implementation files)
```

**Scalable Semantic Search:**
To support hundreds of skills without bloating the AI prompt, Satele uses a **Semantic Skill Indexer**:
- **Indexing:** At startup, `skill_indexer.py` scans all `SKILL.md` files and generates vector embeddings using `sentence-transformers` (specifically the `all-MiniLM-L6-v2` model).
- **Storage:** Embeddings and metadata are cached in `brain/.skill_index_v2.json`.
- **Retrieval:** When a user sends a message, Satele performs a cosine similarity search between the user's instruction and the indexed skills.
- **Prompt Injection:** Only the top 5 most relevant skills are injected into the AI's prompt, ensuring high performance and accuracy even with a massive skill library.

See [Skills System](#skills-system) section for details.

---

## Skills System

### What is a Skill?

A **skill** is a self-contained capability that the AI can use. Each skill consists of:

1. **SKILL.md** - Documentation and metadata
2. **Implementation** - Script(s) that perform the actual work

### SKILL.md Format

```markdown
---
name: Skill Name
description: Brief description of what this skill does
---

# Skill Name

Detailed description...

## Tools
The agent can use the following script:
`python3 .agent/skills/skill_name/script.py [args]`

## Example
If a user says "do something", the agent should:
1. Run `python3 .agent/skills/skill_name/script.py`
2. Get the output `UPLOAD:/path/to/result`
3. Reply with that string.
```

### How Skills Are Loaded

**At Startup:**
1. `monitor.py` calls `get_skills_context()`
2. Scans `.agent/skills/*/SKILL.md`
3. Extracts:
   - `name:` from YAML frontmatter
   - `description:` from YAML frontmatter
   - Command from code blocks (`` `python3 ...` `` or `` `bash ...` ``)
4. Converts relative paths to absolute paths
5. Injects into AI prompt as available tools

**Example Injected Context:**
```
🚀 AVAILABLE SKILLS & CUSTOM SCRIPTS:
- Speedtest Capture: Runs internet speed test and generates result image
  COMMAND: python3 /full/path/to/.agent/skills/speedtest/speedtest_capture.py
```

### Creating a New Skill

**Step 1:** Create directory structure
```bash
mkdir -p .agent/skills/my_skill
```

**Step 2:** Create `SKILL.md`
```markdown
---
name: My Skill
description: Does something useful
---

# My Skill

## Tools
`python3 .agent/skills/my_skill/my_script.py`
```

**Step 3:** Create implementation
```python
# my_script.py
import sys

def main():
    # Do work...
    result_path = "/path/to/output.png"
    print(f"UPLOAD:{result_path}")

if __name__ == "__main__":
    main()
```

**Step 4:** Restart monitor
```bash
pkill -f monitor.py
./venv/bin/python3 brain/monitor.py > /tmp/m3.log 2>&1 &
```

The skill is now available! The AI will automatically discover it.

**How Skills Are Targeted (Semantic Search):**
Unlike simple keyword matching, Satele uses **Semantic Search** to find the right skill. If you have a skill for "Network Diagnostics" and a user says "My internet is slow", the semantic search will correctly identify that "Network Diagnostics" is the most relevant tool and inject it into the AI's context.

### Skill Output Conventions

**For File Uploads:**
```python
print(f"UPLOAD:/absolute/path/to/file.png")
```

**For Text Results:**
```python
print("Result: Success!")
```

**For Errors:**
```python
print("Error: Something went wrong", file=sys.stderr)
sys.exit(1)
```

---

## Data Flow

### Complete Request Flow

```
1. User sends WhatsApp message: "M3 measure speed"
   ↓
2. WhatsApp Web receives message
   ↓
3. whatsapp_client.js detects "M3" trigger
   ↓
4. POST /task → FastAPI Bridge
   {
     "instruction": "measure speed",
     "sender": "+1234567890"
   }
   ↓
5. Bridge → monitor.py (polling or webhook)
   ↓
6. monitor.py:
   a. Loads skills context
   b. Queries AI: "measure speed" + skills context
   c. AI returns: ["python3 /path/to/speedtest_capture.py"]
   d. Executes command
   e. Script outputs: "UPLOAD:/path/to/speedtest.png"
   f. Detects UPLOAD directive
   ↓
7. Returns to bridge: {"type": "upload", "path": "/path/to/speedtest.png"}
   ↓
8. Bridge sends image via WhatsApp
   ↓
9. User receives speedtest result! 🎉
```

### File Upload Flow

When a script outputs `UPLOAD:/path/to/file`:

1. `monitor.py` detects line starting with `UPLOAD:`
2. Extracts file path
3. Resolves relative → absolute path
4. Handles case-insensitive path resolution (macOS)
5. Returns `UPLOAD: /absolute/path` to bridge
6. Bridge reads file and sends via WhatsApp

---

## Configuration

### Environment Variables

**Brain Configuration (`brain/satele_brain.env`):**
```bash
# AI Provider
AI_PROVIDER=ollama              # or "gemini"
OLLAMA_MODEL=satele-m3          # if using Ollama
GEMINI_MODEL=gemini-2.0-flash   # if using Gemini
GOOGLE_API_KEY=your_key_here    # for Gemini

# Bridge Connection
REMOTE_BRIDGE_URL=http://localhost:8000
BRIDGE_SECRET_KEY=default-secret-key

# Bot Trigger
BOT_TRIGGER=m3                  # WhatsApp trigger word
```

**Server Configuration (`server/.env`):**
```bash
BRIDGE_SECRET_KEY=default-secret-key
PORT=8000
```

### AI Provider Selection

**Gemini (Cloud):**
- Faster, more capable
- Requires API key
- Costs money (but cheap)

**Ollama (Local):**
- Free, private
- Requires local Ollama installation
- Slower, less capable

**Switching Providers:**
```bash
# Edit brain/satele_brain.env
AI_PROVIDER=gemini  # or "ollama"
```

---

## Extending Satele

### Adding New Skills

See [Creating a New Skill](#creating-a-new-skill) above.

### Adding New AI Providers

To add support for a new AI provider (e.g., Claude, GPT-4):

1. Edit `brain/monitor.py`
2. Add new provider in `ai_interpret()` function
3. Follow the pattern for Gemini/Ollama
4. Update configuration to support new provider

### Custom Command Handlers

You can add custom command handlers in `monitor.py`:

```python
# In process_instruction()
if instruction.lower().startswith("custom:"):
    # Handle custom command
    return handle_custom_command(instruction)
```

### Webhooks vs Polling

**Current:** Monitor polls bridge every few seconds

**Alternative:** Bridge can push to monitor via webhook

To implement webhooks:
1. Add FastAPI endpoint in `brain/` to receive tasks
2. Update bridge to POST directly to monitor
3. Remove polling loop

---

## Troubleshooting

### Common Issues

**1. Skills not loading**
- Check `SKILL.md` format (YAML frontmatter)
- Verify command syntax in code blocks
- Check logs: `cat /tmp/m3.log | grep Skills`

**2. Commands not executing**
- Check working directory: `M3 what is your current folder`
- Verify absolute paths in skills
- Check script permissions: `chmod +x script.sh`

**3. Files not uploading**
- Verify script outputs `UPLOAD:/absolute/path`
- Check file exists: `ls -l /path/to/file`
- Check path case sensitivity (macOS)

### Debug Logs

**Monitor logs:**
```bash
tail -f /tmp/m3.log
```

**Bridge logs:**
```bash
./satele logs
```

**Skill execution:**
```bash
# Test skill directly
python3 .agent/skills/speedtest/speedtest_capture.py
```

---

## Performance Considerations

### Memory Usage
- ChromaDB: ~100-500MB depending on history
- Monitor process: ~50-100MB
- Bridge: ~100-200MB

### Response Times
- Gemini: 1-3 seconds
- Ollama: 3-10 seconds (depending on model)
- Skills: Varies (speedtest: ~30-60s)

### Scalability
- Current design: Single user
- For multi-user: Add user context isolation
- For high volume: Consider async processing

---

## Security Considerations

### Command Execution
- Monitor blocks dangerous commands (`rm -rf /`, etc.)
- Skills run with user permissions
- No sudo/root access by default

### API Keys
- Store in `.env` files (gitignored)
- Never commit keys to repository
- Use environment variables in production

### WhatsApp Security
- QR code authentication
- Session persistence in `.wwebjs_auth/`
- No password storage

---

## Future Enhancements

### Potential Additions
1. **MCP Support** - Standardized skill protocol
2. **Multi-user** - Support multiple WhatsApp users
3. **Webhooks** - Replace polling with push notifications
4. **Skill Marketplace** - Share skills between users
5. **Voice Messages** - Transcribe and process audio
6. **Scheduled Tasks** - Cron-like automation
7. **Skill Dependencies** - Package management for skills

---

## Related Documentation

- [README.md](README.md) - Getting started guide
- [.agent/skills/speedtest/SKILL.md](.agent/skills/speedtest/SKILL.md) - Example skill
- [.agent/skills/satele_control/SKILL.md](.agent/skills/satele_control/SKILL.md) - Control skill

---

## Contributing

To contribute to Satele:

1. Fork the repository
2. Create a feature branch
3. Add your skill or enhancement
4. Test thoroughly
5. Submit a pull request

---

## Autonomous Evolution

Satele is one of the first AI assistants capable of **self-evolution**. She doesn't just use predefined skills; she can design, test, and install her own new capabilities based on your natural language instructions.

### The Evolution Loop:
1. **AI Design:** When you ask for a new skill, Satele uses Gemini to architect the Python logic (`.py`) and write the necessary system documentation (`SKILL.md`).
2. **Sandbox Testing:** Satele creates an isolated "sandbox" environment, installs its dependencies, and runs the code. If it crashes, she reads the error and fixes the code automatically.
3. **Safety & Performance Rules:**
   - **Native-First:** To avoid dependency hell, she prefers standard libraries (`urllib`, `json`, `random`).
   - **Keyless Execution:** She is forbidden from creating skills that require paid API keys or registration.
   - **SSL Awareness:** She handles Mac-specific SSL certificate issues automatically.
4. **Automatic Deployment:** Once the test passes, Satele moves the files into the production `.agent/skills/` folder.
5. **Auto-indexing:** Satele restarts her core monitor, triggering the **Skill Indexer** to recognize the new power and make it available for use immediately.

---

## Remote Command Execution

Users can execute any shell command or Satele CLI command directly from WhatsApp using the "run command" or "sh:" syntax.

### 1. Run Command Syntax
Users can execute commands using the structure: `<bot-name> run command - <command>`.
- **AI-Mediated:** These commands are parsed by the AI monitor to ensure correct context.
- **Example:** `m1 run command - satele status`

### 2. Emergency Responder (`sh:`)
For cases where the AI Brain might be stalled or stopped, Satele includes an **Emergency Responder** built directly into the FastAPI server (`server/main.py`).
- **Bypass:** It detects the `sh:` prefix and executes the command directly via the system shell, bypassing the AI task interpretation layer.
- **Bypass Recovery:** This allows for remote "Revival" of the system (e.g., `sh: ./satele start`) even when the main monitor process is not responding.

---

## Advanced File Management

### 1. Large Output Ad-hoc Attachments
If a requested log or output is too large for a standard message (typically > 2000 characters), Satele can automatically (or upon request) send it as an attachment.
- **Process:** Satele writes the output to a temporary `.txt` file in the `media/` directory and returns an `UPLOAD:` directive.
- **Example:** *"m1 ask malgus to show apartments help, send me as attachment"*

### 2. Zipping Files and Folders
Satele can handle complex file transfers by zipping them on the fly.
- **Zipping:** The AI can generate shell commands to zip directories (e.g., `zip -r output.zip folder/`).
- **Multimodal Delivery:** Using the `UPLOAD:<path>` directive, Satele can deliver PDFs, ZIPs, or any other file type back to WhatsApp.
- **Remote Retrieval:** This is ideal for pulling logs, source code, or media files from the host machine to your mobile device instantly.
