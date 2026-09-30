import os
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: ChromaDB not installed. Knowledge base queries will be disabled.")

class KnowledgeBase:
    def __init__(self):
        if not CHROMADB_AVAILABLE:
            self.client = None
            self.collection = None
            return
            
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="vera_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        self._load_knowledge()

    def _load_knowledge(self):
        if not CHROMADB_AVAILABLE:
            print("ChromaDB not available - skipping knowledge base loading")
            return
            
        knowledge_path = Path(__file__).parent / "knowledge" / "vera_knowledge.md"
        
        if not knowledge_path.exists():
            raise FileNotFoundError(f"Knowledge file not found at {knowledge_path}")
        
        with open(knowledge_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into chunks by sections
        sections = content.split('\n## ')
        
        # Clear existing documents
        if self.collection.count() > 0:
            self.collection.delete()
        
        documents = []
        metadatas = []
        ids = []
        
        for i, section in enumerate(sections):
            if section.strip():
                lines = section.split('\n')
                title = lines[0].strip() if lines else f"Section {i}"
                body = '\n'.join(lines[1:]).strip()
                
                documents.append(body)
                metadatas.append({"source": "vera_knowledge.md", "section": title})
                ids.append(f"doc_{i}")
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Loaded {len(documents)} knowledge sections into ChromaDB")

    def query(self, query_text: str, n_results: int = 3):
        if not CHROMADB_AVAILABLE:
            print("ChromaDB not available - returning empty results")
            return []
            
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        return results['documents'][0] if results['documents'] else []

# Singleton instance
_kb_instance = None

def get_knowledge_base():
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
