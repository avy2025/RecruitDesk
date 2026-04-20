import pytest
import json
from unittest.mock import MagicMock, patch
from rag.llm_service import LLMService, GeminiProvider, ContextAggregator

@pytest.fixture
def mock_retrieved_chunks():
    return [
        (
            {
                "text": "Expert in React and Node.js with 5 years experience.",
                "metadata": {
                    "candidate_id": "cand_001",
                    "name": "Alice Developer",
                    "experience": 5.0,
                    "skills": ["React", "Node.js"]
                }
            }, 
            0.95
        ),
        (
            {
                "text": "Alice also has experience with AWS and Docker.",
                "metadata": {
                    "candidate_id": "cand_001",
                    "name": "Alice Developer",
                    "experience": 5.0,
                    "skills": ["AWS", "Docker"]
                }
            }, 
            0.85
        )
    ]

@pytest.fixture
def mock_matcher_results():
    return {
        "success": True,
        "candidates": [
            {
                "candidate_id": "cand_001",
                "name": "Alice Developer",
                "score": 0.92,
                "matched_skills": ["React", "Node.js"],
                "missing_skills": ["Python"]
            }
        ]
    }

def test_context_aggregation(mock_retrieved_chunks):
    """Test that chunks are correctly grouped by candidate."""
    context = ContextAggregator.aggregate_context(mock_retrieved_chunks)
    
    assert "Alice Developer" in context
    assert "ID: cand_001" in context
    assert "Expert in React" in context
    assert "AWS and Docker" in context
    # Should only have one candidate heading despite two chunks
    assert context.count("### Candidate:") == 1

@patch("rag.llm_service.GeminiProvider.generate_response")
def test_llm_query_schema_validation(mock_gen, mock_retrieved_chunks, mock_matcher_results):
    """Test that LLMService correctly parses a valid JSON response."""
    mock_response = {
        "answer": "Alice is a strong match for the React role.",
        "top_candidates": [
            {
                "candidate_id": "cand_001",
                "name": "Alice Developer",
                "score": 0.95,
                "reasoning": "Strong React skills and 5 years of experience."
            }
        ],
        "insights": "The candidate pool is small but high quality.",
        "confidence": "high"
    }
    mock_gen.return_value = json.dumps(mock_response)
    
    service = LLMService(provider_type="gemini")
    result = service.query("Who is best for React?", mock_retrieved_chunks, mock_matcher_results)
    
    assert result["answer"] == mock_response["answer"]
    assert len(result["top_candidates"]) == 1
    assert result["top_candidates"][0]["candidate_id"] == "cand_001"

@patch("rag.llm_service.GeminiProvider.generate_response")
def test_hallucination_prevention_logic(mock_gen, mock_retrieved_chunks):
    """Test 'no match' scenario handling."""
    mock_response = {
        "answer": "No matches found for Python developer.",
        "top_candidates": [],
        "insights": "insufficient data",
        "confidence": "low"
    }
    mock_gen.return_value = json.dumps(mock_response)
    
    service = LLMService(provider_type="gemini")
    # Query for something not in context
    result = service.query("Find me a Python developer", mock_retrieved_chunks)
    
    assert "No strong matches found" in result["answer"]
    assert result["top_candidates"] == []

def test_robust_json_parse():
    """Test that the service can handle markdown-wrapped JSON."""
    service = LLMService(provider_type="gemini")
    markdown_json = "```json\n{\"test\": \"data\"}\n```"
    parsed = service._robust_json_parse(markdown_json)
    assert parsed["test"] == "data"
    
    raw_json = "{\"test\": \"data\"}"
    parsed = service._robust_json_parse(raw_json)
    assert parsed["test"] == "data"
