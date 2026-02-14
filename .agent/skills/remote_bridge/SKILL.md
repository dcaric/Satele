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

## Example Workflow
1. Agent calls `check_inbox()`.
2. Agent receives: "gravity check the disk usage".
3. Agent runs `df -h`.
4. Agent calls `reply(id, "Disk usage is 40%...")`.
