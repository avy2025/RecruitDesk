"""
Phase 5 Test Suite for ConversationMemory and LLMService.
Tests: session lifecycle, structured memory, intent extraction, query rewriting,
multi-turn conversation, filter refinement, context drift, comparison queries,
token-aware trimming, and empty retrieval handling.
"""

import time
import pytest
from rag.memory import ConversationMemory
from rag.llm_service import LLMService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory():
    return ConversationMemory(max_sessions=5, ttl_seconds=2, max_messages=15)


@pytest.fixture
def llm():
    svc = LLMService()
    # Inject mock provider so no real API calls are made
    class MockProvider:
        def generate_response(self, prompt, system_instruction=""):
            # Return a sensible JSON for any prompt type
            if "rewritten_query" in prompt or "FOLLOW-UP QUERY" in prompt:
                return '{"rewritten_query": "Senior Java Developer with 5+ years"}'
            return (
                '{"answer": "Mock answer", "top_candidates": [], '
                '"insights": "", "confidence": "high", "detected_filters": {}}'
            )
    svc.provider = MockProvider()
    return svc


# ---------------------------------------------------------------------------
# 1. Session lifecycle (existing — kept and extended)
# ---------------------------------------------------------------------------

def test_session_lifecycle():
    """Session cap evicts oldest; TTL cleanup removes expired sessions."""
    memory = ConversationMemory(max_sessions=2, ttl_seconds=1)

    memory.get_session("session_1")
    memory.get_session("session_2")
    assert len(memory.sessions) == 2

    # Third session should evict the oldest (session_1)
    memory.get_session("session_3")
    assert len(memory.sessions) == 2
    assert "session_1" not in memory.sessions

    # Wait for TTL expiry
    time.sleep(1.2)
    memory.cleanup_expired()
    assert len(memory.sessions) == 0


# ---------------------------------------------------------------------------
# 2. Structured memory (existing — kept)
# ---------------------------------------------------------------------------

def test_structured_memory(memory):
    """Filters and candidates are stored and retrievable."""
    sid = "test_memory"

    memory.add_message(sid, "user", "Find Python developers")
    memory.add_message(sid, "ai", "Here are the top Python developers...")

    memory.update_context(
        sid,
        filters={"skills": ["Python"], "min_experience": 3.0},
        candidates=[{
            "candidate_id": "c1",
            "name": "Alice",
            "score": 0.9,
            "matched_skills": ["Python", "Django"],
        }]
    )

    session = memory.get_session(sid)
    assert len(session["history"]) == 2
    assert "Python" in session["last_filters"]["skills"]
    assert session["last_filters"]["min_experience"] == 3.0
    assert len(session["last_candidates"]) == 1
    assert session["last_candidates"][0]["name"] == "Alice"
    # Structured candidate data must include matched_skills
    assert "matched_skills" in session["last_candidates"][0]


# ---------------------------------------------------------------------------
# 3. Intent extraction (existing — extended)
# ---------------------------------------------------------------------------

def test_hybrid_intent_extraction(llm):
    """Rule-based: extracts experience years and skill keywords."""
    f1 = llm.extract_intent("Find someone with 5+ years experience")
    assert f1["min_experience"] == 5.0

    f2 = llm.extract_intent("only 3 years is fine")
    assert f2["min_experience"] == 3.0

    f3 = llm.extract_intent("Looking for Java experts")
    assert f3["min_experience"] is None
    assert "java" in f3["skills"]

    f4 = llm.extract_intent("Show me React and Python developers with 4 years")
    assert f4["min_experience"] == 4.0
    assert "react" in f4["skills"]
    assert "python" in f4["skills"]

    f5 = llm.extract_intent("General question about the team")
    assert f5["min_experience"] is None
    assert f5["skills"] == []


# ---------------------------------------------------------------------------
# 4. Query rewrite mock (existing — extended with session_id cache)
# ---------------------------------------------------------------------------

