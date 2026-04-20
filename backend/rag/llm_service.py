import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Union, Tuple
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import google.generativeai as genai
from .vector_store import RAGVectorStore

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    @abstractmethod
    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        pass

class GeminiProvider(LLMProvider):
    """Google Gemini implementation."""
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found in environment variables.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"response_mime_type": "application/json"}
        )

    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        try:
            # For Gemini 1.5, we can use system_instruction in the constructor or content
            # Here we just prepend it if provided for simplicity, or use formal system_instruction if available
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=self.model.model_name,
                    system_instruction=system_instruction,
                    generation_config={"response_mime_type": "application/json"}
                )
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return json.dumps({"error": "LLM generation failed", "detail": str(e)})

class ContextAggregator:
    """Helper to group and merge RAG chunks for LLM context."""
    
    @staticmethod
    def aggregate_context(chunks: List[Tuple[Dict[str, Any], float]], top_n_per_candidate: int = 3) -> str:
        """
        Groups chunks by candidate_id and returns a formatted string.
        """
        candidates = {}
        
        for meta, score in chunks:
            # Metadata is nested in RAGDocument.metadata if stored via matcher/loader
            # actually RAGVectorStore returns the dict representation of RAGDocument
            doc_meta = meta.get("metadata", {})
            cand_id = doc_meta.get("candidate_id", "unknown")
            cand_name = doc_meta.get("name", "Unknown Candidate")
            
            if cand_id not in candidates:
                candidates[cand_id] = {
                    "name": cand_name,
                    "experience": doc_meta.get("experience", 0),
                    "skills": doc_meta.get("skills", []),
                    "chunks": []
                }
            
            if len(candidates[cand_id]["chunks"]) < top_n_per_candidate:
                candidates[cand_id]["chunks"].append(meta.get("text", ""))

        # Format context string
        context_parts = []
        for cand_id, data in candidates.items():
            cand_str = f"### Candidate: {data['name']} (ID: {cand_id})\n"
            cand_str += f"Experience: {data['experience']} years\n"
            cand_str += f"Skills: {', '.join(data['skills'])}\n"
            cand_str += "Relevant Resume Chunks:\n"
            for i, chunk in enumerate(data["chunks"]):
                cand_str += f"- [Chunk {i+1}]: {chunk}\n"
            context_parts.append(cand_str)
            
        return "\n\n".join(context_parts)

class LLMService:
    """
    Main service for AI Recruiter Intelligence.
    Handles RAG integration, strict prompting, and output formatting.
    """
    def __init__(self, provider_type: str = None):
        if provider_type is None:
            provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
            
        if provider_type == "gemini":
            self.provider = GeminiProvider()
        else:
            # Default to Gemini for now as per user request
            self.provider = GeminiProvider()
            
        self._cache = {} # Simple in-memory cache for queries

    def _get_cache_key(self, query: str, context_hash: str) -> str:
        return hashlib.md5(f"{query}:{context_hash}".encode()).hexdigest()

    def query(self, query: str, retrieved_chunks: List[Any], matcher_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate a structured answer based on retrieved candidate context.
        """
        # 1. Prepare Context
        from typing import Tuple
        context_str = ContextAggregator.aggregate_context(retrieved_chunks)
        
        # Add Phase 3 Matcher results if available
        matcher_context = ""
        if matcher_results and "candidates" in matcher_results:
            matcher_context = "\n### Pre-calculated Matcher Scores (Phase 3):\n"
            for cand in matcher_results["candidates"]:
                matcher_context += f"- {cand['name']} (ID: {cand['candidate_id']}): Score {cand['score']}, Matched: {cand['matched_skills']}, Missing: {cand['missing_skills']}\n"

        full_context = f"{context_str}\n{matcher_context}"
        
        # 2. Check Cache
        context_hash = hashlib.md5(full_context.encode()).hexdigest()
        cache_key = self._get_cache_key(query, context_hash)
        if cache_key in self._cache:
            logger.info("Serving query response from cache")
            return self._cache[cache_key]

        # 3. Detect Comparison Query
        is_comparison = any(word in query.lower() for word in ["compare", "difference", "versus", "vs", "between", "better"])
        comparison_instruction = ""
        if is_comparison:
            comparison_instruction = (
                "\n6. This is a COMPARISON query. Structure your answer to highlight key differences "
                "and similarities between candidates in terms of skills, experience, and fit. "
                "Provide a clear recommendation if applicable."
            )

        # 4. Construct Prompt
        system_instruction = (
            "You are an expert AI Technical Recruiter. Your goal is to analyze candidate resumes "
            "provided in the context and answer queries factually and concisely.\n\n"
            "STRICT CONSTRAINTS:\n"
            "1. ONLY use the provided context. Do NOT use outside knowledge.\n"
            "2. DO NOT hallucinate candidates or skills. If the data is not present, say 'insufficient data'.\n"
            "3. If no relevant candidates are found in the context, return an answer stating no matches were found.\n"
            "4. Your output MUST be valid JSON.\n"
            f"5. For each candidate mentioned, include their candidate_id, score, reasoning, and matched_skills.{comparison_instruction}"
        )

        prompt = (
            f"USER QUERY: {query}\n\n"
            f"CANDIDATE CONTEXT:\n{full_context}\n\n"
            "RESPONSE FORMAT (JSON):\n"
            "{\n"
            "  \"answer\": \"Overall summary of findings\",\n"
            "  \"top_candidates\": [\n"
            "    {\n"
            "      \"candidate_id\": \"id\",\n"
            "      \"name\": \"name\",\n"
            "      \"score\": 0.95,\n"
            "      \"matched_skills\": [\"skill1\", \"skill2\"],\n"
            "      \"reasoning\": \"Why this candidate is a good/bad match based ONLY on context\"\n"
            "    }\n"
            "  ],\n"
            "  \"insights\": \"Specific recruiter-level insights about the talent pool\",\n"
            "  \"confidence\": \"high|medium|low\"\n"
            "}"
        )

        # 4. Call LLM
        raw_response = self.provider.generate_response(prompt, system_instruction)
        
        # 5. Parse and Format
        try:
            parsed = self._robust_json_parse(raw_response)
            
            # Simple check for "no match"
            if not parsed.get("top_candidates") and "no" in parsed.get("answer", "").lower():
                parsed["answer"] = "No strong matches found based on the provided query and candidate database."
            
            self._cache[cache_key] = parsed
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {
                "answer": "Error processing the query. The AI response was malformed.",
                "top_candidates": [],
                "insights": str(e),
                "confidence": "low"
            }

    def _robust_json_parse(self, text: str) -> Dict[str, Any]:
        """Attempts to extract and parse JSON from LLM output."""
        try:
            # Clean possible markdown formatting
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback: simple regex or manual fix if needed (skipping for now)
            raise
