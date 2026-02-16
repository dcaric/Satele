"""
Skill Indexer - Semantic search for skills
Enables efficient skill discovery even with 100+ skills
Uses sentence-transformers and local JSON storage (no ChromaDB needed)
"""
import os
import re
import json
import numpy as np
import warnings

# Use a local cache for HuggingFace models to avoid permission issues
HF_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "huggingface")
os.makedirs(HF_CACHE, exist_ok=True)
os.environ["HF_HOME"] = HF_CACHE

# Suppress warnings
warnings.filterwarnings('ignore')

from sentence_transformers import SentenceTransformer

class SkillIndexer:
    def __init__(self, project_root):
        self.project_root = project_root
        self.skills_dir = os.path.join(project_root, ".agent", "skills")
        self.cache_file = os.path.join(project_root, "brain", ".skill_index_v2.json")
        
        # Initialize embedding model (lightweight, fast)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.data = self._load_cache()
        
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {"skills": {}}
        return {"skills": {}}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.data, f)

    def index_all_skills(self):
        """Scan and index all SKILL.md files"""
        if not os.path.exists(self.skills_dir):
            print(f"⚠️ Skills directory not found: {self.skills_dir}")
            return 0
        
        skills_indexed = 0
        current_skills = {}
        
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name, "SKILL.md")
            
            if os.path.exists(skill_path):
                try:
                    with open(skill_path, 'r') as f:
                        content = f.read()
                        
                    # Extract metadata
                    name = skill_name
                    description = ""
                    
                    # Parse YAML frontmatter
                    for line in content.split('\n'):
                        if line.startswith('name:'):
                            name = line.replace('name:', '').strip()
                        if line.startswith('description:'):
                            description = line.replace('description:', '').strip()
                    
                    # Extract command
                    match = re.search(r'`((?:python3|bash) .agent/skills/([^`]+))`', content)
                    if match:
                        full_cmd = match.group(1)
                        cmd_parts = full_cmd.split(' ', 1)
                        cmd_prefix = cmd_parts[0]
                        rel_path = f".agent/skills/{match.group(2)}"
                        abs_path = os.path.join(self.project_root, rel_path)
                        command = f"{cmd_prefix} {abs_path}"
                    
                    if description and command:
                        text_to_embed = f"{name}: {description}"
                        
                        # Only re-embed if text changed or not in cache
                        cache_id = f"{skill_name}"
                        if cache_id not in self.data["skills"] or self.data["skills"][cache_id]["text"] != text_to_embed:
                            embedding = self.model.encode(text_to_embed).tolist()
                            self.data["skills"][cache_id] = {
                                "name": name,
                                "description": description,
                                "command": command,
                                "text": text_to_embed,
                                "embedding": embedding
                            }
                        
                        current_skills[cache_id] = self.data["skills"][cache_id]
                        skills_indexed += 1
                        print(f"✅ Indexed: {name}")
                        
                except Exception as e:
                    print(f"⚠️ Error indexing {skill_name}: {e}")
        
        # Clean up removed skills
        self.data["skills"] = current_skills
        self._save_cache()
        return skills_indexed
    
    def search_skills(self, query, top_k=5):
        """Search for relevant skills using cosine similarity"""
        if not self.data["skills"]:
            self.index_all_skills()
        
        if not self.data["skills"]:
            return ""

        # Embed query
        query_vec = self.model.encode(query)
        
        # Calculate similarities
        results = []
        for skill_id, skill in self.data["skills"].items():
            skill_vec = np.array(skill["embedding"])
            # Cosine similarity
            similarity = np.dot(query_vec, skill_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(skill_vec))
            results.append((similarity, skill))
        
        # Sort by similarity
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Filter top_k
        top_results = results[:top_k]
        
        skills_context = "\n🚀 AVAILABLE SKILLS & CUSTOM SCRIPTS:\n"
        for score, skill in top_results:
            # Only include if similarity is reasonable (e.g. > 0.3)
            if score > 0.2:
                skills_context += f"- {skill['name']}: {skill['description']}\n"
                skills_context += f"  COMMAND: {skill['command']}\n"
        
        return skills_context
    
    def get_all_skills(self):
        """Get all skills"""
        if not self.data["skills"]:
            self.index_all_skills()
        
        skills_context = "\n🚀 AVAILABLE SKILLS & CUSTOM SCRIPTS:\n"
        for skill in self.data["skills"].values():
            skills_context += f"- {skill['name']}: {skill['description']}\n"
            skills_context += f"  COMMAND: {skill['command']}\n"
        
        return skills_context

# Global instance
_skill_indexer = None

def get_skill_indexer(project_root):
    global _skill_indexer
    if _skill_indexer is None:
        _skill_indexer = SkillIndexer(project_root)
    return _skill_indexer
