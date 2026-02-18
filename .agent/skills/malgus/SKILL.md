---
name: Malgus Intelligence
description: Enables Satele to communicate with the Malgus AI agent running on the same system.
---

# Malgus Intelligence Skill

This skill allows the Antigravity Agent to delegate tasks or query the Malgus AI agent. Malgus is another specialized autonomous agent running on the same local environment.

## Capabilities
1. **Chat/Task Delegation**: Send messages or complex instructions to Malgus.
2. **Autonomous Collaboration**: Malgus can execute coding tasks, manage spreadsheets, and control macOS apps.
3. **Session Persistence**: Maintains conversation context via session IDs.

## Tools
The agent should use the following Python script to interact with Malgus:
`python3 .agent/skills/malgus/malgus_client.py "[message]" [session_id]`

### Usage Examples
- `python3 .agent/skills/malgus/malgus_client.py "Can you check the latest apartment prices in the spreadsheet?"`
- `python3 .agent/skills/malgus/malgus_client.py "Run the trading analysis script and report back." "trading_session"`

## Configuration
The client uses the following defaults (can be overridden via environment variables):
- `MALGUS_URL`: `http://localhost:8080`
- `MALGUS_KEY`: `malgusZiost90` (X-Malgus-Key header)

## When to use
Use this skill when the user explicitly asks to "talk to Malgus", "ask Malgus", or when a task is better suited for Malgus's specific capabilities (like Numbers spreadsheet manipulation or specialized macOS automation that Malgus is already configured for).
