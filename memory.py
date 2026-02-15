import chromadb
import uuid
import datetime
import os

class Memory:
    def __init__(self, db_path="satele_memory"):
        # Make path relative to this file's dir
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, db_path)
        
        print(f"🧠 Initializing Memory at {full_path}...")
        self.client = chromadb.PersistentClient(path=full_path)
        self.collection = self.client.get_or_create_collection(name="satele_logs")

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
            
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            
            context_lines = []
            for i, doc in enumerate(docs):
                ts = metas[i].get("timestamp", "")[:16].replace("T", " ")
                role = metas[i].get("role", "unknown")
                cwd = metas[i].get("cwd", "?")
                # Format: [Date] (Role) CWD -> Content
                context_lines.append(f"[{ts}] ({role}) CWD:{cwd} -> {doc}")
                
            return context_lines
        except Exception as e:
            print(f"Create Query Error: {e}")
            return []
