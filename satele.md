---
description: Activates the Satele Patrol to handle remote tasks.
---

1. Print "🪐 Satele Patrol Active. Checking WhatsApp..."
2. Run the bridge interface script in a 3-minute loop:
   `python3 .agent/skills/satele_control/bridge_interface.py check`
   - If a task is found (starts with JSON):
     - Print the task.
     - Execute the task using full agent reasoning.
     - Send the reply using: `python3 .agent/skills/satele_control/bridge_interface.py reply <id> <message>`
   - If no task, wait 5 seconds and check again.
3. Print "🏁 Satele Patrol paused. Use /satele to resume."