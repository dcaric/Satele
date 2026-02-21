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
- **Skills List**: View all registered AI skills and capabilities.
  `./satele skills`
- **Help**: Show all available CLI subcommands.
  `./satele help`

## When to use
- Use `gitpull` when the user asks to "update", "pull latest", or "update code".
- Use `restart` when the user asks to "restart", "reboot".
- Use `status` to diagnose connection or service issues.
- Use `skills` or `help` when the user wants to know what Satele can do.

## WhatsApp Printout Service
Users can request a raw command "printout" to bypass AI reasoning and truncation:
- "send me printout - satele help"
- "send me printout - satele skills"
- "send me printout - satele status"
- "send me printout - ls -la"

## Usage Examples
- "satele restart"
- "satele status"
- "send me printout - satele skills"
- "send me printout - satele help"
