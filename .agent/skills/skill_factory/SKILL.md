---
name: Skill Factory
description: Allows Satele to autonomously design, test, and deploy new skills from raw descriptions.
---

# Skill Factory 🏗️

This is Satele's "Evolution Engine". It allows Satele to create her own new capabilities by writing Python code, generating documentation, and testing the implementation in a sandbox before "hot-deploying" it.

## Capabilities
1. **Instruction to Skill**: Turn a natural language description into a working Satele skill.
2. **Autonomous Coding**: Writes the `.py` logic and `SKILL.md` frontmatter.
3. **Sandbox Testing**: Installs dependencies and verifies the script runs before deployment.
4. **Auto-Deployment**: Places the files in `.agent/skills/` and prompts for (or triggers) a restart.

## Tools
The agent can use the following script:
`python3 .agent/skills/skill_factory/skill_developer.py "[skill_description]"`

## Usage Examples (CRITICAL: Only trigger when a NEW skill is requested)
- "Design a new skill to..."
- "Create a new capability for..."
- "Build a skill that..."
- "I need a NEW skill that..."

## Process Flow
1. Satele receives a design request.
2. She runs the `skill_developer.py` with the description.
3. The script uses Gemini to generate the implementation.
4. A sandbox is created to verify the code works.
5. On success, the skill is moved to the production `.agent/skills/` folder.
6. Satele is restarted to index the new capability.
