import time
import uuid
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    In-memory storage for chat sessions with structured context.
    Supports TTL, session capping, and summarization safety.
    """
    def __init__(self, max_sessions: int = 100, ttl_seconds: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self.last_cleanup = time.time()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve session data and update TTL."""
        if session_id in self.sessions:
            self.sessions[session_id]["last_accessed"] = time.time()
            return self.sessions[session_id]
        return self.create_session(session_id)

    def create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Initialize a new session."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Enforce session cap (remove oldest if full)
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_oldest()

        self.sessions[session_id] = {
            "session_id": session_id,
            "history": [],
            "last_filters": {"skills": [], "min_experience": 0.0},
            "last_candidates": [],
            "last_accessed": time.time(),
            "created_at": time.time()
        }
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the history."""
        session = self.get_session(session_id)
        session["history"].append({"role": role, "content": content})
        
        # Simple limit to trigger summarization check (e.g., 20 messages)
        # Real summarization would be called by the LLM service
        if len(session["history"]) > 20:
             # This is a placeholder for where the actual logic to trigger 
             # LLM summarization would happen if we wanted it fully automated here.
             pass

    def update_context(self, session_id: str, filters: Optional[Dict] = None, candidates: Optional[List] = None):
        """Update structured memory."""
        session = self.get_session(session_id)
        if filters:
            session["last_filters"].update(filters)
        if candidates is not None:
            # We keep enough metadata for follow-up comparison as requested
            session["last_candidates"] = [
                {
                    "candidate_id": c.get("candidate_id"),
                    "name": c.get("name"),
                    "score": c.get("score"),
                    "matched_skills": c.get("matched_skills", [])
                }
                for c in candidates
            ][:5] # Limit to top 5 for memory efficiency

    def clear_session(self, session_id: str):
        """Manually clear a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def cleanup_expired(self):
        """Remove sessions past TTL."""
        now = time.time()
        expired_ids = [
            sid for sid, data in self.sessions.items()
            if now - data["last_accessed"] > self.ttl_seconds
        ]
        for sid in expired_ids:
            del self.sessions[sid]
        self.last_cleanup = now
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions.")

    def _cleanup_oldest(self):
        """Remove the least recently used session."""
        if not self.sessions:
            return
        oldest_sid = min(self.sessions, key=lambda sid: self.sessions[sid]["last_accessed"])
        del self.sessions[oldest_sid]
        logger.info(f"Session cap reached. Removed oldest session: {oldest_sid}")

    def summarize_history(self, session_id: str, summary: str):
        """Replace older messages with a summary, preserving structured memory."""
        session = self.get_session(session_id)
        # Keep the summary + the last 2-3 messages for immediate continuity
        last_few = session["history"][-3:] if len(session["history"]) > 3 else []
        session["history"] = [
            {"role": "system", "content": f"Summary of previous conversation: {summary}"}
        ] + last_few
