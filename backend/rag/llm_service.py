import os
import json
import logging
import hashlib
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import google.generativeai as genai
from collections import OrderedDict
from .vector_store import RAGVectorStore

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Common skill keyword set for intent extraction (extends parser's DB if
# needed; kept here to avoid circular imports)
# ---------------------------------------------------------------------------
_COMMON_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "nodejs", "django", "flask", "fastapi", "spring", "express",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "git", "ci/cd", "devops", "graphql", "rest", "microservices",
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "pandas", "numpy", "scikit-learn", "spark", "hadoop",
    "c++", "c#", "go", "golang", "rust", "kotlin", "swift",
    "html", "css", "sass", "tailwind", "nextjs", "nuxt",
    "linux", "unix", "bash", "shell", "jenkins", "github actions",
    "kafka", "rabbitmq", "celery", "airflow",
    "agile", "scrum", "jira", "figma",
}


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
    def aggregate_context(
        chunks: List[Tuple[Dict[str, Any], float]],
        top_n_per_candidate: int = 3
    ) -> str:
        """
        Groups chunks by candidate_id and returns a formatted string.
        """
        candidates: Dict[str, Any] = {}

        for meta, score in chunks:
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


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough estimate: words × 1.3."""
    return int(len(text.split()) * 1.3)





def _aggressive_trim(
    history: List[Dict[str, str]],
    llm_provider: Optional[Any] = None,
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """
    Aggressively summarizes history after 4 turns (8 messages).
    Keeps 1st turn and last 2 turns, summarizes the rest.
    """
    num_messages = len(history)
    # Turn = 2 messages. 4 turns = 8 messages.
    if num_messages <= 8:
        tokens = sum(_estimate_tokens(m["content"]) for m in history)
        return history, {"total": num_messages // 2, "summarized": 0, "tokens": tokens}

    # Extract components
    first_turn = history[:2]
    last_two_turns = history[-4:]
    middle_turns = history[2:-4]
    
    middle_text = " ".join([m["content"] for m in middle_turns]).lower()
    
    # Check for complex turns needing LLM fallback
    needs_llm = any(
        word in middle_text 
        for word in ["compare", "explain", "why", "versus", "vs", "difference"]
    )
    
    summary_text = ""
    if needs_llm and llm_provider:
        try:
            prompt = (
                "Summarize the following candidate search conversation history concisely, "
                "focusing on the core technical requirements and filters discussed:\n\n"
                f"{middle_text}\n\n"
                "Summary (1 sentence):"
            )
            raw = llm_provider.generate_response(prompt, "You are a concise summarizer.")
            # Basic cleanup if JSON returned
            if raw.strip().startswith("{"):
                try:
                    summary_text = json.loads(raw).get("summary", raw)
                except:
                    summary_text = raw[:100]
            else:
                summary_text = raw.strip()
        except:
            needs_llm = False # Fallback to local on error
            
    if not needs_llm or not summary_text:
        # Local regex-based summarization
        topic = "general recruitment"
        for skill in _COMMON_SKILLS:
            if skill.lower() in middle_text:
                topic = skill
                break
        
        filters = "none"
        exp_match = re.search(r'(\d+)\s*\+?\s*years?', middle_text)
        if exp_match:
            filters = f"{exp_match.group(1)}+ years"
        
        summary_text = f"candidate search for {topic}, filters applied: {filters}"

    summary_msg = {
        "role": "system", 
        "content": f"[Summary: {summary_text}]"
    }
    
    new_history = first_turn + [summary_msg] + last_two_turns
    
    stats = {
        "total": num_messages // 2,
        "summarized": (num_messages - 6) // 2,
        "tokens": sum(_estimate_tokens(m["content"]) for m in new_history)
    }
    
    return new_history, stats


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
            self.provider = GeminiProvider()

        # In-memory caches
        self._query_cache: Dict[str, Any] = {}           # Keyed by query+context hash
        self._rewrite_cache: Dict[str, str] = {}         # Per-session: query -> rewritten
        
        # Responses cache (FIFO, max 256)
        self._cache = OrderedDict()
        self._hits = 0
        self._misses = 0

        # Memory stats tracking
        self._total_turns_processed = 0
        self._summarized_turns_count = 0
        self._last_tokens_estimate = 0

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cache_key(self, query: str, context_hash: str) -> str:
        return hashlib.md5(f"{query}:{context_hash}".encode()).hexdigest()

    def _get_rewrite_key(self, session_id: str, query: str) -> str:
        return hashlib.md5(f"{session_id}:{query}".encode()).hexdigest()

    def _get_cache_key(self, prompt: str) -> str:
        """Helper to create a hash key for a prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _is_simple_filter(self, message: str) -> bool:
        """Determines if a message is a simple filter that doesn't need LLM."""
        message_lower = message.lower()
        keywords = ["only", "exclude", "without", "remove", "add", "more than", 
                    "less than", "at least", "under", "over", "show me", "filter"]
        negative_keywords = ["why", "how", "what", "explain", "compare"]
        
        has_keyword = any(k in message_lower for k in keywords)
        is_short = len(message.split()) < 12
        no_questions = not any(q in message_lower for q in negative_keywords)
        
        return (has_keyword or is_short) and no_questions

    def _rule_based_rewrite(self, message: str, history: List[Dict]) -> str:
        """Appends a simple filter to the last standalone query."""
        base_query = ""
        # Find the last user message that wasn't a simple filter
        for msg in reversed(history):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if not self._is_simple_filter(content):
                    base_query = content
                    break
        
        if not base_query:
            # Fallback to the first user message if no standalone found
            for msg in history:
                if msg.get("role") == "user":
                    base_query = msg.get("content", "")
                    break
        
        if not base_query:
            return message

        msg_clean = message.strip()
        msg_lower = msg_clean.lower()
        
        # Natural language transformation for common patterns
        if msg_lower.startswith("exclude "):
            return f"{base_query} excluding {msg_clean[8:].strip()}"
        if msg_lower.startswith("without "):
            return f"{base_query} without {msg_clean[8:].strip()}"
        if msg_lower.startswith("only "):
            return f"{base_query} only {msg_clean[5:].strip()}"
            
        return f"{base_query} {msg_clean}"

    def cache_stats(self) -> Dict[str, int]:
        """Returns cache efficiency statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache)
        }

    def memory_stats(self) -> Dict[str, int]:
        """Returns aggregate memory usage stats."""
        return {
            "total_turns": self._total_turns_processed,
            "summarized_turns": self._summarized_turns_count,
            "current_tokens_estimate": self._last_tokens_estimate
        }

    # ------------------------------------------------------------------
    # Intent extraction
    # ------------------------------------------------------------------

    def extract_intent(self, query: str) -> Dict[str, Any]:
        """
        Hybrid Intent Extraction: Rule-based for filters.
        Extracts both experience requirements and explicitly mentioned skills.
        """
        filters: Dict[str, Any] = {"skills": [], "min_experience": None}
        query_lower = query.lower()

        # Rule 1: Experience (e.g., "5+ years", "at least 3 years")
        exp_match = re.search(
            r'(?:at\s+least\s+)?(\d+)\s*\+?\s*years?',
            query_lower
        )
        if exp_match:
            filters["min_experience"] = float(exp_match.group(1))

        # Rule 2: Skill detection from known keyword set
        detected_skills = []
        for skill in _COMMON_SKILLS:
            # Use word-boundary-aware matching for multi-word and single-word skills
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, query_lower):
                detected_skills.append(skill)

        if detected_skills:
            filters["skills"] = detected_skills

        return filters

    # ------------------------------------------------------------------
    # Context drift detection
    # ------------------------------------------------------------------

    def detect_context_drift(
        self,
        new_skills: List[str],
        previous_skills: List[str],
    ) -> str:
        """
        Determines whether the query represents a context drift.

        Returns:
          - "reset"  : Clearly new topic (no meaningful overlap)
          - "merge"  : Partial overlap — keep existing context and merge
          - "same"   : Same or very similar topic — no change needed
        """
        if not new_skills or not previous_skills:
            # No new skills detected or no prior context — nothing to drift from
            return "same"

        new_set = set(s.lower() for s in new_skills)
        prev_set = set(s.lower() for s in previous_skills)

        overlap = new_set & prev_set
        overlap_ratio = len(overlap) / max(len(new_set), len(prev_set))

        if overlap_ratio >= 0.5:
            return "same"      # Majority overlap — stay in context
        elif overlap_ratio > 0:
            return "merge"     # Partial overlap — blend contexts
        else:
            # Zero overlap: only reset if new_skills contains a clearly dominant
            # different topic (more than 1 new skill signals intentional pivot)
            if len(new_set - prev_set) >= 2:
                return "reset"
            return "merge"     # Single new skill might just be additive

    # ------------------------------------------------------------------
    # Query rewriting
    # ------------------------------------------------------------------

    def rewrite_query(
        self,
        query: str,
        history: List[Dict],
        last_filters: Dict,
        session_id: str = "",
    ) -> str:
        """
        Rewrites a follow-up query into a standalone version using
        conversation history and active filters.
        Uses session-scoped cache to avoid redundant LLM calls.
        """
        # Cache check (session + original query)
        cache_key = self._get_rewrite_key(session_id, query)
        if cache_key in self._rewrite_cache:
            logger.debug(f"Rewrite cache hit for query: {query[:50]}")
            return self._rewrite_cache[cache_key]

        if not history:
            return query

        # Heuristic: is this a follow-up?
        is_follow_up = (
            len(query.split()) < 6
            or any(
                word in query.lower()
                for word in ["those", "them", "they", "only", "about", "her",
                             "him", "these", "that", "this", "also", "instead",
                             "exclude", "without", "more", "better"]
            )
        )

        if not is_follow_up:
            self._rewrite_cache[cache_key] = query
            return query

        # Rule-based optimization for simple filters
        if self._is_simple_filter(query):
            rewritten = self._rule_based_rewrite(query, history)
            print("[RULE REWRITE]")
            self._rewrite_cache[cache_key] = rewritten
            return rewritten

        # Aggressive trimming and summarization
        trimmed, stats = _aggressive_trim(history, self.provider)
        self._total_turns_processed += stats["total"]
        self._summarized_turns_count += stats["summarized"]
        self._last_tokens_estimate = stats["tokens"]
        
        history_context = "\n".join(
            [f"{m['role'].upper()}: {m['content']}" for m in trimmed]
        )

        # Build filter context string for injection
        filter_parts = []
        if last_filters.get("skills"):
            filter_parts.append(f"Skills required: {', '.join(last_filters['skills'])}")
        if last_filters.get("min_experience"):
            filter_parts.append(f"Minimum experience: {last_filters['min_experience']} years")
        filter_str = "; ".join(filter_parts) if filter_parts else "None"

        system_instruction = (
            "You are a query optimization assistant for a recruitment RAG system. "
            "Rewrite follow-up queries into complete, standalone search queries "
            "that incorporate relevant context from conversation history AND active filters."
        )

        prompt = (
            f"CONVERSATION HISTORY:\n{history_context}\n\n"
            f"ACTIVE FILTERS: {filter_str}\n\n"
            f"FOLLOW-UP QUERY: {query}\n\n"
            "Rewrite this follow-up into a single, descriptive standalone search query "
            "that respects the active filters above. "
            "The rewritten query must NOT contradict the active filters.\n"
            "Example: filters=React, 5+ years; query='only senior ones' "
            "→ 'Senior React developers with 5+ years of experience'\n"
            'FORMAT: {"rewritten_query": "..."}'
        )

        try:
            # 1. Check response cache
            cache_key = self._get_cache_key(prompt)
            if cache_key in self._cache:
                print("[CACHE HIT]")
                self._hits += 1
                # Move to end to maintain FIFO/LRU-like but the user said FIFO
                # OrderedDict normally inserts at end and deletes from start (popitem(last=False))
                # If we just want FIFO, we don't re-insert. If we want LRU, we re-insert.
                # User said "evict the oldest entry (FIFO using collections.OrderedDict)".
                # Standard FIFO in OrderedDict is achieved by always adding new entries at the end
                # and popping from the front. We won't re-order on hits to preserve FIFO.
                raw = self._cache[cache_key]
            else:
                print("[CACHE MISS]")
                print("[LLM REWRITE]")
                self._misses += 1
                raw = self.provider.generate_response(prompt, system_instruction)
                
                # 2. Update cache with FIFO eviction
                if len(self._cache) >= 256:
                    self._cache.popitem(last=False)  # Remove oldest
                self._cache[cache_key] = raw

            parsed = self._robust_json_parse(raw)
            rewritten = parsed.get("rewritten_query", query)
        except Exception:
            rewritten = query

        self._rewrite_cache[cache_key] = rewritten
        return rewritten

    # ------------------------------------------------------------------
    # Main query generation
    # ------------------------------------------------------------------

    def query(
        self,
        query: str,
        retrieved_chunks: List[Any],
        matcher_results: Optional[Dict] = None,
        history: List[Dict] = None,
        last_filters: Dict = None,
        last_candidates: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured answer based on retrieved context and
        conversation history.
        """
        history = history or []
        last_filters = last_filters or {}
        last_candidates = last_candidates or []

        # 1. Prepare Context
        context_str = ContextAggregator.aggregate_context(retrieved_chunks)

        # Matcher context
        matcher_context = ""
        if matcher_results and "candidates" in matcher_results:
            matcher_context = "\n### Pre-calculated Matcher Scores:\n"
            for cand in matcher_results["candidates"]:
                matcher_context += (
                    f"- {cand['name']} (ID: {cand['candidate_id']}): "
                    f"Score {cand['score']}, "
                    f"Matched: {cand['matched_skills']}, "
                    f"Missing: {cand['missing_skills']}\n"
                )

        # Aggressive trimming and summarization
        trimmed_history, stats = _aggressive_trim(history, self.provider)
        self._total_turns_processed += stats["total"]
        self._summarized_turns_count += stats["summarized"]
        self._last_tokens_estimate = stats["tokens"]
        
        history_context = ""
        if trimmed_history:
            history_context = "\n### Recent Conversation History:\n"
            for msg in trimmed_history:
                history_context += f"- {msg['role'].upper()}: {msg['content']}\n"

        # Structured memory context
        structured_context = ""
        if last_filters or last_candidates:
            structured_context = "\n### Active Memory & Filter Context:\n"
            if last_filters:
                structured_context += f"Current Filters: {json.dumps(last_filters)}\n"
            if last_candidates:
                cand_lines = [
                    f"  - {c['name']} (ID: {c.get('candidate_id', 'N/A')}, "
                    f"Score: {c.get('score', 'N/A')}, "
                    f"Skills: {', '.join(c.get('matched_skills', []))})"
                    for c in last_candidates
                ]
                structured_context += (
                    "Previously Discussed Candidates:\n"
                    + "\n".join(cand_lines) + "\n"
                )

        full_context = (
            f"{structured_context}\n{history_context}\n"
            f"{context_str}\n{matcher_context}"
        )

        # 2. Cache check
        context_hash = hashlib.md5(full_context.encode()).hexdigest()
        cache_key = self._get_cache_key(query, context_hash)
        if cache_key in self._query_cache:
            logger.info("Serving query response from cache")
            return self._query_cache[cache_key]

        # 3. Detect query type
        is_comparison = any(
            word in query.lower()
            for word in ["compare", "difference", "versus", "vs", "between", "better"]
        )
        comparison_instruction = ""
        if is_comparison:
            comparison_instruction = (
                "\n6. This is a COMPARISON query. Use the 'Previously Discussed Candidates' "
                "and 'Matcher Scores' to provide a detailed comparison. "
                "Highlight trade-offs in skills and experience."
            )

        # 4. Construct prompt
        system_instruction = (
            "You are an expert AI Technical Recruiter. Analyze candidate resumes "
            "provided in the context and answer queries factually and concisely. "
            "Leverage conversation history for follow-up answers.\n\n"
            "STRICT CONSTRAINTS:\n"
            "1. ONLY use the provided context. Do NOT use outside knowledge.\n"
            "2. Do NOT hallucinate candidates. If a name is not in context, say so.\n"
            "3. DO NOT repeat previous answers unnecessarily.\n"
            "4. If context changed mid-conversation (new filters), acknowledge it.\n"
            "5. Interpret follow-up queries correctly using conversation history.\n"
            f"6. For each candidate mentioned, include candidate_id, score, "
            f"reasoning, and matched_skills.{comparison_instruction}"
        )

        prompt = (
            f"USER QUERY: {query}\n\n"
            f"CANDIDATE AND CONVERSATION CONTEXT:\n{full_context}\n\n"
            "RESPONSE FORMAT (JSON):\n"
            "{\n"
            '  "answer": "Detailed summary answering the user query in context",\n'
            '  "top_candidates": [\n'
            "    {\n"
            '      "candidate_id": "id",\n'
            '      "name": "name",\n'
            '      "score": 0.95,\n'
            '      "matched_skills": ["skill1", "skill2"],\n'
            '      "reasoning": "Context-aware reasoning why this candidate fits"\n'
            "    }\n"
            "  ],\n"
            '  "insights": "Specific recruiter-level insights or empty string",\n'
            '  "confidence": "high|medium|low",\n'
            '  "detected_filters": {"skills": [], "min_experience": 0}\n'
            "}"
        )

        # 5. Call LLM
        # Response cache check
        cache_key = self._get_cache_key(prompt)
        if cache_key in self._cache:
            print("[CACHE HIT]")
            self._hits += 1
            raw_response = self._cache[cache_key]
        else:
            print("[CACHE MISS]")
            print("[LLM REWRITE]")
            self._misses += 1
            raw_response = self.provider.generate_response(prompt, system_instruction)
            
            # Update cache (FIFO)
            if len(self._cache) >= 256:
                self._cache.popitem(last=False)
            self._cache[cache_key] = raw_response

        # 6. Parse and format
        try:
            parsed = self._robust_json_parse(raw_response)

            if not parsed.get("top_candidates") and "no" in parsed.get("answer", "").lower():
                parsed["answer"] = (
                    "No strong matches found based on the provided query "
                    "and candidate database."
                )

            self._query_cache[cache_key] = parsed
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {
                "answer": "Error processing the query. The AI response was malformed.",
                "top_candidates": [],
                "insights": str(e),
                "confidence": "low",
            }

    # ------------------------------------------------------------------
    # JSON parsing helper
    # ------------------------------------------------------------------

    def _robust_json_parse(self, text: str) -> Dict[str, Any]:
        """Attempts to extract and parse JSON from LLM output."""
        clean_text = text.strip()
        # Strip markdown code fences
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        return json.loads(clean_text.strip())
