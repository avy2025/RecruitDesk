from dataclasses import dataclass, asdict
import re
import spacy
from typing import List, Dict, Optional, Set

@dataclass
class JDAnalysis:
    must_have_skills: List[str]       # explicitly required ("must", "required", "essential")
    nice_to_have_skills: List[str]    # soft signals ("preferred", "plus", "bonus", "familiar")
    experience_requirement: Dict      # {"min_years": int, "max_years": int | None}
    education_requirement: Optional[str] # "bachelor", "master", "phd", or None
    seniority_level: str              # "junior", "mid", "senior", "lead", "any"
    domain_keywords: List[str]        # core domain terms (e.g. "machine learning", "REST API")
    soft_skills: List[str]            # communication, leadership, teamwork etc.
    red_flags: List[str]              # vague/inflated JD signals: "rockstar", "ninja", "hustle culture"

class JDAnalyzer:
    def __init__(self, nlp=None):
        if nlp:
            self.nlp = nlp
        else:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.nlp = spacy.blank("en")

        self.soft_skills_list = [
            "communication", "leadership", "teamwork", "problem-solving", 
            "collaboration", "time management", "adaptability", "attention to detail"
        ]
        
        self.red_flags_list = [
            "rockstar", "ninja", "wizard", "hustle", "wear many hats", 
            "fast-paced", "self-starter", "passionate"
        ]

    def analyze(self, jd_text: str) -> JDAnalysis:
        doc = self.nlp(jd_text)
        sentences = [sent.text for sent in doc.sents]
        
        must_have_skills = self._extract_skills_by_keywords(sentences, ["must", "required", "essential", "mandatory"])
        nice_to_have_skills = self._extract_skills_by_keywords(sentences, ["preferred", "nice to have", "plus", "bonus", "familiarity with"])
        
        # Deduplicate: if it's in must-have, it shouldn't be in nice-to-have or domain_keywords
        must_have_set = set(must_have_skills)
        nice_to_have_set = set(nice_to_have_skills) - must_have_set
        
        all_tech_chunks = self._extract_noun_chunks(jd_text)
        domain_keywords = sorted(list(set(all_tech_chunks) - must_have_set - nice_to_have_set))
        
        return JDAnalysis(
            must_have_skills=sorted(list(must_have_set)),
            nice_to_have_skills=sorted(list(nice_to_have_set)),
            experience_requirement=self._extract_experience(jd_text),
            education_requirement=self._extract_education(jd_text),
            seniority_level=self._extract_seniority(jd_text),
            domain_keywords=domain_keywords,
            soft_skills=self._match_list(jd_text, self.soft_skills_list),
            red_flags=self._match_list(jd_text, self.red_flags_list)
        )

    def _extract_skills_by_keywords(self, sentences: List[str], keywords: List[str]) -> List[str]:
        extracted_skills = set()
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in keywords):
                # Extract noun chunks from this sentence
                doc = self.nlp(sent)
                for chunk in doc.noun_chunks:
                    # Clean the chunk
                    text = chunk.text.lower().strip()
                    # Filter out the keyword itself and common filler words
                    if text not in keywords and len(text) > 1 and not self.nlp.vocab[text].is_stop:
                        extracted_skills.add(text)
        return list(extracted_skills)

    def _extract_noun_chunks(self, text: str) -> List[str]:
        doc = self.nlp(text)
        chunks = set()
        for chunk in doc.noun_chunks:
            t = chunk.text.lower().strip()
            if len(t) > 2 and not self.nlp.vocab[t].is_stop:
                chunks.add(t)
        return list(chunks)

    def _extract_experience(self, text: str) -> Dict:
        text_lower = text.lower()
        min_years = 0
        max_years = None
        
        # Try range first: "2-5 years"
        range_match = re.search(r"(\d+)\s*-\s*(\d+)\s*years?", text_lower)
        if range_match:
            min_years = int(range_match.group(1))
            max_years = int(range_match.group(2))
            return {"min_years": min_years, "max_years": max_years}

        # Try "X+ years", "minimum X years", "X years"
        patterns = [
            r"(\d+)\+\s*years?",
            r"minimum\s*(\d+)\s*years?",
            r"at least\s*(\d+)\s*years?",
            r"(\d+)\s*years?"
        ]
        
        for p in patterns:
            match = re.search(p, text_lower)
            if match:
                min_years = int(match.group(1))
                break
                        
        return {"min_years": min_years, "max_years": max_years}

    def _extract_education(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        levels = {
            "phd": 4,
            "doctorate": 4,
            "master": 3,
            "msc": 3,
            "mba": 3,
            "bachelor": 2,
            "bsc": 2,
            "degree": 1
        }
        
        highest_level = None
        highest_val = 0
        
        for kw, val in levels.items():
            if kw in text_lower:
                if val > highest_val:
                    highest_val = val
                    if val == 4: highest_level = "phd"
                    elif val == 3: highest_level = "master"
                    elif val == 2: highest_level = "bachelor"
                    elif val == 1: highest_level = "degree"
        
        return highest_level

    def _extract_seniority(self, text: str) -> str:
        text_lower = text.lower()
        mapping = {
            "entry level": "junior",
            "junior": "junior",
            "associate": "mid",
            "mid level": "mid",
            "mid-level": "mid",
            "senior": "senior",
            "lead": "lead",
            "staff": "lead",
            "principal": "lead",
            "head of": "lead"
        }
        
        for kw, level in reversed(list(mapping.items())): # Check senior levels first
            if kw in text_lower:
                return level
        
        return "any"

    def _match_list(self, text: str, items: List[str]) -> List[str]:
        text_lower = text.lower()
        found = []
        for item in items:
            if item in text_lower:
                found.append(item)
        return sorted(list(set(found)))
