# 🪐 Satele: Autonomous Remote Bridge

Satele is an advanced, multimodal bridge that connects your **WhatsApp** to your **Server/Desktop Environment**. It allows you to control your machine via text or voice commands using AI (Gemini or Ollama).

---

## 🌍 Supported Platforms

| OS | Support Level | Notes |
| :--- | :--- | :--- |
| **macOS** (Silicon/Intel) | ✅ Full | Native support for all features including audio. |
| **Linux** (Ubuntu/Debian) | ✅ Full | Requires `nodejs`, `python3-venv`, and `ffmpeg` installed. |
| **Windows** | ❌ No | Only via WSL2 (treat as Linux). |

---

## 🚀 Installation & Setup

### 1. Clone & Prepare
Clone the repository to your desired location (e.g., `~/satele`):
```bash
git clone https://github.com/dcaric/Satele.git ~/satele
cd ~/satele
```

### 2. Install Dependencies
Run the built-in setup command to install Node.js modules and Python virtual environment:
```bash
./satele setup
```

### 3. Make Command Global
To use `satele` from anywhere (instead of `./satele`), add it to your shell profile.

**On macOS (Zsh):**
```bash
echo 'export PATH="$HOME/satele:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

**On Linux (Bash):**
```bash
echo 'export PATH="$HOME/satele:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

Now you can just type `satele status` from any folder!

---

## 🧠 AI Configuration

Satele supports two AI backends: **Cloud (Google Gemini)** and **Local (Ollama)**.

### Option A: Cloud (Google Gemini)
Best for speed, multimodal (audio/images), and complex reasoning.
1.  **Get Key**: Obtain a key from [Google AI Studio](https://aistudio.google.com/).
2.  **Set Key**:
    ```bash
    satele geminikey AIzaSy...
    ```
3.  **Select Model** (Optional, default is `gemini-2.0-flash`):
    ```bash
    satele gemini gemini-3-flash-preview
    ```
4.  **Track Costs**: Set pricing (e.g., $0.50/1M input, $3.00/1M output):
    ```bash
    satele tokens 0.50 3.00
    ```

### Option B: Local (Ollama)
Best for privacy and offline usage. Free.
1.  **Install/Check**:
    ```bash
    satele ollama
    ```
2.  **Download Model**:
    ```bash
    satele ollama gemma3:4b
    ```
    *(This downloads the model and creates a custom `satele` variant with system prompts)*.
3.  **Switch to Local**:
    ```bash
    satele ollama start
    satele stop && satele start
    ```
4.  **Switch Back to Cloud**:
    ```bash
    satele ollama stop
    satele stop && satele start
    ```

---

## 🛠️ Usage & Commands

### 📱 1. Connect WhatsApp
Link your device to enable remote control:
```bash
satele whatsapp
```
Scan the QR code with WhatsApp (Linked Devices).

### 🤖 2. Manage Service
| Command | Description |
| :--- | :--- |
| `satele start` | Starts all background services. |
| `satele stop` | Stops all services. |
| `satele status` | Shows health, active AI model, and token usage cost. |
| `satele name <name>` | Sets a custom wake-word (e.g. `satele name M1`). Useful for multi-bot setups. |
| `satele setup-sudo` | Configures passwordless `sudo` for Satele (Advanced). |

### 🎙️ 3. Remote Capabilities (WhatsApp)

#### **System Checks**
> *"M1 check disk usage"*
> *"Status report"*
> *"Who is logged in?"*

#### **File Transfer**
> *"Send me satele.log"*
> *"Get config.json"*

#### **Voice Interaction**
> *(Send a Voice Note)*: "Check if the docker container is running and restart it if not."

#### **Direct Shell**
> *"sh: ls -la /var/log"*

---

## 🛡️ Security

- **Sudo Access**: Satele runs as your user. It cannot run `sudo` unless you explicitly enable it via `satele setup-sudo`.
- **Environment**: API Keys are stored in `.env` (git-ignored).
- **Logs**: Activity is logged to `satele.log` (git-ignored).
- **WhatsApp**: Uses end-to-end encryption via Multi-Device API.

---

## 🐧 Linux Specifics
- Ensure `ffmpeg` is installed for voice note processing (`sudo apt install ffmpeg`).
- If `satele setup` fails on `npm`, ensure `nodejs` (v18+) is installed.
