from dataclasses import dataclass, asdict
import re
import spacy
from typing import List, Dict, Optional

@dataclass
class JDAnalysis:
    must_have_skills: list[str]        # from "required", "must", "essential", "mandatory" sentences
    nice_to_have_skills: list[str]     # from "preferred", "plus", "bonus", "familiar" sentences
    experience_requirement: dict       # {"min_years": int, "max_years": int | None}
    education_requirement: str | None  # "bachelor", "master", "phd", or None
    seniority_level: str               # "junior", "mid", "senior", "lead", "any"
    domain_keywords: list[str]         # technical terms not in must_have or nice_to_have
    soft_skills: list[str]             # matched from hardcoded list
    red_flags: list[str]               # inflated JD language detected

class JDAnalyzer:
    def __init__(self, nlp=None):
        if nlp:
            self.nlp = nlp
        else:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.nlp = spacy.blank("en")
        
        self.soft_skills_list = ["communication", "leadership", "teamwork", "problem-solving", "collaboration", "time management", "adaptability", "attention to detail", "critical thinking", "ownership"]
        self.red_flags_list = ["rockstar", "ninja", "wizard", "hustle", "wear many hats", "fast-paced", "self-starter", "passionate", "go-getter", "superhero"]
        
        try:
            from rag.parser import TECH_SKILLS_DB
            self.tech_skills = TECH_SKILLS_DB
        except ImportError:
            self.tech_skills = set()

    def analyze(self, jd_text: str) -> JDAnalysis:
        doc = self.nlp(jd_text)
        sentences = list(doc.sents)
        
        must_have_keywords = ["required", "must have", "essential", "mandatory", "must"]
        nice_to_have_keywords = ["preferred", "nice to have", "a plus", "bonus", "familiarity with", "familiar"]
        
        must_have_skills = []
        nice_to_have_skills = []
        
        for sent in sentences:
            sent_text = sent.text.lower()
            # Check must-have first
            if any(kw in sent_text for kw in must_have_keywords):
                must_have_skills.extend(self._extract_terms(sent))
            elif any(kw in sent_text for kw in nice_to_have_keywords):
                nice_to_have_skills.extend(self._extract_terms(sent))
        
        must_have_skills = sorted(list(set(must_have_skills)))
        nice_to_have_skills = sorted(list(set(nice_to_have_skills)))
        
        # domain_keywords: all technical noun chunks from the full JD not already captured in must_have or nice_to_have
        all_terms = self._extract_terms(doc)
        must_set = set(must_have_skills)
        nice_set = set(nice_to_have_skills)
        domain_keywords = sorted(list(set(all_terms) - must_set - nice_set))
        
        return JDAnalysis(
            must_have_skills=must_have_skills,
            nice_to_have_skills=nice_to_have_skills,
            experience_requirement=self._extract_experience(jd_text),
            education_requirement=self._extract_education(jd_text),
            seniority_level=self._extract_seniority(jd_text),
            domain_keywords=domain_keywords,
            soft_skills=self._match_list(jd_text, self.soft_skills_list),
            red_flags=self._match_list(jd_text, self.red_flags_list)
        )

    def _extract_terms(self, doc_or_sent) -> List[str]:
        terms = []
        # Extract noun chunks
        if hasattr(doc_or_sent, "noun_chunks"):
            for chunk in doc_or_sent.noun_chunks:
                text = chunk.text.lower().strip()
                if len(text) > 1 and not self.nlp.vocab[text].is_stop:
                    terms.append(text)
        
        # Extract known tech tokens
        for token in doc_or_sent:
            text = token.text.lower().strip()
            if text in self.tech_skills:
                terms.append(text)
        
        return list(set(terms))

    def _extract_experience(self, text: str) -> Dict:
        text_lower = text.lower()
        
        # Range: "2-5 years"
        range_match = re.search(r"(\d+)\s*-\s*(\d+)\s*years?", text_lower)
        if range_match:
            return {"min_years": int(range_match.group(1)), "max_years": int(range_match.group(2))}
        
        # Plus: "3+ years"
        plus_match = re.search(r"(\d+)\+\s*years?", text_lower)
        if plus_match:
            return {"min_years": int(plus_match.group(1)), "max_years": None}
            
        # Min/At least: "minimum 4 years", "at least 2 years"
        min_match = re.search(r"(?:minimum|at least)\s*(\d+)\s*years?", text_lower)
        if min_match:
            return {"min_years": int(min_match.group(1)), "max_years": None}
            
        # Simple: "5 years"
        simple_match = re.search(r"(\d+)\s*years?", text_lower)
        if simple_match:
            return {"min_years": int(simple_match.group(1)), "max_years": None}
            
        return {"min_years": 0, "max_years": None}

    def _extract_education(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if "phd" in text_lower or "doctorate" in text_lower:
            return "phd"
        if "master" in text_lower:
            return "master"
        if "bachelor" in text_lower or "degree" in text_lower:
            return "bachelor"
        return None

    def _extract_seniority(self, text: str) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["lead", "staff", "principal"]):
            return "lead"
        if "senior" in text_lower:
            return "senior"
        if any(kw in text_lower for kw in ["mid", "intermediate"]):
            return "mid"
        if any(kw in text_lower for kw in ["junior", "entry level"]):
            return "junior"
        return "any"

    def _match_list(self, text: str, items: List[str]) -> List[str]:
        text_lower = text.lower()
        found = []
        for item in items:
            if item in text_lower:
                found.append(item)
        return sorted(list(set(found)))
