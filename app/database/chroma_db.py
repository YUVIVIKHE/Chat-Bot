import chromadb
from chromadb.config import Settings
import os
from app.config.settings import CHROMA_PERSIST_DIRECTORY

class ChromaDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaDBManager, cls).__new__(cls)
            cls._instance._client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIRECTORY,
                settings=Settings(allow_reset=True)
            )
            # Ensure collections exist
            cls._instance._setup_collections()
        return cls._instance

    def _setup_collections(self):
        """Set up default collections for the application."""
        collections = {
            "qa_pairs": "Store Q&A pairs for compliance bot",
            "user_queries": "Store user queries and responses",
            "iso_bot": "Collection for ISO 27001 related content",
            "risk_bot": "Collection for risk assessment related content",
            "compliance_coach": "Collection for compliance training content",
            "audit_buddy": "Collection for audit preparation content",
            "policy_navigator": "Collection for policy navigation content",
            "security_advisor": "Collection for security advice content"
        }
        
        existing_collections = [col.name for col in self._client.list_collections()]
        
        for name, description in collections.items():
            if name not in existing_collections:
                self._client.create_collection(
                    name=name,
                    metadata={"description": description}
                )
    
    def get_collection(self, collection_name):
        """Get a collection by name."""
        return self._client.get_collection(name=collection_name)
    
    def add_documents(self, collection_name, documents, metadatas=None, ids=None):
        """Add documents to a collection."""
        collection = self.get_collection(collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas if metadatas else [{}] * len(documents),
            ids=ids if ids else [f"id_{i}" for i in range(len(documents))]
        )
    
    def query_collection(self, collection_name, query_text, n_results=5):
        """Query a collection with text."""
        collection = self.get_collection(collection_name)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results
    
    def get_all_collections(self):
        """Get all collections."""
        return self._client.list_collections()

# Create a singleton instance
chroma_db = ChromaDBManager() 