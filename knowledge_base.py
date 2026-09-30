import os
from pathlib import Path

class KnowledgeBase:
    def __init__(self):
        self.documents = []
        self._load_knowledge_simple()

    def _load_knowledge_simple(self):
        """Load knowledge into memory for simple text search"""
        knowledge_path = Path(__file__).parent / "knowledge" / "vera_knowledge.md"
        
        if not knowledge_path.exists():
            print(f"Warning: Knowledge file not found at {knowledge_path}")
            return
        
        with open(knowledge_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into chunks by sections
        sections = content.split('\n## ')
        
        for i, section in enumerate(sections):
            if section.strip():
                lines = section.split('\n')
                title = lines[0].strip() if lines else f"Section {i}"
                body = '\n'.join(lines[1:]).strip()
                self.documents.append({
                    'title': title,
                    'content': body
                })
        
        print(f"Loaded {len(self.documents)} knowledge sections for instant text search")

    def query(self, query_text: str, n_results: int = 3):
        if not self.documents:
            return []
        
        # Simple keyword matching
        query_lower = query_text.lower()
        scored_docs = []
        
        for doc in self.documents:
            score = 0
            # Check for keyword matches in title and content
            for word in query_lower.split():
                # Avoid counting very common short words
                if len(word) > 3:
                    if word in doc['title'].lower():
                        score += 3
                    if word in doc['content'].lower():
                        score += 1
            
            if score > 0:
                scored_docs.append((score, doc['content']))
        
        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:n_results]]

# Singleton instance
_kb_instance = None

def get_knowledge_base():
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
