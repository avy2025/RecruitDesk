import os
import re
import pdfplumber
import docx
import spacy
from typing import Dict, List, Any, Optional
from datetime import datetime

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model 'en_core_web_sm' not found. Falling back to blank model.")
    nlp = spacy.blank("en")

# Extensive tech skills list (derived from main.py and expanded)
TECH_SKILLS_DB = {
    "python", "java", "c++", "c#", "javascript", "typescript", "golang", "rust", "php", "ruby", "swift", "kotlin", "scala", "dart", "r", "julia", "lua",
    "react", "angular", "vue", "next.js", "nuxt.js", "svelte", "tailwind", "sass", "less", "html", "css", "bootstrap", "redux", "mobx", "webpack", "vite", "babel",
    "node", "express", "fastapi", "django", "flask", "spring boot", "laravel", "rails", "asp.net", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sql", "nosql", "cassandra", "mariadb", "sqlite",
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "terraform", "ansible", "linux", "git", "ci/cd", "circleci", "gitlab", "bitbucket", "prometheus", "grafana", "nginx", "apache",
    "machine learning", "ai", "deep learning", "nlp", "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn", "spark", "hadoop", "data science", "keras", "opencv", "matplotlib", "seaborn", "nltk", "spacy",
    "flutter", "react native", "ios", "android", "xamarin", "ionic",
    "agile", "scrum", "kanban", "communication", "leadership", "management", "problem solving", "analysis", "teamwork", "critical thinking"
}

def parse_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    text = ""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""
        
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                logger.warning(f"PDF has no pages: {file_path}")
                return ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.error(f"Error parsing PDF {file_path}: {str(e)}")
        # If pdfplumber fails, it might be an encrypted or corrupt file
    return text.strip()

def parse_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    text = ""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""

    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
    except Exception as e:
        logger.error(f"Error parsing DOCX {file_path}: {str(e)}")
    return text.strip()

def parse_resume_sections(text: str) -> Dict[str, str]:
    """
    Segment resume text into logical sections (Skills, Experience, Education)
    """
    sections = {
        "skills": "",
        "experience": "",
        "education": "",
        "projects": "",
        "summary": ""
    }
    
    # Common headers for sections (case insensitive)
    headers = {
        "skills": ["skills", "technical skills", "technologies", "competencies", "core competencies", "tools", "expertise"],
        "experience": ["experience", "work experience", "professional experience", "employment history", "work history", "employment"],
        "education": ["education", "academic background", "certifications", "qualifications", "academic profile"],
        "projects": ["projects", "personal projects", "academic projects", "key projects"],
        "summary": ["summary", "profile", "professional summary", "about me", "objective", "professional profile"]
    }
    
    current_section = "summary" # Default to summary or unmatched text
    
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip().lower().rstrip(':')
        
        # Check if line is a header
        is_header = False
        if len(line_clean) < 40: # Headers are usually short
            for section, keywords in headers.items():
                if any(keyword == line_clean for keyword in keywords):
                    current_section = section
                    is_header = True
                    break
        
        if not is_header and line.strip():
            sections[current_section] += line + "\n"
            
    return sections

def parse_file(file_path: str) -> str:
    """Unified entry point for parsing files."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return parse_pdf(file_path)
    elif ext == '.docx':
        return parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Only PDF and DOCX are supported.")

def extract_years_of_experience(text: str) -> float:
    """Extract total years of experience using regex patterns."""
    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?|yr)\b',
        r'(?:experience|history)\s*of\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?|yr)\b'
    ]
    
    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        matches.extend([float(m) for m in found])
    
    # Date range extraction (simplified)
    date_range_pattern = r'(?:20|19)\d{2}\s*[-–—]\s*(?:present|current|20\d{2})'
    date_ranges = re.findall(date_range_pattern, text, re.IGNORECASE)
    
    current_year = datetime.now().year
    range_years = 0
    for dr in date_ranges:
        parts = re.split(r'[-–—]', dr)
        if len(parts) == 2:
            try:
                start_match = re.search(r'\d{4}', parts[0])
                if start_match:
                    start_year = int(start_match.group())
                    end_str = parts[1].strip().lower()
                    if 'present' in end_str or 'current' in end_str:
                        end_year = current_year
                    else:
                        end_match = re.search(r'\d{4}', end_str)
                        end_year = int(end_match.group()) if end_match else current_year
                    
                    exp = end_year - start_year
                    if 0 < exp < 50:
                        range_years += exp
            except (ValueError, AttributeError):
                continue
    
    if range_years > 0:
        matches.append(float(range_years))
        
    return max(matches) if matches else 0.0

def extract_metadata(text: str) -> Dict[str, Any]:
    """
    Extract name, skills, and experience with confidence scoring.
    """
    doc = nlp(text[:10000]) # Limit spacy processing for very long docs
    
    # 1. Extract Name (best effort)
    name = None
    name_confidence = 0.0
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text
            name_confidence = 0.8
            break
    
    # Fallback: Check first line if no PERSON found
    if not name:
        lines = text.split('\n')
        if lines and len(lines[0].split()) <= 4: # Likely a name
            name = lines[0].strip()
            name_confidence = 0.4

    # 2. Extract Skills
    detected_skills = []
    # Token-based check
    tokens = {token.text.lower() for token in doc}
    detected_skills.extend([skill for skill in TECH_SKILLS_DB if skill in tokens])
    
    # Noun chunk check for multi-word skills
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.lower().strip()
        if chunk_text in TECH_SKILLS_DB and chunk_text not in detected_skills:
            detected_skills.append(chunk_text)
            
    # 3. Extract Experience
    yoe = extract_years_of_experience(text)
    
    # 4. Handle very small text edge case
    if len(text.strip()) < 50:
        logger.warning("Extremely short text provided for metadata extraction.")
    
    # 4. Calculate overall confidence
    # Heuristic: 
    # - name_confidence (0.3 weight)
    # - skill_count (0.4 weight, capped at 10 skills)
    # - experience found (0.3 weight)
    skill_conf = min(len(detected_skills) / 10, 1.0)
    exp_conf = 1.0 if yoe > 0 else 0.0
    
    overall_confidence = (name_confidence * 0.3) + (skill_conf * 0.4) + (exp_conf * 0.3)
    
    return {
        "name": name,
        "skills": detected_skills,
        "experience": yoe,
        "confidence": round(overall_confidence, 2)
    }

def extract_job_metadata(text: str) -> Dict[str, Any]:
    """
    Extract role, required skills, and experience required from a job description.
    """
    doc = nlp(text[:10000])
    
    # 1. Extract Role (Job Title)
    # Heuristic: Check first few lines for capitalized nouns or known title patterns
    role = None
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        for line in lines[:3]: # Usually in the first 3 non-empty lines
            if 3 < len(line) < 100:
                role = line
                break
    
    # 2. Extract Skills
    detected_skills = []
    tokens = {token.text.lower() for token in doc}
    detected_skills.extend([skill for skill in TECH_SKILLS_DB if skill in tokens])
    
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.lower().strip()
        if chunk_text in TECH_SKILLS_DB and chunk_text not in detected_skills:
            detected_skills.append(chunk_text)
            
    # 3. Extract Experience Required
    # Look for "X+ years", "at least X years", etc.
    exp_required = extract_years_of_experience(text)
    
    return {
        "role": role,
        "required_skills": sorted(list(set(detected_skills))),
        "experience_required": float(exp_required)
    }
