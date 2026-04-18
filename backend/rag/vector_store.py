import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
from .schema import RAGDocument

class RAGVectorStore:
    """
    Vector store implementation using FAISS for embeddings and JSON for metadata.
    """
    def __init__(self, dimension: int = 384): # Default dimension for all-MiniLM-L6-v2
        self.dimension = dimension
        # Use IndexFlatIP for Cosine Similarity (requires normalized vectors)
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: List[Dict[str, Any]] = []

    def add_documents(self, documents: List[RAGDocument], embeddings: np.ndarray):
        """
        Add documents and their corresponding embeddings to the store.
        """
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.dimension}, got {embeddings.shape[1]}")

        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Add to metadata list
        for doc in documents:
            self.metadata.append(doc.dict())

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieve top-k most similar documents.
        Returns a list of tuples containing (document_data, similarity_score).
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx != -1 and idx < len(self.metadata):
                results.append((self.metadata[idx], float(distances[0][i])))
                
        return results

    def save(self, index_path: str, metadata_path: str):
        """
        Save the FAISS index and metadata to disk.
        """
        faiss.write_index(self.index, index_path)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load(self, index_path: str, metadata_path: str):
        """
        Load the FAISS index and metadata from disk.
        """
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        
        # Verify alignment
        if self.index.ntotal != len(self.metadata):
            print(f"Warning: Index count ({self.index.ntotal}) and metadata count ({len(self.metadata)}) mismatch!")

    def validate_integrity(self) -> Dict[str, Any]:
        """
        Verify that the FAISS index and metadata are perfectly aligned.
        """
        ntotal = self.index.ntotal
        meta_count = len(self.metadata)
        is_consistent = ntotal == meta_count
        
        return {
            "is_consistent": is_consistent,
            "index_count": ntotal,
            "metadata_count": meta_count,
            "status": "valid" if is_consistent else "error"
        }
