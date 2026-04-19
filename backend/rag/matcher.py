import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from .vector_store import RAGVectorStore
from .embedder import RAGEmbedder
from .loader import JobLoader
from .parser import extract_job_metadata

logger = logging.getLogger(__name__)

class CandidateMatcher:
    """
    Core engine for matching candidate resumes to job descriptions.
    Uses a hybrid scoring system (Similarity, Skills, Experience).
    """
    def __init__(self, vector_store: RAGVectorStore, embedder: RAGEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.job_loader = JobLoader(vector_store, embedder)

    def match_candidates_to_job(
        self, 
        job_description: str, 
        top_k_candidates: int = 5,
        min_experience: float = 0,
        required_skills: List[str] = None,
        store_job: bool = False
    ) -> Dict[str, Any]:
        """
        Main pipeline for candidate matching.
        """
        # 1. Process Job Description
        job_result = self.job_loader.ingest_job(job_description, store_job=store_job)
        job_meta = job_result["metadata"]
        jd_embeddings = np.array(job_result["embeddings"]) # Chunks of JD

        # 2. Retrieve Relevant Resume Chunks
        # Search for each JD chunk and aggregate
        chunk_results = []
        for i in range(len(jd_embeddings)):
            matches = self.vector_store.search(
                jd_embeddings[i], 
                k=20, # Get enough chunks for robust aggregation
                filter_dict={"type": "resume"}
            )
            chunk_results.extend(matches)

        if not chunk_results:
            return {
                "success": True,
                "message": "No matching candidates found in the database.",
                "job_metadata": job_meta,
                "candidates": []
            }

        # 3. Aggregate results by candidate_id
        candidate_data = {}
        for doc_dict, score in chunk_results:
            # Metadata is nested in RAGDocument.metadata
            meta = doc_dict.get("metadata", {})
            cand_id = meta.get("candidate_id")
            if not cand_id:
                continue
            
            if cand_id not in candidate_data:
                candidate_data[cand_id] = {
                    "id": cand_id,
                    "name": meta.get("name"),
                    "skills": meta.get("skills", []),
                    "experience": meta.get("experience", 0.0),
                    "chunk_scores": []
                }
            candidate_data[cand_id]["chunk_scores"].append(score)

        # 4. Filter and Score Candidates
        results = []
        req_exp = job_meta.get("experience_required", 0.0)
        jd_skills_normalized = set(s.lower().strip() for s in job_meta.get("required_skills", []))
        
        # Add user-provided required skills if any
        if required_skills:
            jd_skills_normalized.update(s.lower().strip() for s in required_skills)

        for cand_id, data in candidate_data.items():
            # Apply hard filters first
            if data["experience"] < min_experience:
                continue
            
            # Semantic Similarity Score (Aggregation)
            scores = sorted(data["chunk_scores"], reverse=True)
            max_score = scores[0]
            avg_top_k = np.mean(scores[:3]) if len(scores) >= 1 else 0
            # Formula: 0.7 * max + 0.3 * avg
            sim_score = (0.7 * max_score) + (0.3 * avg_top_k)
            # Normalize to 0-1 range (assuming cosine similarity is already roughly 0-1)
            sim_score = max(0.0, min(1.0, float(sim_score)))

            # Skill Score
            cand_skills_normalized = set(s.lower().strip() for s in data["skills"])
            matched_skills = jd_skills_normalized.intersection(cand_skills_normalized)
            missing_skills = jd_skills_normalized - cand_skills_normalized
            
            skill_overlap_ratio = (len(matched_skills) / len(jd_skills_normalized)) if jd_skills_normalized else 1.0
            skill_score = skill_overlap_ratio

            # Experience Score
            if req_exp > 0:
                experience_score = min(data["experience"] / req_exp, 1.0)
            else:
                experience_score = 1.0 # No requirement met by default

            # Final Weighted Score (60% Sim, 30% Skill, 10% Exp)
            final_score = (sim_score * 0.6) + (skill_score * 0.3) + (experience_score * 0.1)
            
            # Generate Reasoning
            reasoning = self._generate_reasoning(
                sim_score, skill_score, experience_score, 
                data["experience"], req_exp, 
                list(matched_skills)
            )

            results.append({
                "candidate_id": cand_id,
                "name": data["name"],
                "score": round(float(final_score), 4),
                "similarity_score": round(sim_score, 4),
                "skill_score": round(skill_score, 4),
                "experience_score": round(experience_score, 4),
                "matched_skills": sorted(list(matched_skills)),
                "missing_skills": sorted(list(missing_skills)),
                "experience": data["experience"],
                "reasoning": reasoning
            })

        # 5. Rank and Cap Results
        results.sort(key=lambda x: x["score"], reverse=True)
        top_results = results[:top_k_candidates]

        return {
            "success": True,
            "job_metadata": job_meta,
            "total_candidates_processed": len(candidate_data),
            "total_matches": len(results),
            "candidates": top_results
        }

    def _generate_reasoning(
        self, sim: float, skill: float, exp: float, 
        cand_exp: float, req_exp: float, matched: List[str]
    ) -> str:
        """Generate a concise, recruiter-friendly reasoning string."""
        reasons = []
        if sim > 0.75:
            reasons.append("Strong semantic match to job focus.")
        elif sim > 0.6:
            reasons.append("Good relevance to core responsibilities.")
            
        if skill > 0.8:
            reasons.append("Excellent skill alignment.")
        elif skill > 0.5:
            reasons.append(f"Matches several key skills ({len(matched)}).")
        
        if cand_exp >= req_exp and req_exp > 0:
            reasons.append(f"Meets or exceeds experience requirements ({cand_exp} yrs).")
        elif cand_exp > 0:
             reasons.append(f"Has {cand_exp} years of relevant background.")

        if not reasons:
            return "Potential match based on overlapping keywords and background."
            
        return " ".join(reasons[:2]) # Keep it concise
