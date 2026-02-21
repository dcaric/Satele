---
name: File Explorer
description: List files, read directories, and find information about the filesystem.
---

# File Explorer Skill

This skill allows the agent to navigate and explore the filesystem.

## Tools
`ls -F .`

### Usage
- Use `ls -F` to list files in a directory. Add a path to list a specific folder.
- Use `find . -name "*.ext"` to search for files in the current directory.
- Use `cat` or `head` to preview file contents.
- Use `realpath <file>` to get the absolute path.

## Example
If a user says "list files", the agent should:
1. Run `ls -F`

If a user says "list files in media", the agent should:
1. Run `ls -F media/`

If a user says "send me the latest report", the agent should:
1. Run `echo "UPLOAD:$(ls -t latest_report*.pdf 2>/dev/null | head -1 | xargs realpath)"`

## Usage Examples
- "Check current weather"
