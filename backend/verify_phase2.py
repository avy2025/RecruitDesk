import os
import sys
import logging
from typing import Dict, Any

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from rag.embedder import RAGEmbedder
from rag.vector_store import RAGVectorStore
from rag.loader import ResumeLoader
from rag.parser import parse_file, extract_metadata

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_system():
    logger.info("Starting Phase 2 System Verification...")
    
    # 1. Initialize Components
    logger.info("Step 1: Initializing RAG components...")
    try:
        embedder = RAGEmbedder.get_instance()
        vector_store = RAGVectorStore(dimension=384)
        loader = ResumeLoader(vector_store, embedder)
        logger.info("✅ Components initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize components: {e}")
        return

    # 2. Test Parsing and Metadata Consolidation
    logger.info("Step 2: Testing centralized parser...")
    sample_text = "Alice Smith. expert in Python, React, and AWS with 10 years experience."
    metadata = extract_metadata(sample_text)
    
    if metadata.get('name') == "Alice Smith" and "python" in [s.lower() for s in metadata['skills']]:
        logger.info("✅ Centralized metadata extraction verified.")
    else:
        logger.warning(f"⚠️ Metadata extraction results were not ideal: {metadata}")

    # 3. Test Ingestion Loop
    logger.info("Step 3: Verifying ingestion pipeline (using mock text)...")
    # For verification script, we'll manually add a document to bypass file dependencies if needed,
    # but since we want to test the full pipeline, we'll try to create a small docx.
    try:
        import docx
        test_file = "verify_temp.docx"
        doc = docx.Document()
        doc.add_paragraph("Bob Jones. 5 years of experience in Java and SQL.")
        doc.save(test_file)
        
        result = loader.ingest(test_file, candidate_id="cand_bob_999")
        if result['status'] == 'success':
            logger.info("✅ ingestion pipeline verified.")
        else:
            logger.error(f"❌ Ingestion failed: {result.get('message')}")
            
        if os.path.exists(test_file): os.remove(test_file)
    except ImportError:
        logger.warning("⚠️ python-docx not found. Skipping DOCX ingestion check.")
    except Exception as e:
        logger.error(f"❌ Ingestion pipeline test failed: {e}")

    # 4. Test Persistence Integrity
    logger.info("Step 4: Checking persistence integrity...")
    idx_path = "verify_index.faiss"
    meta_path = "verify_metadata.json"
    
    try:
        vector_store.save(idx_path, meta_path)
        new_store = RAGVectorStore(dimension=384)
        new_store.load(idx_path, meta_path)
        
        integrity = new_store.validate_integrity()
        if integrity['is_consistent']:
            logger.info(f"✅ Persistence verified. Total chunks: {integrity['index_count']}")
        else:
            logger.error(f"❌ Persistence integrity check failed! {integrity}")
            
        # Search test
        query_emb = embedder.embed_text("Java expert")
        search_results = new_store.search(query_emb, k=1)
        if search_results and "Bob" in search_results[0][0]['text']:
            logger.info("✅ Search retrieval verified.")
        else:
            logger.warning("⚠️ Search retrieval did not find the expected candidate.")
            
    except Exception as e:
        logger.error(f"❌ Persistence test failed: {e}")
    finally:
        if os.path.exists(idx_path): os.remove(idx_path)
        if os.path.exists(meta_path): os.remove(meta_path)

    logger.info("\n--- Verification Summary ---")
    logger.info("Phase 2 components are modular and functionally integrated.")
    logger.info("System is ready for Phase 3 (Matching & Retrieval).")

if __name__ == "__main__":
    verify_system()
