import imaplib
import email
from email.header import decode_header
import datetime
import os
from dotenv import load_dotenv

# Load config (Traverse up from .agent/skills/gmail/ to project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
env_path = os.path.join(PROJECT_ROOT, "satele.config")
load_dotenv(env_path)

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD") # Requires App Password

def connect():
    if not GMAIL_USER or not GMAIL_PASS:
        raise Exception("GMAIL_USER and GMAIL_APP_PASSWORD must be set in satele.config")
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASS)
    return mail

def search_emails(query_params):
    """
    query_params: dict with keys like 'sender', 'subject', 'days'
    """
    mail = connect()
    mail.select("inbox")
    
    criterion = []
    if query_params.get('sender'):
        criterion.append(f'FROM "{query_params["sender"]}"')
    if query_params.get('subject'):
        # Use substring search for subjects to be more flexible
        criterion.append(f'SUBJECT "{query_params["subject"]}"')
    
    if query_params.get('days'):
        date = (datetime.date.today() - datetime.timedelta(days=int(query_params['days']))).strftime("%d-%b-%Y")
        criterion.append(f'SINCE "{date}"')
    
    search_query = " ".join(criterion) if criterion else 'ALL'
    
    status, messages = mail.search(None, search_query)
    if status != "OK":
        return f"Search failed with status: {status}"
    
    ids = messages[0].split()
    if not ids:
        return f"No emails found matching query: {search_query}"
        
    results = []
    # Get last N (specified by limit or default 5)
    limit = int(query_params.get('limit', 5))
    for i in ids[-limit:]:
        res, msg_data = mail.fetch(i, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                from_ = msg.get("From")
                date = msg.get("Date")
                
                results.append({
                    "id": i.decode(),
                    "from": from_,
                    "subject": subject,
                    "date": date
                })
    
    mail.logout()
    return results

def read_email(msg_id):
    mail = connect()
    mail.select("inbox")
    res, msg_data = mail.fetch(msg_id, "(RFC822)")
    
    content = ""
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                content += payload.decode(errors='ignore')
                        except: pass
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        content = payload.decode(errors='ignore')
                except: pass
    
    mail.logout()
    return content

def fetch_full(query_params):
    """
    Finds emails matching query and returns a text dump of all bodies.
    Supports optional 'filter' parameter to extract specific sections.
    """
    mail = connect()
    mail.select("inbox")
    
    criterion = []
    if query_params.get('sender'):
        criterion.append(f'FROM "{query_params["sender"]}"')
    if query_params.get('subject'):
        criterion.append(f'SUBJECT "{query_params["subject"]}"')
    if query_params.get('days'):
        date = (datetime.date.today() - datetime.timedelta(days=int(query_params['days']))).strftime("%d-%b-%Y")
        criterion.append(f'SINCE "{date}"')
    
    search_query = " ".join(criterion) if criterion else 'ALL'
    
    status, messages = mail.search(None, search_query)
    if status != "OK":
        return f"Search failed with status: {status}"
    
    ids = messages[0].split()
    if not ids:
        return f"No emails found for content fetch matching: {search_query}"
        
    results = []
    content_filter = query_params.get('filter', '').lower()  # Optional filter keyword
    
    # Limit to prevent token overflow
    limit = int(query_params.get('limit', 5))
    for i in ids[-limit:]:
        # Fetch body
        res, msg_data = mail.fetch(i, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                content = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    content += payload.decode(errors='ignore')
                            except: pass
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            content = payload.decode(errors='ignore')
                    except: pass
                
                # Apply content filter if specified
                if content_filter:
                    filtered_lines = []
                    for line in content.split('\n'):
                        if content_filter in line.lower():
                            # Include context: 2 lines before and after
                            line_idx = content.split('\n').index(line)
                            start = max(0, line_idx - 2)
                            end = min(len(content.split('\n')), line_idx + 3)
                            filtered_lines.extend(content.split('\n')[start:end])
                            break  # Only get first match per email
                    if filtered_lines:
                        content = '\n'.join(filtered_lines)
                    else:
                        content = f"[Filter '{content_filter}' not found in email]"
                
                results.append(f"--- EMAIL ID: {i.decode()} ---\nSubject: {subject}\nFrom: {msg.get('From')}\nDate: {msg.get('Date')}\nContent:\n{content}\n")
    
    mail.logout()
    return "\n".join(results)

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: gmail_tool.py [search|fetch_full|read] <args>")
        sys.exit(1)
        
    cmd = sys.argv[1]
    
    try:
        if cmd == "search":
            params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
            res = search_emails(params)
            print(json.dumps(res, indent=2) if isinstance(res, list) else res)
        elif cmd == "fetch_full":
            params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
            print(fetch_full(params))
        elif cmd == "read":
            print(read_email(sys.argv[2]))
        else:
            print(f"Unknown command: {cmd}")
    except Exception as e:
        print(f"Error: {e}")
