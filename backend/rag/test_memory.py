import pytest
import time
from rag.memory import ConversationMemory
from rag.llm_service import LLMService

def test_session_lifecycle():
    memory = ConversationMemory(max_sessions=2, ttl_seconds=1)
    
    # Create sessions
    s1 = memory.get_session("session_1")
    s2 = memory.get_session("session_2")
    
    assert len(memory.sessions) == 2
    
    # Test Cap Limit
    s3 = memory.get_session("session_3")
    assert len(memory.sessions) == 2
    assert "session_1" not in memory.sessions # Should have evicted oldest
    
    # Test TTL Cleanup
    time.sleep(1.2)
    memory.cleanup_expired()
    assert len(memory.sessions) == 0

def test_structured_memory():
    memory = ConversationMemory()
    sid = "test_memory"
    
    memory.add_message(sid, "user", "Find Python developers")
    memory.add_message(sid, "ai", "Here are the top Python developers...")
    
    memory.update_context(
        sid,
        filters={"skills": ["Python"], "min_experience": 3.0},
        candidates=[{"candidate_id": "c1", "name": "Alice", "score": 0.9}]
    )
    
    session = memory.get_session(sid)
    assert len(session["history"]) == 2
    assert session["last_filters"]["skills"] == ["Python"]
    assert len(session["last_candidates"]) == 1
    assert session["last_candidates"][0]["name"] == "Alice"

def test_hybrid_intent_extraction():
    llm = LLMService(provider_type="dummy") # Ignore actual LLM for intent purely checking regex
    
    # Rule 1: Experience
    filters1 = llm.extract_intent("Find someone with 5+ years experience")
    assert filters1["min_experience"] == 5.0
    
    filters2 = llm.extract_intent("only 3 years is fine")
    assert filters2["min_experience"] == 3.0
    
    filters3 = llm.extract_intent("Looking for Java experts")
    assert filters3["min_experience"] is None

def test_query_rewrite_mock():
    # Since rewrite uses actual LLM, we test the pass-through logic
    llm = LLMService()
    # Mock the LLM provider for isolated testing
    class MockProvider:
        def generate_response(self, p, s):
            return '{"rewritten_query": "Senior Java Developer"}'
    llm.provider = MockProvider()
    
    history = [
        {"role": "user", "content": "Find Java devs"},
        {"role": "ai", "content": "Found 3 Java devs"}
    ]
    filters = {"skills": ["Java"]}
    
    # Short follow-up
    rewritten = llm.rewrite_query("only senior ones", history, filters)
    assert rewritten == "Senior Java Developer"
    
    # New full query should not rewrite aggressively
    # The logic in llm_service uses length < 5
    not_rewritten = llm.rewrite_query("Show me candidates who have experience in React and Node instead", history, filters)
    assert not_rewritten == "Show me candidates who have experience in React and Node instead"
