import logging
import hashlib
import re
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

        is_comparison = any(word in query.lower() for word in ["compare", "difference", "versus", "vs", "between", "better"])
        comparison_instruction = ""
        if is_comparison:
            comparison_instruction = (
                "\n6. This is a COMPARISON query. Structure your answer to highlight key differences "
                "and similarities between candidates in terms of skills, experience, and fit. "
                "Use the provided structured candidate data for accurate comparisons."
            )

    def extract_intent(self, query: str) -> Dict[str, Any]:
        """
        Hybrid Intent Extraction: Rule-based for filters, LLM as fallback.
        """
        filters = {"skills": [], "min_experience": None}
        
        # Rule 1: Experience (e.g., "5+ years", "only 3 years")
        exp_match = re.search(r'(\d+)\s*\+?\s*years?', query.lower())
        if exp_match:
            filters["min_experience"] = float(exp_match.group(1))
            
        # Rule 2: Exclusions (simple heuristic)
        if "exclude" in query.lower() or "no " in query.lower():
            # This would normally need more complex NLP or LLM
            pass
            
        return filters

    def rewrite_query(self, query: str, history: List[Dict], last_filters: Dict) -> str:
        """
        Rewrites a follow-up query into a standalone version using conversation history.
        """
        if not history:
            return query

        # If it's a very short follow-up, it definitely needs rewriting
        is_follow_up = len(query.split()) < 5 or any(word in query.lower() for word in ["those", "them", "they", "only", "about", "her", "him"])
        
        if not is_follow_up:
            return query

        system_instruction = (
            "You are a query optimization assistant for a recruitment RAG system. "
            "Your task is to rewrite user follow-up queries into standalone, descriptive search queries "
            "that incorporate relevant context from the conversation history."
        )
        
        history_context = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history[-3:]])
        
        prompt = (
            f"CONVERSATION HISTORY:\n{history_context}\n\n"
            f"CURRENT FILTERS: {last_filters}\n\n"
            f"FOLLOW-UP QUERY: {query}\n\n"
            "REWRITE this follow-up into a single standalone search query for a vector database. "
            "Return ONLY the rewritten query string as JSON."
            "\nExample: If user said 'Find React devs' then 'only experienced ones', rewrite to 'Experienced React developers'."
            "\nFORMAT: {\"rewritten_query\": \"...\"}"
        )

        try:
            raw = self.provider.generate_response(prompt, system_instruction)
            parsed = self._robust_json_parse(raw)
            return parsed.get("rewritten_query", query)
        except:
            return query

    def query(self, query: str, retrieved_chunks: List[Any], 
              matcher_results: Optional[Dict] = None, 
              history: List[Dict] = None,
              last_filters: Dict = None,
              last_candidates: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate a structured answer based on retrieved context and conversation history.
        """
        # 1. Prepare Context
        context_str = ContextAggregator.aggregate_context(retrieved_chunks)
        
        # Add Phase 3 Matcher results
        matcher_context = ""
        if matcher_results and "candidates" in matcher_results:
            matcher_context = "\n### Pre-calculated Matcher Scores (Phase 3):\n"
            for cand in matcher_results["candidates"]:
                matcher_context += f"- {cand['name']} (ID: {cand['candidate_id']}): Score {cand['score']}, Matched: {cand['matched_skills']}, Missing: {cand['missing_skills']}\n"

        # Add History Context if available
        history_context = ""
        if history:
            history_context = "\n### Recent Conversation History:\n"
            for msg in history[-3:]: # last 3 turns
                 history_context += f"- {msg['role'].upper()}: {msg['content']}\n"

        # Add Structured Memory for consistency
        structured_context = ""
        if last_filters or last_candidates:
            structured_context = "\n### Active Memory & Filter Context:\n"
            if last_filters:
                structured_context += f"Current Filters: {last_filters}\n"
            if last_candidates:
                structured_context += "Previously Discussed Candidates: " + ", ".join([c['name'] for c in last_candidates]) + "\n"

        full_context = f"{structured_context}\n{history_context}\n{context_str}\n{matcher_context}"
        
        # 2. Check Cache (Include history hash)
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
                "\n6. This is a COMPARISON query. Use the 'Previously Discussed Candidates' and 'Matcher Scores' "
                "to provide a detailed comparison. Highlight trade-offs in skills and experience."
            )

        # 4. Construct Prompt
        system_instruction = (
            "You are an expert AI Technical Recruiter. Your goal is to analyze candidate resumes "
            "provided in the context and answer queries factually and concisely. "
            "Leverage the conversation history to provide contextual and follow-up answers.\n\n"
            "STRICT CONSTRAINTS:\n"
            "1. ONLY use the provided context. Do NOT use outside knowledge.\n"
            "2. DO NOT repeat previous answers unnecessarily. Refer back to them if needed.\n"
            "3. If context changed mid-conversation (e.g., new filters), acknowledge the change.\n"
            "4. Your output MUST be valid JSON.\n"
            f"5. For each candidate mentioned, include their candidate_id, score, reasoning, and matched_skills.{comparison_instruction}"
        )

        prompt = (
            f"USER QUERY: {query}\n\n"
            f"CANDIDATE AND CONVERSATION CONTEXT:\n{full_context}\n\n"
            "RESPONSE FORMAT (JSON):\n"
            "{\n"
            "  \"answer\": \"Detailed summary answering the user query in context\",\n"
            "  \"top_candidates\": [\n"
            "    {\n"
            "      \"candidate_id\": \"id\",\n"
            "      \"name\": \"name\",\n"
            "      \"score\": 0.95,\n"
            "      \"matched_skills\": [\"skill1\", \"skill2\"],\n"
            "      \"reasoning\": \"Context-aware reasoning why this candidate fits the query\"\n"
            "    }\n"
            "  ],\n"
            "  \"insights\": \"Specific recruiter-level insights\",\n"
            "  \"confidence\": \"high|medium|low\",\n"
            "  \"detected_filters\": {\"skills\": [], \"min_experience\": 0}\n"
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
