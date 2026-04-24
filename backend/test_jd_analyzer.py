import pytest
from jd_analyzer import JDAnalyzer, JDAnalysis

def test_must_have_extraction():
    analyzer = JDAnalyzer()
    jd_text = "Requirements: You must have experience with Python and FastAPI. Essential skills include SQL."
    analysis = analyzer.analyze(jd_text)
    
    assert any("python" in s.lower() for s in analysis.must_have_skills)
    assert any("fastapi" in s.lower() for s in analysis.must_have_skills)
    assert any("sql" in s.lower() for s in analysis.must_have_skills)

def test_nice_to_have_extraction():
    analyzer = JDAnalyzer()
    jd_text = "Preferred skills: Familiarity with AWS and Docker. Bonus points for Kubernetes."
    analysis = analyzer.analyze(jd_text)
    
    assert any("aws" in s.lower() for s in analysis.nice_to_have_skills)
    assert any("docker" in s.lower() for s in analysis.nice_to_have_skills)
    assert any("kubernetes" in s.lower() for s in analysis.nice_to_have_skills)

def test_experience_regex():
    analyzer = JDAnalyzer()
    jd_text1 = "Minimum 3 years of experience required."
    analysis1 = analyzer.analyze(jd_text1)
    assert analysis1.experience_requirement["min_years"] == 3
    
    jd_text2 = "Looking for someone with 2-5 years of industry experience."
    analysis2 = analyzer.analyze(jd_text2)
    assert analysis2.experience_requirement["min_years"] == 2
    assert analysis2.experience_requirement["max_years"] == 5

def test_seniority_detection():
    analyzer = JDAnalyzer()
    assert analyzer.analyze("Senior Software Engineer").seniority_level == "senior"
    assert analyzer.analyze("Junior Developer").seniority_level == "junior"
    assert analyzer.analyze("Lead Architect").seniority_level == "lead"
    assert analyzer.analyze("Principal Engineer").seniority_level == "lead"

def test_red_flag_detection():
    analyzer = JDAnalyzer()
    jd_text = "We are looking for a rockstar ninja who can hustle in a fast-paced environment."
    analysis = analyzer.analyze(jd_text)
    
    assert "rockstar" in analysis.red_flags
    assert "ninja" in analysis.red_flags
    assert "hustle" in analysis.red_flags
    assert "fast-paced" in analysis.red_flags

def test_education_detection():
    analyzer = JDAnalyzer()
    assert analyzer.analyze("Must have a Master's degree in CS").education_requirement == "master"
    assert analyzer.analyze("PhD preferred").education_requirement == "phd"
    assert analyzer.analyze("Bachelor degree required").education_requirement == "bachelor"
