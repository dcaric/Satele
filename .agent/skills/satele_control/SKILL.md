---
name: Satele Control Bridge
description: Provides core functions for the Antigravity Agent to interact with the Satele remote bridge.
---

# Satele Control Skill

This skill allows the Antigravity Agent to act as the primary brain for the Satele Remote Bridge.

## Capabilities
1. **Check Inbox**: Polls the bridge server for new tasks from WhatsApp.
2. **Execute & Reply**: Processes the task using full agent capabilities and sends the result back to WhatsApp.
3. **Voice Handling**: Automatically receives transcribed text from voice notes.

## Tools
The agent should use the following Python script to interact with the bridge:
`python3 .agent/skills/satele_control/bridge_interface.py [check|reply <id> <message>]`

### Commands
- `check`: Returns JSON of the pending task or `null`.
- `reply <id> <message>`: Sends the completion message back to the user.

## Workflow Integration
This skill is designed to be used within the `/satele` workflow.

## Usage Examples
- "Check inbox"
- "Reply to task"
