---
name: Satele Core Control
description: Essential system commands for maintaining Satele remotely.
---

# Satele Core Control

Use these commands to manage the Satele environment itself.

## Commands
- **Git Pull**: Pull the latest code updates from the repository.
  `./satele gitpull`
- **Restart**: Safely restart all Satele services (WhatsApp Bridge, FastAPI Server, and AI Monitor). Use this after configuration changes or git updates.
  `./satele restart`
- **Status Check**: Verify which services are running.
  `./satele status`

## When to use
- Use `gitpull` when the user asks to "update", "pull latest", or "update code".
- Use `restart` when the user asks to "restart", "reboot", or after you have modified a configuration file like `satele.config`.
- Use `status` to diagnose connection issues.
