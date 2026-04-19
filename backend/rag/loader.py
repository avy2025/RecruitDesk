import uuid
import logging
from typing import List, Dict, Any, Optional
from .parser import parse_file, extract_metadata
from .schema import RAGDocument, DocumentMetadata
from .embedder import RAGEmbedder
from .vector_store import RAGVectorStore

logger = logging.getLogger(__name__)

class ResumeLoader:
    """
    Orchestrates the resume ingestion pipeline:
    parse -> extract metadata -> chunk -> embed -> store
    """
    def __init__(self, vector_store: RAGVectorStore, embedder: RAGEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks. 
        Approximates tokens by splitting on whitespace.
        """
        words = text.split()
        if not words:
            return []
            
        chunks = []
        step = chunk_size - overlap
        if step <= 0:
            step = chunk_size
            
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
        return chunks

    def ingest(self, file_path: str, candidate_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the full ingestion pipeline for a single resume file.
        """
        # 1. Parse File
        try:
            raw_text = parse_file(file_path)
            if not raw_text or not raw_text.strip():
                raise ValueError(f"Extracted text is empty for {file_path}")
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to extract text: {str(e)}",
                "file_path": file_path
            }

        # 2. Extract Metadata
        metadata_raw = extract_metadata(raw_text)
        
        # 3. Generate candidate_id if not provided
        if not candidate_id:
            candidate_id = f"cand_{uuid.uuid4().hex[:8]}"

        # 4. Chunk Text
        text_len = len(raw_text.split())
        if text_len < 100:
            # For very small files, treat as a single chunk
            text_chunks = [raw_text]
        else:
            text_chunks = self.chunk_text(raw_text, chunk_size=450, overlap=50)
        
        # 5. Prepare RAGDocuments and Embeddings
        documents = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{candidate_id}_ch{i}"
            
            doc_metadata = DocumentMetadata(
                type="resume",
                source="resume",
                candidate_id=candidate_id,
                name=metadata_raw.get("name"),
                skills=metadata_raw.get("skills", []),
                experience=metadata_raw.get("experience", 0.0),
                confidence=metadata_raw.get("confidence", 0.0),
                chunk_id=chunk_id,
                chunk_index=i
            )
            
            doc = RAGDocument(
                id=chunk_id,
                text=chunk_text,
                metadata=doc_metadata
            )
            documents.append(doc)

        # 6. Create Embeddings in batch
        texts_to_embed = [doc.text for doc in documents]
        embeddings = self.embedder.embed_batch(texts_to_embed)

        # 7. Store in Vector DB
        self.vector_store.add_documents(documents, embeddings)

        # 8. Persist store (index and metadata)
        # Assuming standard paths for now or managing them via vector_store
        # For this phase, we let the caller handle save or use default names
        self.vector_store.save("resume_index.faiss", "resume_metadata.json")

        return {
            "status": "success",
            "candidate_id": candidate_id,
            "chunks_created": len(documents),
            "metadata": metadata_raw,
            "skills_detected": metadata_raw.get("skills", [])
        }

class JobLoader:
    """
    Orchestrates the job description ingestion pipeline:
    extract metadata -> chunk -> embed -> store (optional)
    """
    def __init__(self, vector_store: RAGVectorStore, embedder: RAGEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        if not words:
            return []
        chunks = []
        step = chunk_size - overlap
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
        return chunks

    def ingest_job(self, raw_text: str, job_id: Optional[str] = None, store_job: bool = False) -> Dict[str, Any]:
        """
        Extract metadata and optionally store JD in vector store.
        """
        from .parser import extract_job_metadata
        
        # 1. Extract Metadata
        metadata_raw = extract_job_metadata(raw_text)
        
        # 2. Generate job_id if not provided
        if not job_id:
            job_id = f"job_{uuid.uuid4().hex[:8]}"

        # 3. Chunk Text
        text_chunks = self.chunk_text(raw_text, chunk_size=400, overlap=50)
        
        # 4. Prepare Documents
        documents = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{job_id}_ch{i}"
            doc_metadata = DocumentMetadata(
                type="job",
                source="job",
                candidate_id=None, # Not applicable
                name=metadata_raw.get("role"), # Using role instead of name
                skills=metadata_raw.get("required_skills", []),
                experience=metadata_raw.get("experience_required", 0.0),
                confidence=1.0,
                chunk_id=chunk_id,
                chunk_index=i
            )
            doc = RAGDocument(id=chunk_id, text=chunk_text, metadata=doc_metadata)
            documents.append(doc)

        # 5. Get Embeddings
        texts_to_embed = [doc.text for doc in documents]
        embeddings = self.embedder.embed_batch(texts_to_embed)

        # 6. Store if requested
        if store_job:
            self.vector_store.add_documents(documents, embeddings)
            self.vector_store.save("resume_index.faiss", "resume_metadata.json")

        return {
            "status": "success",
            "job_id": job_id,
            "chunks_created": len(documents),
            "metadata": metadata_raw,
            "embeddings": embeddings.tolist() if not store_job else None # Return for transient matching
        }
