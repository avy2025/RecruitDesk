import time
import uuid
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: words × 1.3."""
    return int(len(text.split()) * 1.3)


class ConversationMemory:
    """
    In-memory storage for chat sessions with structured context.
    Supports TTL, session capping, token-aware history trimming,
    hard message-count cap, and summarization safety.
    """

    def __init__(
        self,
        max_sessions: int = 100,
        ttl_seconds: int = 3600,
        max_messages: int = 15,
        max_history_tokens: int = 2000,
    ):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self.max_history_tokens = max_history_tokens
        self.last_cleanup = time.time()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def get_session(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Retrieve session data and update TTL. Creates new session if missing."""
        if session_id and session_id in self.sessions:
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
            "created_at": time.time(),
        }
        logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Manually clear a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id}")

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the history and enforce hard cap."""
        session = self.get_session(session_id)
        session["history"].append({"role": role, "content": content})

        # Enforce hard message-count cap (keeps most recent messages)
        regular_msgs = [m for m in session["history"] if m.get("role") != "system"]
        system_msgs = [m for m in session["history"] if m.get("role") == "system"]

        if len(regular_msgs) > self.max_messages:
            regular_msgs = regular_msgs[-self.max_messages:]
            session["history"] = system_msgs + regular_msgs
            logger.debug(
                f"Session {session_id}: trimmed to {self.max_messages} messages."
            )

    def get_recent_history(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
        hard_cap: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Return a token-aware, capped slice of conversation history.

        Args:
            session_id: The session to retrieve history for.
            max_tokens: Override for max token budget (default: self.max_history_tokens).
            hard_cap: Override for message hard cap (default: self.max_messages).

        Returns:
            List of history messages that fit within the token budget.
            System / summary messages are always included first.
        """
        session = self.get_session(session_id)
        history = session["history"]
        budget = max_tokens or self.max_history_tokens
        cap = hard_cap or self.max_messages

        # Separate system/summary messages (always keep)
        system_msgs = [m for m in history if m.get("role") == "system"]
        regular_msgs = [m for m in history if m.get("role") != "system"]

        # Apply hard cap first
        if len(regular_msgs) > cap:
            regular_msgs = regular_msgs[-cap:]

        # Apply token budget (newest first, fill backwards)
        used = sum(_estimate_tokens(m.get("content", "")) for m in system_msgs)
        trimmed: List[Dict[str, str]] = []
        for msg in reversed(regular_msgs):
            tokens = _estimate_tokens(msg.get("content", ""))
            if used + tokens > budget:
                break
            trimmed.insert(0, msg)
            used += tokens

        return system_msgs + trimmed

    # ------------------------------------------------------------------
    # Structured context management
    # ------------------------------------------------------------------

    def update_context(
        self,
        session_id: str,
        filters: Optional[Dict] = None,
        candidates: Optional[List] = None,
    ) -> None:
        """Update structured memory (filters + top candidates)."""
        session = self.get_session(session_id)

        if filters:
            # Merge skills lists (union), take max experience
            existing = session["last_filters"]
            if "skills" in filters and filters["skills"]:
                merged_skills = list(
                    set(existing.get("skills", [])) | set(filters["skills"])
                )
                existing["skills"] = merged_skills
            if "min_experience" in filters and filters["min_experience"]:
                existing["min_experience"] = max(
                    existing.get("min_experience", 0.0),
                    filters["min_experience"],
                )
            existing.update(
                {k: v for k, v in filters.items() if k not in ("skills", "min_experience")}
            )

        if candidates is not None:
            # Store structured candidate data (id, name, score, matched_skills)
            session["last_candidates"] = [
                {
                    "candidate_id": c.get("candidate_id"),
                    "name": c.get("name"),
                    "score": c.get("score"),
                    "matched_skills": c.get("matched_skills", []),
                    "reasoning": c.get("reasoning", ""),
                }
                for c in candidates
            ][:5]  # Limit to top 5 for memory efficiency

    def reset_filters(self, session_id: str) -> None:
        """Reset only the skill filters (experience remains sticky)."""
        session = self.get_session(session_id)
        session["last_filters"]["skills"] = []
        logger.info(f"Session {session_id}: skill filters reset due to context drift.")

    def full_reset_filters(self, session_id: str) -> None:
        """Reset all filters (full context pivot)."""
        session = self.get_session(session_id)
        session["last_filters"] = {"skills": [], "min_experience": 0.0}
        session["last_candidates"] = []
        logger.info(f"Session {session_id}: full context reset due to major drift.")

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    def summarize_history(self, session_id: str, summary: str) -> None:
        """
        Replace older messages with an LLM-generated summary,
        preserving structured memory entirely.
        Recent messages (last 3) are kept for immediate continuity.
        """
        session = self.get_session(session_id)
        last_few = session["history"][-3:] if len(session["history"]) > 3 else []
        session["history"] = [
            {"role": "system", "content": f"Summary of previous conversation: {summary}"}
        ] + last_few

    # ------------------------------------------------------------------
    # TTL cleanup
    # ------------------------------------------------------------------

    def cleanup_expired(self) -> None:
        """Remove sessions past TTL."""
        now = time.time()
        expired_ids = [
            sid
            for sid, data in self.sessions.items()
            if now - data["last_accessed"] > self.ttl_seconds
        ]
        for sid in expired_ids:
            del self.sessions[sid]
        self.last_cleanup = now
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions.")

    def _cleanup_oldest(self) -> None:
        """Remove the least recently used session."""
        if not self.sessions:
            return
        oldest_sid = min(
            self.sessions, key=lambda sid: self.sessions[sid]["last_accessed"]
        )
        del self.sessions[oldest_sid]
        logger.info(f"Session cap reached. Removed oldest session: {oldest_sid}")
