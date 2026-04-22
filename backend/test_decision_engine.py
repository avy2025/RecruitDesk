import unittest

try:
    from decision_engine import HiringDecisionEngine
except ModuleNotFoundError:
    from backend.decision_engine import HiringDecisionEngine


class Decision:
    HIRE = "Hire"
    CONSIDER = "Consider"
    REJECT = "Reject"


class TestHiringDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = HiringDecisionEngine()
        self.base_jd = (
            "Senior Backend Engineer role. 5+ years experience required. "
            "Python required. SQL required. Cloud architecture preferred."
        )
        self.complete_text = (
            "Experienced backend engineer with strong Python and SQL background. "
            "Built scalable cloud services and APIs. Education: Bachelor of Computer Science."
        )

    def _make_candidate(
        self,
        semantic=80,
        keyword=80,
        matched=None,
        missing=None,
        yoe=6,
        education="Bachelor of Computer Science",
        section_breakdown=None,
        filename="candidate.pdf",
    ):
        return {
            "filename": filename,
            "candidate_id": "cand-1",
            "semantic_score": semantic,
            "keyword_score": keyword,
            "matched_skills": matched if matched is not None else ["python", "sql"],
            "missing_skills": missing if missing is not None else [],
            "years_of_experience": yoe,
            "education": education,
            "section_breakdown": section_breakdown
            if section_breakdown is not None
            else {"skills": 90, "experience": 90, "education": 80},
        }

    # Thresholding
    def test_threshold_hire_at_or_above_72(self):
        candidate = self._make_candidate(semantic=92, keyword=92, yoe=8, missing=[])
        result = self.engine.evaluate_candidate(candidate, self.base_jd, self.complete_text)
        self.assertGreaterEqual(result.composite_score, 72)
        self.assertEqual(result.decision, Decision.HIRE)

    def test_threshold_consider_between_50_and_71(self):
        candidate = self._make_candidate(
            semantic=60,
            keyword=55,
            matched=["python"],
            missing=["sql", "docker"],
            yoe=4,
            education="Bachelor degree",
        )
        result = self.engine.evaluate_candidate(candidate, self.base_jd, self.complete_text)
        self.assertGreaterEqual(result.composite_score, 50)
        self.assertLess(result.composite_score, 72)
        self.assertEqual(result.decision, Decision.CONSIDER)

    def test_threshold_reject_below_50(self):
        candidate = self._make_candidate(
            semantic=30,
            keyword=25,
            matched=[],
            missing=["python", "sql", "cloud"],
            yoe=1,
            education="",
            section_breakdown={"skills": 0, "experience": 0, "education": 0},
        )
        result = self.engine.evaluate_candidate(candidate, self.base_jd, "short resume")
        self.assertLess(result.composite_score, 50)
        self.assertEqual(result.decision, Decision.REJECT)

    def test_boundary_threshold_exact_scores(self):
        self.assertEqual(self.engine._decision_from_score(72), Decision.HIRE)
        self.assertEqual(self.engine._decision_from_score(50), Decision.CONSIDER)

    # Bias flags
    def test_bias_flag_age_detected(self):
        result = self.engine.evaluate_candidate(
            self._make_candidate(), self.base_jd, "Professional summary. age: 34. Python developer."
        )
        self.assertTrue(any("age" in flag.lower() for flag in result.bias_warnings))

    def test_bias_flag_marital_status_detected(self):
        result = self.engine.evaluate_candidate(
            self._make_candidate(), self.base_jd, "Candidate is married and has 6 years experience."
        )
        self.assertTrue(any("marital status" in flag.lower() for flag in result.bias_warnings))

    def test_bias_flag_photo_detected(self):
        result = self.engine.evaluate_candidate(
            self._make_candidate(), self.base_jd, "Resume includes portfolio. photo attached."
        )
        self.assertTrue(any("photo" in flag.lower() for flag in result.bias_warnings))

    def test_clean_resume_has_zero_bias_flags(self):
        result = self.engine.evaluate_candidate(self._make_candidate(), self.base_jd, self.complete_text)
        self.assertEqual(len(result.bias_warnings), 0)

    def test_bias_flags_do_not_change_composite_score(self):
        candidate = self._make_candidate()
        clean = self.engine.evaluate_candidate(candidate, self.base_jd, self.complete_text)
        biased = self.engine.evaluate_candidate(
            candidate, self.base_jd, self.complete_text + " age: 34 married photo attached"
        )
        self.assertEqual(clean.composite_score, biased.composite_score)
        self.assertGreater(len(biased.bias_warnings), 0)

    # Confidence labels
    def test_high_confidence_for_high_score_complete_data(self):
        candidate = self._make_candidate(semantic=95, keyword=95, yoe=9, missing=[])
        result = self.engine.evaluate_candidate(candidate, self.base_jd, self.complete_text)
        self.assertEqual(result.confidence_label, "High")
        self.assertGreaterEqual(result.confidence, 0.75)

    def test_borderline_confidence_medium_with_uncertainty_notes(self):
        confidence, label, notes = self.engine._confidence_assessment(
            composite_score=55.0,
            completeness_ratio=0.9,
            has_bias_flags=False,
            missing_skills_count=1,
        )
        self.assertEqual(label, "Medium")
        self.assertGreaterEqual(confidence, 0.5)
        self.assertGreaterEqual(len(notes), 1)

    def test_sparse_data_low_confidence(self):
        sparse_candidate = self._make_candidate(
            semantic=52,
            keyword=40,
            matched=[],
            missing=["python", "sql"],
            yoe=0,
            education="",
            section_breakdown={"skills": 0, "experience": 0, "education": 0},
        )
        result = self.engine.evaluate_candidate(sparse_candidate, self.base_jd, "brief")
        self.assertEqual(result.confidence_label, "Low")
        self.assertLess(result.confidence, 0.5)

    # Skill gap severity
    def test_skill_gap_required_is_critical(self):
        jd = "Python required. SQL required. 5+ years experience required."
        candidate = self._make_candidate(matched=["sql"], missing=["python"])
        result = self.engine.evaluate_candidate(candidate, jd, self.complete_text)
        gap = next(g for g in result.skill_gap_analysis if g["skill"] == "python")
        self.assertEqual(gap["severity"], "Critical")

    def test_skill_gap_mentioned_twice_is_important(self):
        jd = (
            "We use Docker in deployment. Docker knowledge helps with CI. "
            "5+ years experience required."
        )
        candidate = self._make_candidate(matched=["python"], missing=["docker"])
        result = self.engine.evaluate_candidate(candidate, jd, self.complete_text)
        gap = next(g for g in result.skill_gap_analysis if g["skill"] == "docker")
        self.assertEqual(gap["severity"], "Important")

    def test_skill_gap_once_is_nice_to_have(self):
        jd = "Experience with GraphQL is a plus. Strong communication is valued."
        candidate = self._make_candidate(matched=["python"], missing=["graphql"])
        result = self.engine.evaluate_candidate(candidate, jd, self.complete_text)
        gap = next(g for g in result.skill_gap_analysis if g["skill"] == "graphql")
        self.assertEqual(gap["severity"], "Nice-to-have")

    # General
    def test_decision_result_contains_expected_fields(self):
        result = self.engine.evaluate_candidate(self._make_candidate(), self.base_jd, self.complete_text)
        payload = result.to_dict()
        expected = {
            "filename",
            "candidate_id",
            "decision",
            "composite_score",
            "semantic_score",
            "keyword_skill_score",
            "experience_fit_score",
            "education_match_score",
            "resume_completeness_score",
            "confidence",
            "confidence_label",
            "uncertainty_notes",
            "reasons",
            "skill_gap_analysis",
            "bias_warnings",
            "matched_skills",
            "missing_skills",
            "years_of_experience",
        }
        self.assertTrue(expected.issubset(set(payload.keys())))

    def test_engine_runs_without_fastapi_context(self):
        engine = HiringDecisionEngine()
        result = engine.evaluate_candidate(self._make_candidate(), self.base_jd, self.complete_text)
        self.assertIsNotNone(result)
        self.assertIn(result.decision, {Decision.HIRE, Decision.CONSIDER, Decision.REJECT})


if __name__ == "__main__":
    unittest.main()
