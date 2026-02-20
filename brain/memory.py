import os
import pathlib
import errno

# --- CRITICAL PATCH FOR SYSTEM PERMISSIONS (MACOS/LINUX) ---
# Pydantic (used by ChromaDB) tries to stat() all .env files in parent dirs.
# The root .env in this folder sometimes throws PermissionError or is blocked.
# We monkey-patch os.stat and pathlib.Path.stat to pretend any .env doesn't exist.
# This logic applies to ALL systems to prevent permissions crashes.
orig_os_stat = os.stat
def patched_os_stat(path, *args, **kwargs):
    if str(path).endswith(".env"):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))
    return orig_os_stat(path, *args, **kwargs)
os.stat = patched_os_stat

orig_path_stat = pathlib.Path.stat
def patched_path_stat(self, *args, **kwargs):
    if str(self).endswith(".env"):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(self))
    return orig_path_stat(self, *args, **kwargs)
pathlib.Path.stat = patched_path_stat
# --------------------------------------------

import chromadb
import uuid
import datetime
import requests
import json
import platform

class Memory:
    def __init__(self, db_path="satele_memory", silent=False):
        # Make path relative to this file's dir
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, db_path)
        
        if not silent: print(f"🧠 Initializing Memory at {full_path}...")
        self.client = chromadb.PersistentClient(path=full_path)
        self.collection = self.client.get_or_create_collection(name="satele_logs")

    def get_count(self):
        return self.collection.count()

    def remember(self, text, role="user", metadata=None):
        if not text: return
        meta = metadata or {}
        # Ensure metadata values are strings/int/float/bool (Chroma requirement)
        # Convert Path objects or None to string
        clean_meta = {}
        for k, v in meta.items():
            if v is None: clean_meta[k] = ""
            else: clean_meta[k] = str(v)
            
        clean_meta["timestamp"] = datetime.datetime.now().isoformat()
        clean_meta["role"] = role
        
        self.collection.add(
            documents=[text],
            metadatas=[clean_meta],
            ids=[str(uuid.uuid4())]
        )

    def recall(self, query_text, n_results=5):
        if not query_text: return []
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            # Use 'get' to safely access list inside structure
            docs = results.get('documents', [[]])[0]
            metas = results.get('metadatas', [[]])[0]
            
            context_lines = []
            if not docs: return []
            
            for i, doc in enumerate(docs):
                ts = metas[i].get("timestamp", "")[:16].replace("T", " ")
                role = metas[i].get("role", "unknown")
                cwd = metas[i].get("cwd", "?")
                # Format: [Date] (Role) CWD -> Content
                context_lines.append(f"[{ts}] ({role}) CWD:{cwd} -> {doc}")
                
            return context_lines
        except Exception as e:
            # print(f"Query Error: {e}")
            return []

    def clear(self):
        """Wipes all memory records"""
        try:
            self.client.delete_collection(name="satele_logs")
            self.collection = self.client.get_or_create_collection(name="satele_logs")
            return True
        except Exception as e:
            print(f"Error clearing memory: {e}")
            return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        # Silent init
        try:
            m = Memory(silent=True)
            print(m.get_count())
        except Exception as e:
            # Print error to stderr so it can be seen if needed, but return 0 for the script
            import traceback
            # sys.stderr.write(f"Memory Error: {e}\n")
            # For the CLI, we want to know it failed
            print(f"ERROR: {e}")
