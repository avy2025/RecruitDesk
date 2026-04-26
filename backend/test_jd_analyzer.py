import unittest
import sys
import os

# Ensure the parent directory is in sys.path if needed
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from jd_analyzer import JDAnalyzer

class TestJDAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We can pass nlp=None to JDAnalyzer to let it load itself
        cls.analyzer = JDAnalyzer()

    def test_must_have_extraction(self):
        jd_text = "The candidate must have experience with Python and FastAPI. It is required to know SQL."
        analysis = self.analyzer.analyze(jd_text)
        # Convert to lower for robustness in check if needed, but analyze already lowercases
        self.assertIn("python", [s.lower() for s in analysis.must_have_skills])
        self.assertIn("fastapi", [s.lower() for s in analysis.must_have_skills])
        self.assertIn("sql", [s.lower() for s in analysis.must_have_skills])

    def test_nice_to_have_extraction(self):
        jd_text = "Familiarity with Docker is a plus. Preferred experience with AWS."
        analysis = self.analyzer.analyze(jd_text)
        self.assertIn("docker", [s.lower() for s in analysis.nice_to_have_skills])
        self.assertIn("aws", [s.lower() for s in analysis.nice_to_have_skills])

    def test_experience_regex_plus(self):
        jd_text = "Requirement: 3+ years of experience."
        analysis = self.analyzer.analyze(jd_text)
        self.assertEqual(analysis.experience_requirement["min_years"], 3)
        self.assertIsNone(analysis.experience_requirement["max_years"])

    def test_experience_regex_range(self):
        jd_text = "Looking for 2-5 years of experience."
        analysis = self.analyzer.analyze(jd_text)
        self.assertEqual(analysis.experience_requirement["min_years"], 2)
        self.assertEqual(analysis.experience_requirement["max_years"], 5)

    def test_seniority_detection(self):
        analysis = self.analyzer.analyze("Senior Software Engineer")
        self.assertEqual(analysis.seniority_level, "senior")
        
        analysis = self.analyzer.analyze("Lead Architect")
        self.assertEqual(analysis.seniority_level, "lead")

    def test_red_flag_detection(self):
        jd_text = "We need a rockstar developer who can hustle."
        analysis = self.analyzer.analyze(jd_text)
        self.assertIn("rockstar", analysis.red_flags)
        self.assertIn("hustle", analysis.red_flags)

if __name__ == "__main__":
    unittest.main()
