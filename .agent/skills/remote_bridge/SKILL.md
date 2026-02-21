# Remote Message Bridge

This skill allows the agent to synchronize with a remote FastAPI server to receive instructions from iMessage/WhatsApp and report back progress.

## Prerequisite
- A running FastAPI server with `/get-task` and `/report-result` endpoints.
- Environment variable `REMOTE_BRIDGE_URL` set to your server address.
- Environment variable `BRIDGE_SECRET_KEY` for authentication.

## Usage
The Antigravity Agent can use these tools to interact with the remote bridge.

### Tools:
- `remote_bridge.check_inbox()`: Returns the latest message from WhatsApp/iMessage.
- `remote_bridge.reply(task_id, message)`: Sends a response back to the sender's phone.

## Usage Examples
- "Check my messages"
- "Any new tasks for me?"
- "Reply to the user that I'm on it"
