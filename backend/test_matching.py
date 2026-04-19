import os
import sys
import unittest
import numpy as np
import tempfile
import shutil
from typing import List, Dict, Any

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.embedder import RAGEmbedder
from rag.vector_store import RAGVectorStore
from rag.loader import ResumeLoader
from rag.matcher import CandidateMatcher

class TestCandidateMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.embedder = RAGEmbedder.get_instance()
        cls.test_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir)

    def setUp(self):
        self.vector_store = RAGVectorStore(dimension=384)
        self.resume_loader = ResumeLoader(self.vector_store, self.embedder)
        self.matcher = CandidateMatcher(self.vector_store, self.embedder)

    def create_fake_docx(self, name, text):
        import docx
        path = os.path.join(self.test_dir, f"{name.replace(' ', '_')}.docx")
        doc = docx.Document()
        doc.add_paragraph(text)
        doc.save(path)
        return path

    def test_basic_matching_ranking(self):
        """Test that candidates are ranked correctly based on hybrid scores."""
        # 1. Setup Candidates
        # Python expert, 8 years
        c1_path = self.create_fake_docx("Python Expert", "John Python. Expert Python developer with 8 years of experience. Skills: Python, Django, AWS, Docker.")
        # Java expert, 10 years
        c2_path = self.create_fake_docx("Java Veteran", "Steve Java. Senior Java Engineer with 10 years experience. Skills: Java, Spring Boot, MySQL, Kubernetes.")
        # Junior Python, 2 years
        c3_path = self.create_fake_docx("Junior Python", "Alice Junior. Junior Developer with 2 years of experience. Skills: Python, HTML, CSS.")

        self.resume_loader.ingest(c1_path, candidate_id="cand_python_01")
        self.resume_loader.ingest(c2_path, candidate_id="cand_java_01")
        self.resume_loader.ingest(c3_path, candidate_id="cand_python_jr")

        # 2. Match against Python Job
        jd = """
        Senior Python Backend Engineer
        Requirements:
        - 5+ years of experience with Python
        - Experience with Cloud (AWS/Azure)
        - Familiar with Docker and Containerization
        """
        
        result = self.matcher.match_candidates_to_job(jd, min_experience=0)
        
        self.assertTrue(result["success"])
        candidates = result["candidates"]
        self.assertGreater(len(candidates), 0)
        
        # John should be #1 due to Python + AWS + Docker + 8yrs exp
        self.assertEqual(candidates[0]["candidate_id"], "cand_python_01")
        self.assertGreater(candidates[0]["score"], candidates[1]["score"])
        
        # Verify explainability
        self.assertIn("python", [s.lower() for s in candidates[0]["matched_skills"]])
        self.assertGreater(candidates[0]["experience"], 5)

    def test_experience_filter(self):
        """Test that min_experience filter works correctly."""
        c1_path = self.create_fake_docx("Senior", "Senior Dev. 10 years exp. Skills: Python.")
        c2_path = self.create_fake_docx("Junior", "Junior Dev. 2 years exp. Skills: Python.")
        
        self.resume_loader.ingest(c1_path, candidate_id="senior_01")
        self.resume_loader.ingest(c2_path, candidate_id="junior_01")
        
        jd = "Python Developer with 5 years exp."
        
        # Use filter
        result = self.matcher.match_candidates_to_job(jd, min_experience=5)
        
        ids = [c["candidate_id"] for c in result["candidates"]]
        self.assertIn("senior_01", ids)
        self.assertNotIn("junior_01", ids)

    def test_no_matches_edge_case(self):
        """Test behavior when no candidates match at all."""
        jd = "Rust Developer with 15 years experience in Blockchain and WASM."
        
        result = self.matcher.match_candidates_to_job(jd)
        
        # It should still succeed but return an empty or warning message if no candidates exist
        # If candidates exist but don't match semantic or filters, handle gracefully
        # In our vector store we have no Rust devs.
        
        # If the store is empty, it returns message
        empty_vs = RAGVectorStore(dimension=384)
        empty_matcher = CandidateMatcher(empty_vs, self.embedder)
        res_empty = empty_matcher.match_candidates_to_job(jd)
        self.assertIn("No matching candidates", res_empty["message"])

    def test_conflicting_candidates_ranking(self):
        """Test ranking between high skills vs high similarity."""
        # Candidate A: High Similarity (exact semantic match in text) but fewer explicit skills
        # Candidate B: Lower Similarity but more explicit matched skills
        
        # JD: "Expert in Cloud Infrastructure and DevOps"
        # A: "I specialize in cloud infrastructure and devops. I love scaling systems." (No explicit skills mentioned from DB)
        # B: "System Administrator. Skills: AWS, Docker, Jenkins, Kubernetes." (Explicit skills but generic text)
        
        pass # This would be a more complex test to fine-tune weights

if __name__ == "__main__":
    unittest.main()