def test_query_rewrite_mock(llm):
    """Short follow-ups are rewritten; standalone queries pass through unchanged.
    Rewrite cache prevents duplicate LLM calls within a session."""
    history = [
        {"role": "user", "content": "Find Java devs"},
        {"role": "ai",   "content": "Found 3 Java devs"},
    ]
    filters = {"skills": ["java"]}

    # Short follow-up → should be rewritten (< 6 words)
    rewritten = llm.rewrite_query("only senior ones", history, filters, session_id="s1")
    assert rewritten == "Senior Java Developer with 5+ years"

    # Same call again → should hit cache, not re-call provider
    call_count = [0]
    original = llm.provider.generate_response
    def counting_gen(prompt, system_instruction=""):
        call_count[0] += 1
        return original(prompt, system_instruction)
    llm.provider.generate_response = counting_gen

    rewritten_again = llm.rewrite_query("only senior ones", history, filters, session_id="s1")
    assert rewritten_again == "Senior Java Developer with 5+ years"
    assert call_count[0] == 0  # Cache hit — no extra LLM call

    # Restore provider before next assertion
    llm.provider.generate_response = original

    # Fully standalone, long query with no follow-up trigger words → pass through unchanged
    # Uses a separate session so cache does not interfere
    standalone = (
        "Find candidates who have strong experience in machine learning and data engineering"
    )
    not_rewritten = llm.rewrite_query(standalone, history, filters, session_id="s2_standalone")
    assert not_rewritten == standalone


# ---------------------------------------------------------------------------
# 5. Multi-turn conversation (NEW)
# ---------------------------------------------------------------------------

def test_multi_turn_conversation(memory):
    """History grows correctly across turns and respects hard cap."""
    sid = "multi_turn"

    turns = [
        ("user", "Find Python developers"),
        ("ai",   "Found 5 Python developers."),
        ("user", "Only those with 5+ years"),
        ("ai",   "Narrowed to 2 candidates."),
        ("user", "Compare them"),
        ("ai",   "Alice has more experience; Bob has broader skills."),
    ]

    for role, content in turns:
        memory.add_message(sid, role, content)

    session = memory.get_session(sid)
    assert len(session["history"]) == 6

    # All roles and content must be preserved
    assert session["history"][0]["role"] == "user"
    assert session["history"][0]["content"] == "Find Python developers"
    assert session["history"][-1]["role"] == "ai"


def test_hard_message_cap(memory):
    """Hard cap of 15 messages is enforced; oldest are dropped."""
    memory_capped = ConversationMemory(max_sessions=5, ttl_seconds=3600, max_messages=5)
    sid = "cap_test"

    for i in range(8):
        memory_capped.add_message(sid, "user", f"Message {i}")

    session = memory_capped.get_session(sid)
    # Should never exceed 5 after trimming
    assert len(session["history"]) <= 5
    # Most recent message must be retained
    assert session["history"][-1]["content"] == "Message 7"


# ---------------------------------------------------------------------------
# 6. Filter refinement across turns (NEW)
# ---------------------------------------------------------------------------

def test_filter_refinement(memory):
    """Filters accumulate correctly across Q1 → Q2 → Q3 turns."""
    sid = "filter_refine"

    # Q1: Find Python developers
    memory.update_context(sid, filters={"skills": ["python"]})
    # Q2: Only 5+ years
    memory.update_context(sid, filters={"min_experience": 5.0})
    # Q3: Exclude Django — adds a new non-overlapping skill exclusion note
    # (In a real pipeline this would be via query rewrite; here we test accumulation)
    memory.update_context(sid, filters={"skills": ["python", "django"]})

    session = memory.get_session(sid)
    # Skills union: python + django
    assert "python" in session["last_filters"]["skills"]
    assert "django" in session["last_filters"]["skills"]
    # Experience should be max of all updates
    assert session["last_filters"]["min_experience"] == 5.0


# ---------------------------------------------------------------------------
# 7. Context drift: merge vs reset (NEW)
# ---------------------------------------------------------------------------

def test_context_drift_merge_vs_reset(llm):
    """
    Zero overlap with ≥2 new skills → reset.
    Single new skill → merge.
    Partial overlap → merge.
    No new skills → same.
    """
    # Case 1: Full reset — entirely new topic (2+ new skills, no overlap)
    action = llm.detect_context_drift(
        new_skills=["java", "spring"],
        previous_skills=["python", "django"]
    )
    assert action == "reset"

    # Case 2: Merge — single new skill (could be additive)
    action = llm.detect_context_drift(
        new_skills=["docker"],
        previous_skills=["python", "django"]
    )
    assert action == "merge"

    # Case 3: Merge — partial overlap
    action = llm.detect_context_drift(
        new_skills=["python", "react"],
        previous_skills=["python", "django"]
    )
    assert action in ("same", "merge")  # python overlaps

    # Case 4: Same — identical skills
    action = llm.detect_context_drift(
        new_skills=["python"],
        previous_skills=["python", "django"]
    )
    assert action == "same"

    # Case 5: Same — no new skills detected
    action = llm.detect_context_drift(
        new_skills=[],
        previous_skills=["python", "django"]
    )
    assert action == "same"


