"""
Hiring Decision Engine for RecruitDesk AI.

This module is intentionally standalone so it can be unit tested without FastAPI.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import re


@dataclass
class DecisionResult:
    filename: str
    candidate_id: Optional[str]
    decision: str
    composite_score: float
    semantic_score: float
    keyword_skill_score: float
    experience_fit_score: float
    education_match_score: float
    resume_completeness_score: float
    confidence: float
    confidence_label: str
    uncertainty_notes: List[str]
    reasons: List[str]
    skill_gap_analysis: List[Dict[str, str]]
    bias_warnings: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    years_of_experience: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HiringDecisionEngine:
    """
    Explainable hiring decision engine with bias-aware checks.
    """

    WEIGHTS = {
        "semantic": 0.35,
        "keyword_skill": 0.25,
        "experience": 0.25,
        "education": 0.10,
        "completeness": 0.05,
    }

    def evaluate_candidate(
        self,
        candidate_data: Dict[str, Any],
        job_description: str,
        resume_text: str = "",
    ) -> DecisionResult:
        semantic_score = self._clamp_score(candidate_data.get("semantic_score", 0.0))
        keyword_score = self._clamp_score(candidate_data.get("keyword_score", 0.0))
        matched_skills = list(candidate_data.get("matched_skills", []))
        missing_skills = list(candidate_data.get("missing_skills", []))
        years_of_experience = float(candidate_data.get("years_of_experience", 0.0) or 0.0)
        education_text = (candidate_data.get("education") or "").strip()
        section_breakdown = candidate_data.get("section_breakdown", {}) or {}
        filename = candidate_data.get("filename", "unknown")
        candidate_id = candidate_data.get("candidate_id")

        keyword_skill_score = self._compute_keyword_skill_score(
            keyword_score, matched_skills, missing_skills
        )
        experience_fit_score = self._compute_experience_fit_score(
            years_of_experience, job_description
        )
        education_match_score = self._compute_education_match_score(
            education_text, job_description
        )
        resume_completeness_score, completeness_ratio = self._compute_resume_completeness_score(
            resume_text, section_breakdown, education_text, years_of_experience
        )

        composite_score = round(
            (semantic_score * self.WEIGHTS["semantic"])
            + (keyword_skill_score * self.WEIGHTS["keyword_skill"])
            + (experience_fit_score * self.WEIGHTS["experience"])
            + (education_match_score * self.WEIGHTS["education"])
            + (resume_completeness_score * self.WEIGHTS["completeness"]),
            2,
        )

        decision = self._decision_from_score(composite_score)
        skill_gap_analysis = self._analyze_skill_gaps(missing_skills, job_description)
        bias_warnings = self._bias_sensitive_flags(resume_text)
        confidence, confidence_label, uncertainty_notes = self._confidence_assessment(
            composite_score=composite_score,
            completeness_ratio=completeness_ratio,
            has_bias_flags=bool(bias_warnings),
            missing_skills_count=len(missing_skills),
        )
        reasons = self._build_reasons(
            semantic_score=semantic_score,
            keyword_skill_score=keyword_skill_score,
            experience_fit_score=experience_fit_score,
            years_of_experience=years_of_experience,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            decision=decision,
        )

        return DecisionResult(
            filename=filename,
            candidate_id=candidate_id,
            decision=decision,
            composite_score=composite_score,
            semantic_score=semantic_score,
            keyword_skill_score=round(keyword_skill_score, 2),
            experience_fit_score=round(experience_fit_score, 2),
            education_match_score=round(education_match_score, 2),
            resume_completeness_score=round(resume_completeness_score, 2),
            confidence=round(confidence, 2),
            confidence_label=confidence_label,
            uncertainty_notes=uncertainty_notes,
            reasons=reasons,
            skill_gap_analysis=skill_gap_analysis,
            bias_warnings=bias_warnings,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            years_of_experience=years_of_experience,
        )

    def _compute_keyword_skill_score(
        self, keyword_score: float, matched_skills: List[str], missing_skills: List[str]
    ) -> float:
        total_skills = len(matched_skills) + len(missing_skills)
        skill_coverage = (len(matched_skills) / total_skills * 100.0) if total_skills else 0.0
        return (keyword_score * 0.5) + (skill_coverage * 0.5)

    def _compute_experience_fit_score(self, years_of_experience: float, job_description: str) -> float:
        required_exp = self._extract_required_experience(job_description)
        if required_exp <= 0:
            return 70.0 if years_of_experience > 0 else 45.0
        ratio = years_of_experience / required_exp if required_exp else 0.0
        if ratio >= 1.2:
            return 100.0
        if ratio >= 1.0:
            return 90.0
        if ratio >= 0.8:
            return 75.0
        if ratio >= 0.6:
            return 60.0
        return 35.0

    def _compute_education_match_score(self, education_text: str, job_description: str) -> float:
        jd = job_description.lower()
        edu = education_text.lower()
        degree_terms = [
            "bachelor",
            "master",
            "phd",
            "b.tech",
            "m.tech",
            "b.sc",
            "m.sc",
            "mba",
            "degree",
        ]
        jd_requires_degree = any(term in jd for term in degree_terms)
        if not jd_requires_degree:
            return 70.0 if edu else 55.0
        if not edu:
            return 25.0
        overlap = sum(1 for term in degree_terms if term in jd and term in edu)
        if overlap >= 2:
            return 95.0
        if overlap == 1:
            return 80.0
        return 60.0

    def _compute_resume_completeness_score(
        self,
        resume_text: str,
        section_breakdown: Dict[str, Any],
        education_text: str,
        years_of_experience: float,
    ) -> Tuple[float, float]:
        checks = []
        checks.append(1.0 if len((resume_text or "").strip()) >= 300 else 0.0)
        checks.append(1.0 if years_of_experience > 0 else 0.0)
        checks.append(1.0 if education_text else 0.0)
        checks.append(1.0 if section_breakdown.get("skills", 0) > 0 else 0.0)
        checks.append(1.0 if section_breakdown.get("experience", 0) > 0 else 0.0)
        completeness_ratio = sum(checks) / len(checks) if checks else 0.0
        return completeness_ratio * 100.0, completeness_ratio

    def _decision_from_score(self, composite_score: float) -> str:
        if composite_score >= 72:
            return "Hire"
        if composite_score >= 50:
            return "Consider"
        return "Reject"

    def _analyze_skill_gaps(self, missing_skills: List[str], job_description: str) -> List[Dict[str, str]]:
        jd = job_description.lower()
        analysis = []
        for skill in missing_skills:
            skill_l = skill.lower().strip()
            mentions = len(re.findall(rf"\b{re.escape(skill_l)}\b", jd))
            required = self._is_required_skill(skill_l, jd)
            if required:
                severity = "Critical"
                suggestion = f"Prioritize screening for direct {skill} experience or evidence of immediate production readiness."
            elif mentions >= 2:
                severity = "Important"
                suggestion = f"Probe adjacent tools and ramp-up plan for {skill} during interview."
            else:
                severity = "Nice-to-have"
                suggestion = f"Treat {skill} as a development area if core requirements are otherwise strong."
            analysis.append(
                {
                    "skill": skill,
                    "severity": severity,
                    "suggestion": suggestion,
                }
            )
        return analysis

    def _is_required_skill(self, skill: str, jd_lower: str) -> bool:
        required_cues = ["required", "must", "mandatory", "need to", "minimum", "essential"]
        for cue in required_cues:
            pattern = rf"({cue}.{{0,40}}{re.escape(skill)}|{re.escape(skill)}.{{0,40}}{cue})"
            if re.search(pattern, jd_lower):
                return True
        return False

    def _bias_sensitive_flags(self, resume_text: str) -> List[str]:
        text = (resume_text or "").lower()
        patterns = {
            "age": r"\b(age|years old|date of birth|dob)\b",
            "gender": r"\b(gender|male|female|non-binary|nonbinary)\b",
            "nationality": r"\b(nationality|citizenship|citizen of)\b",
            "religion": r"\b(religion|hindu|muslim|christian|sikh|buddhist|jewish)\b",
            "marital_status": r"\b(marital status|married|single|divorced|widowed)\b",
            "photo": r"\b(photo|photograph|headshot)\b",
        }
        warnings = []
        for field, pattern in patterns.items():
            if re.search(pattern, text):
                warnings.append(
                    f"Bias-sensitive field detected: {field.replace('_', ' ')} (excluded from scoring)"
                )
        return warnings

    def _confidence_assessment(
        self,
        composite_score: float,
        completeness_ratio: float,
        has_bias_flags: bool,
        missing_skills_count: int,
    ) -> Tuple[float, str, List[str]]:
        notes: List[str] = []
        boundary_distance = min(abs(composite_score - 72), abs(composite_score - 50))
        spread_score = min(boundary_distance / 25.0, 1.0)
        confidence = (0.55 * spread_score) + (0.45 * completeness_ratio)

        if has_bias_flags:
            notes.append("Bias-sensitive attributes were detected and excluded from scoring.")
        if boundary_distance <= 5:
            notes.append("Candidate score is close to a decision threshold.")
        if completeness_ratio < 0.6:
            notes.append("Resume data appears sparse; confidence is reduced.")
        if missing_skills_count >= 5:
            notes.append("Multiple unresolved skill gaps increase uncertainty.")

        confidence = max(0.0, min(confidence, 1.0))
        if confidence >= 0.75:
            label = "High"
        elif confidence >= 0.5:
            label = "Medium"
        else:
            label = "Low"
        return confidence, label, notes

    def _build_reasons(
        self,
        semantic_score: float,
        keyword_skill_score: float,
        experience_fit_score: float,
        years_of_experience: float,
        matched_skills: List[str],
        missing_skills: List[str],
        decision: str,
    ) -> List[str]:
        reasons: List[str] = []

        reasons.append(
            f"Semantic alignment with the role is {semantic_score:.1f}%, indicating "
            f"{'strong' if semantic_score >= 75 else 'moderate' if semantic_score >= 55 else 'limited'} relevance."
        )
        reasons.append(
            f"Skill/keyword fit is {keyword_skill_score:.1f}% with {len(matched_skills)} matched skills."
        )
        reasons.append(
            f"Experience fit is {experience_fit_score:.1f}% based on approximately {years_of_experience:.1f} years of experience."
        )

        if missing_skills:
            reasons.append(f"Key missing skills include {', '.join(missing_skills[:3])}.")
        elif matched_skills:
            reasons.append(f"No major skill gaps were detected among extracted skills.")

        if decision == "Hire":
            reasons.append("Overall evidence supports moving forward to interview/final evaluation.")
        elif decision == "Consider":
            reasons.append("Profile is promising but requires deeper interview validation on gaps.")
        else:
            reasons.append("Current profile misses too many core requirements for this role.")

        return reasons[:5]

    def _extract_required_experience(self, text: str) -> float:
        text_l = (text or "").lower()
        patterns = [
            r"(?:at least|min(?:imum)?|require(?:d|s)?|must have)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
            r"experience\s*(?:of)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
        ]
        matches: List[float] = []
        for pattern in patterns:
            for m in re.findall(pattern, text_l):
                try:
                    val = float(m)
                    if 0 <= val <= 50:
                        matches.append(val)
                except ValueError:
                    continue
        return max(matches) if matches else 0.0

    def _clamp_score(self, value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 0.0
        return max(0.0, min(score, 100.0))
