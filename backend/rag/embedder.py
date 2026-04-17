import threading
import torch
import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

class RAGEmbedder:
    """
    Singleton Embedder class for the RAG pipeline.
    Uses sentence-transformers/all-MiniLM-L6-v2 by default.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(RAGEmbedder, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if self._initialized:
            return
        
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load model once
        self.model = SentenceTransformer(model_name, device=self.device)
        self._initialized = True

    def embed_text(self, text: str) -> np.ndarray:
        """
        Convert a single text string into a normalized embedding vector.
        """
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Convert a list of text strings into a batch of normalized embedding vectors.
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings

    @classmethod
    def get_instance(cls, model_name: str = "all-MiniLM-L6-v2"):
        """Get the singleton instance of RAGEmbedder."""
        return cls(model_name)
