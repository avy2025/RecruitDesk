import os
import numpy as np
import sys

# Add the backend directory to sys.path to allow relative imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.schema import RAGDocument, DocumentMetadata
from rag.embedder import RAGEmbedder
from rag.vector_store import RAGVectorStore

def test_rag_pipeline():
    print("🚀 Starting RAG Pipeline Test...")

    # 1. Initialize Embedder
    print("--- 1. Initializing Embedder ---")
    embedder = RAGEmbedder.get_instance()
    
    # 2. Prepare Sample Documents
    print("--- 2. Preparing Sample Documents ---")
    docs = [
        RAGDocument(
            id="res_001",
            text="Experienced Python developer with 5 years in FastAPI and Machine Learning. Expert in building scalable APIs.",
            metadata=DocumentMetadata(type="resume", candidate_id="cand_001", skills=["python", "fastapi", "ml"], experience=5.0)
        ),
        RAGDocument(
            id="res_002",
            text="Senior Java Engineer specialized in Spring Boot and Microservices. 10 years of experience in enterprise software.",
            metadata=DocumentMetadata(type="resume", candidate_id="cand_002", skills=["java", "spring boot", "microservices"], experience=10.0)
        ),
        RAGDocument(
            id="res_003",
            text="Frontend Developer focusing on React and TypeScript. 3 years of experience building responsive dashboards.",
            metadata=DocumentMetadata(type="resume", candidate_id="cand_003", skills=["react", "typescript", "css"], experience=3.0)
        )
    ]
    
    # 3. Create Embeddings
    print("--- 3. Creating Embeddings ---")
    texts = [doc.text for doc in docs]
    embeddings = embedder.embed_batch(texts)
    print(f"Embeddings created. Shape: {embeddings.shape}")
    
    # Verify normalization
    norm = np.linalg.norm(embeddings[0])
    print(f"Embedding normalization check: {norm:.4f} (should be approx 1.0)")

    # 4. Initialize Vector Store and add documents
    print("--- 4. Initializing Vector Store ---")
    vector_store = RAGVectorStore(dimension=embeddings.shape[1])
    vector_store.add_documents(docs, embeddings)
    
    # 5. Test Search
    print("--- 5. Testing Search ---")
    query = "Looking for a backend expert who knows Python and how to build APIs."
    query_embedding = embedder.embed_text(query)
    
    results = vector_store.search(query_embedding, k=2)
    
    print(f"Search Results for query: '{query}'")
    for doc, score in results:
        print(f"ID: {doc['id']}, Score: {score:.4f}, Text: {doc['text'][:50]}...")

    # Validate ranking correctness
    if results[0][0]['id'] == "res_001":
        print("✅ Ranking correctness validated (Python developer ranked #1)")
    else:
        print("❌ Ranking correctness failed")

    # 6. Test Save and Load
    print("--- 6. Testing Persistence ---")
    index_path = "test_index.faiss"
    metadata_path = "test_metadata.json"
    
    vector_store.save(index_path, metadata_path)
    print(f"Store saved to {index_path} and {metadata_path}")
    
    new_store = RAGVectorStore(dimension=embeddings.shape[1])
    new_store.load(index_path, metadata_path)
    print("Store loaded.")
    
    new_results = new_store.search(query_embedding, k=1)
    if new_results[0][0]['id'] == "res_001":
        print("✅ Persistence validated")
    else:
        print("❌ Persistence check failed")

    # Cleanup
    if os.path.exists(index_path): os.remove(index_path)
    if os.path.exists(metadata_path): os.remove(metadata_path)
    
    print("\n🎉 RAG Pipeline Test Completed Successfully!")

if __name__ == "__main__":
    try:
        test_rag_pipeline()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