def test_full_reset_clears_candidates(memory):
    """full_reset_filters clears both skills and candidates."""
    sid = "drift_reset"
    memory.update_context(
        sid,
        filters={"skills": ["react"], "min_experience": 3.0},
        candidates=[{"candidate_id": "c1", "name": "Alice", "score": 0.9, "matched_skills": []}]
    )
    memory.full_reset_filters(sid)
    session = memory.get_session(sid)
    assert session["last_filters"]["skills"] == []
    assert session["last_candidates"] == []


def test_skill_only_reset_keeps_experience(memory):
    """reset_filters() preserves experience while clearing skills."""
    sid = "partial_reset"
    memory.update_context(sid, filters={"skills": ["react"], "min_experience": 4.0})
    memory.reset_filters(sid)
    session = memory.get_session(sid)
    assert session["last_filters"]["skills"] == []
    assert session["last_filters"]["min_experience"] == 4.0


# ---------------------------------------------------------------------------
# 8. Comparison query rewrite (NEW)
# ---------------------------------------------------------------------------

def test_comparison_query_rewrite(llm):
    """
    When user sends "compare them" with candidates in context,
    the rewrite logic detects it as a short follow-up and calls provider.
    """
    history = [
        {"role": "user", "content": "Find React developers"},
        {"role": "ai",   "content": "Top candidates: Alice (React, 6yr), Bob (React, 4yr)"},
    ]
    filters = {"skills": ["react"], "min_experience": 0}

    # "compare them" is short (2 words) → triggers rewrite path
    rewritten = llm.rewrite_query("compare them", history, filters, session_id="compare_s")
    # Mock returns a fixed string; just assert the rewrite happened (not pass-through)
    assert rewritten != "compare them"
    # Should contain context from the mock
    assert len(rewritten) > 5


# ---------------------------------------------------------------------------
# 9. Token-aware history trimming (NEW)
# ---------------------------------------------------------------------------

def test_token_aware_history_trim(memory):
    """get_recent_history() respects both token budget and hard cap."""
    sid = "token_trim"
    # Add 20 large messages (~50 words each → ~65 tokens each)
    for i in range(20):
        content = " ".join([f"word{j}" for j in range(50)])  # ~50 words
        memory.add_message(sid, "user" if i % 2 == 0 else "ai", content)

    # With default max_history_tokens=2000 and hard_cap=15
    trimmed = memory.get_recent_history(sid, max_tokens=500, hard_cap=15)

    # Must not exceed hard cap
    assert len(trimmed) <= 15

    # Estimate total tokens used
    total_tokens = sum(int(len(m["content"].split()) * 1.3) for m in trimmed)
    assert total_tokens <= 500 + 100  # Allow a small overshoot for the last message


# ---------------------------------------------------------------------------
# 10. Empty retrieval scenario (NEW)
# ---------------------------------------------------------------------------

def test_empty_retrieval_scenario(memory):
    """
    When no candidates are found, session history records the empty response
    and active_filters remain intact.
    """
    sid = "empty_retrieval"

    # Pre-populate some context
    memory.update_context(sid, filters={"skills": ["cobol"], "min_experience": 10.0})

    # Simulate what the /rag-query endpoint does on empty retrieval
    memory.add_message(sid, "user", "Find COBOL developers with 10+ years")
    memory.add_message(sid, "ai", "No matching candidates found with the specified filters.")

    session = memory.get_session(sid)

    # History should contain both messages
    assert len(session["history"]) == 2
    assert "No matching" in session["history"][-1]["content"]

    # Filters should remain intact (don't clear on empty result)
    assert "cobol" in session["last_filters"]["skills"]
    assert session["last_filters"]["min_experience"] == 10.0
