---
name: Gmail Intelligence
description: Enables Satele to search, read, and analyze Gmail messages.
---

# Gmail Skill

This skill allows Satele to access your Gmail inbox to find specific information, summarize email chains, or extract details from receipts/invoices.

## Setup Requirements
1. **Enable IMAP**: Go to Gmail Settings > Forwarding and POP/IMAP > Enable IMAP.
2. **App Password**: Go to Google Account > Security > 2-Step Verification > App Passwords. Create one for "Satele".
3. **Configure**: Use the Satele CLI:
   ```bash
   satele gmail your-email@gmail.com xxxx-xxxx-xxxx-xxxx
   ```

## Tools
1. **Search Emails**: `python3 .agent/skills/gmail/gmail_tool.py search '{"days": 7, "subject": "query"}'` (Returns metadata/IDs only)
2. **Fetch Full Content**: `python3 .agent/skills/gmail/gmail_tool.py fetch_full '{"days": 7, "subject": "query", "limit": 5}'` (Returns full bodies for summarization)
3. **Read Email**: `python3 .agent/skills/gmail/gmail_tool.py read <id>`

### Query JSON Format:
- `days`: Number of days to look back (default: all).
- `subject`: Partial subject match.
- `sender`: Optional sender email filter.
- `limit`: Number of emails to return (e.g., 1 for "the last one", 5 for "last 5").

## Natural Language Capability
Once configured, you can ask Satele:
- *"Satele, search my gmail for invoices from last week"*
- *"Summarize the latest emails from Dario"*
- *"What did my boss say about the project in the email he sent yesterday?"*
