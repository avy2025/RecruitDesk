"""
RecruitDesk AI - Backend API
FastAPI application for AI-powered resume ranking using sentence transformers and spaCy
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from sklearn.metrics.pairwise import cosine_similarity
import pdfplumber
import tempfile
import os
from typing import List, Dict, Any
import logging
import spacy
import numpy as np
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RecruitDesk AI",
    description="AI-powered resume ranking system with explainable matching",
    version="2.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store models (loaded once at startup)
model = None
nlp = None


@app.on_event("startup")
async def load_models():
    """Load the sentence transformer model and spaCy model at startup"""
    global model, nlp
    
    # Load Sentence Transformer
    logger.info("Loading sentence-transformers model: all-mpnet-base-v2 (This may take a while on first run)")
    try:
        model = SentenceTransformer('all-mpnet-base-v2')
        logger.info("Sentence Transformer model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load sentence-transformers model: {e}")
        # Fallback to smaller model if large one fails
        logger.warning("Falling back to all-MiniLM-L6-v2")
        model = SentenceTransformer('all-MiniLM-L6-v2')

    # Load spaCy model
    logger.info("Loading spaCy model: en_core_web_sm")
    try:
        nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model loaded successfully")
    except OSError:
        logger.warning("spaCy model 'en_core_web_sm' not found. Downloading...")
        # Use subprocess to download the model to avoid permission issues or path issues
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model downloaded and loaded successfully")
        except Exception as e:
            logger.error(f"Failed to download spaCy model: {e}")
            # Fallback to a basic blank model if download fails
            nlp = spacy.blank("en")
            logger.warning("Falling back to blank spaCy model")


def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract text content from a PDF file using pdfplumber
    """
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")


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


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract entities like Skills, Organizations, Dates using spaCy
    """
    if not nlp:
        return {"ORG": [], "DATE": [], "NOUN_CHUNKS": []}

    doc = nlp(text)
    entities = {
        "ORG": [],
        "DATE": [],
        "GPE": [], # Locations
        "PERSON": [],
        "NOUN_CHUNKS": [] # Potential skills/technologies often appear as noun chunks
    }
    
    for ent in doc.ents:
        if ent.label_ in entities:
            if ent.text not in entities[ent.label_]:
                entities[ent.label_].append(ent.text)
                
    # Extract noun chunks for keyword matching
    for chunk in doc.noun_chunks:
        clean_chunk = chunk.text.lower().strip()
        if len(clean_chunk) > 2 and not nlp.vocab[clean_chunk].is_stop:
            entities["NOUN_CHUNKS"].append(clean_chunk)
            
    return entities


def extract_years_of_experience(text: str) -> float:
    """
    Extract total years of experience using regex patterns and date calculation
    """
    # 1. Direct mentions like "5 years", "10+ years", "5+ yrs"
    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?|yr)\b',
        r'(?:experience|history)\s*of\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?|yr)\b'
    ]
    
    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        matches.extend([float(m) for m in found])
    
    # 2. Date ranges like "2018 - 2023" or "2015 - Present"
    date_range_pattern = r'(?:20|19)\d{2}\s*[-–—]\s*(?:present|current|20\d{2})'
    date_ranges = re.findall(date_range_pattern, text, re.IGNORECASE)
    
    current_year = datetime.now().year
    range_years = 0
    for dr in date_ranges:
        parts = re.split(r'[-–—]', dr)
        if len(parts) == 2:
            try:
                start_year = int(re.search(r'\d{4}', parts[0]).group())
                end_str = parts[1].strip().lower()
                if 'present' in end_str or 'current' in end_str:
                    end_year = current_year
                else:
                    end_year = int(re.search(r'\d{4}', end_str).group())
                
                exp = end_year - start_year
                if 0 < exp < 50:
                    range_years += exp
            except (ValueError, AttributeError):
                continue

    if range_years > 0:
        matches.append(range_years)
    
    if matches:
        # Filter for realistic years of experience (0 to 50)
        valid_matches = [m for m in matches if 0 <= m <= 50]
        if valid_matches:
            # We use max for explicit mentions, but we should be careful about summing ranges vs mentions
            # If we have ranges, they might be more accurate if we sum unique periods, 
            # but for an MVP, max of either explicit or range is a good heuristic.
            return max(valid_matches)
    
    return 0.0


def calculate_section_aware_score(job_text: str, resume_sections: Dict[str, str]) -> Dict[str, float]:
    """
    Calculate semantic similarity scores for each section separately
    """
    job_embedding = model.encode(job_text, convert_to_tensor=True)
    
    section_scores = {}
    weights = {
        "skills": 0.45,
        "experience": 0.35,
        "education": 0.05,
        "summary": 0.05,
        "projects": 0.10
    }
    
    for section, text in resume_sections.items():
        if text.strip() and len(text.strip()) > 20:
            section_embedding = model.encode(text, convert_to_tensor=True)
            score = float(util.cos_sim(job_embedding, section_embedding)[0][0]) * 100
            section_scores[section] = round(score, 2)
        else:
            section_scores[section] = 0
            
    # Calculate weighted average
    weighted_score = sum(section_scores.get(s, 0) * weights.get(s, 0.1) for s in weights)
    # Re-normalize if some sections were empty
    total_weight = sum(weights.get(s, 0) for s in section_scores if section_scores[s] > 0)
    if total_weight > 0:
        weighted_score = weighted_score / total_weight
    
    return {
        "weighted_semantic_score": round(weighted_score, 2),
        "section_breakdown": section_scores
    }


def calculate_hybrid_score(job_text: str, resume_text: str, resume_details: Dict) -> Dict[str, Any]:
    """
    Calculate a hybrid score based on section-aware semantic similarity, keyword overlap, and skills.
    """
    # 1. Section-aware Semantic Score
    section_data = calculate_section_aware_score(job_text, resume_details['sections'])
    semantic_score = section_data['weighted_semantic_score']
    
    # 2. Extract Years of Experience
    yoe = extract_years_of_experience(resume_text)

    # 3. Keyword/Entity Overlap Score
    if nlp:
        job_doc = nlp(job_text)
        job_keywords = set([chunk.text.lower() for chunk in job_doc.noun_chunks if not nlp.vocab[chunk.text.lower()].is_stop])
        resume_keywords = set(resume_details['entities']['NOUN_CHUNKS'])
        
        # Enhanced tech skills database
        tech_skills_db = {
            # Languages
            "python", "java", "c++", "c#", "javascript", "typescript", "golang", "rust", "php", "ruby", "swift", "kotlin", "scala", "dart", "r", "julia", "lua",
            # Frontend
            "react", "angular", "vue", "next.js", "nuxt.js", "svelte", "tailwind", "sass", "less", "html", "css", "bootstrap", "redux", "mobx", "webpack", "vite", "babel",
            # Backend/DB
            "node", "express", "fastapi", "django", "flask", "spring boot", "laravel", "rails", "asp.net", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sql", "nosql", "cassandra", "mariadb", "sqlite",
            # Cloud/DevOps
            "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "terraform", "ansible", "linux", "git", "ci/cd", "circleci", "gitlab", "bitbucket", "prometheus", "grafana", "nginx", "apache",
            # AI/Data
            "machine learning", "ai", "deep learning", "nlp", "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn", "spark", "hadoop", "data science", "keras", "opencv", "matplotlib", "seaborn", "nltk", "spacy",
            # Mobile
            "flutter", "react native", "ios", "android", "xamarin", "ionic",
            # Soft Skills/Process
            "agile", "scrum", "kanban", "communication", "leadership", "management", "problem solving", "analysis", "teamwork", "critical thinking"
        }
        
        # Extract explicit skills from text
        job_skills = {token.text.lower() for token in job_doc if token.text.lower() in tech_skills_db}
        # Check noun chunks for skills too (many are multi-word)
        for chunk in job_doc.noun_chunks:
            if chunk.text.lower() in tech_skills_db:
                job_skills.add(chunk.text.lower())
                
        resume_doc = nlp(resume_text)
        resume_skills = {token.text.lower() for token in resume_doc if token.text.lower() in tech_skills_db}
        for chunk in resume_doc.noun_chunks:
            if chunk.text.lower() in tech_skills_db:
                resume_skills.add(chunk.text.lower())
        
        # Calculate overlap
        common_keywords = job_keywords.intersection(resume_keywords)
        common_skills = job_skills.intersection(resume_skills)
        missing_skills = job_skills - resume_skills
        
        # Keyword score calculation
        keyword_score = (len(common_keywords) / len(job_keywords) * 100) if job_keywords else 0
        skill_score = (len(common_skills) / len(job_skills) * 100) if job_skills else 0
            
        matched_skills_list = list(common_skills)
        missing_skills_list = list(missing_skills)
        matched_keywords_list = list(common_keywords)[:10]

    else:
        keyword_score = 0
        skill_score = 0
        matched_skills_list = []
        missing_skills_list = []
        matched_keywords_list = []

    # 5. Extract Top 3 Strengths
    # Logic: Most relevant matched skills or high-scoring sections
    strengths = []
    # Mix of skills and section performance
    sorted_skills = sorted(matched_skills_list, key=lambda s: len(s), reverse=True) # Longest skills often more specific
    if sorted_skills:
        strengths.extend(sorted_skills[:2])
    
    if semantic_score > 80:
        strengths.append("Exceptional semantic match")
    elif yoe >= 5:
        strengths.append(f"Deep experience ({yoe}+ years)")
    elif section_data['section_breakdown'].get('skills', 0) > 85:
        strengths.append("High technical skill density")
    
    # Ensure unique and capped at 3
    final_strengths = []
    for s in strengths:
        if s not in final_strengths:
            final_strengths.append(s)
    final_strengths = final_strengths[:3]

    # Calculate Final Hybrid Score (60% Semantic, 40% Skills)
    final_score = round((semantic_score * 0.6) + (skill_score * 0.4), 2)

    return {
        "final_score": final_score,
        "semantic_score": semantic_score,
        "skill_score": round(skill_score, 2),
        "keyword_score": round(keyword_score, 2),
        "matched_skills": matched_skills_list,
        "missing_skills": missing_skills_list,
        "matched_keywords": matched_keywords_list,
        "section_breakdown": section_data['section_breakdown'],
        "years_of_experience": yoe,
        "top_strengths": final_strengths
    }


@app.post("/rank-resumes")
async def rank_resumes(
    job_description: str = Form(...),
    resumes: List[UploadFile] = File(...)
):
    """
    Rank resumes based on hybrid matching algorithm
    """
    # Basic Input Sanitization
    job_description = re.sub(r'[^\x00-\x7F]+', ' ', job_description) # Remove non-ASCII
    job_description = job_description.strip()

    if not job_description or len(job_description) < 10:
        raise HTTPException(status_code=400, detail="Job description is too short or empty")
    
    if not resumes or len(resumes) == 0:
        raise HTTPException(status_code=400, detail="At least one resume is required")
    
    if len(resumes) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 resumes allowed")
    
    temp_files = []
    results = []
    
    try:
        logger.info(f"Ranking {len(resumes)} resumes against job description")
        
        # Process each resume
        for resume_file in resumes:
            # Validate file type
            if not resume_file.filename.lower().endswith('.pdf'):
                logger.warning(f"Skipping non-PDF file: {resume_file.filename}")
                continue
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                content = await resume_file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
                temp_files.append(temp_file_path)
            
            # Extract text from PDF
            resume_text = extract_text_from_pdf(temp_file_path)
            
            if not resume_text or len(resume_text.strip()) < 50:
                results.append({
                    "filename": resume_file.filename,
                    "match_percentage": 0,
                    "error": "Insufficient text content",
                    "match_details": {}
                })
                continue
            
            # Parse sections and entities
            sections = parse_resume_sections(resume_text)
            entities = extract_entities(resume_text)
            
            resume_details = {
                "sections": sections,
                "entities": entities
            }
            
            # Calculate match scores
            match_data = calculate_hybrid_score(job_description, resume_text, resume_details)
            
            # Generate summary reasons
            match_reasons = []
            if match_data['semantic_score'] > 75:
                match_reasons.append("High semantic similarity to job description")
            if len(match_data['matched_skills']) > 0:
                match_reasons.append(f"Matched key skills: {', '.join(match_data['matched_skills'][:5])}")
            if match_data['keyword_score'] > 50:
                 match_reasons.append("Strong overlap in terminology and domain language")
            
            # Generate candidate summary
            skill_count = len(match_data['matched_skills'])
            yoe = match_data['years_of_experience']
            summary = f"{yoe}+ years of experience. Matched {skill_count} key skills including {', '.join(match_data['matched_skills'][:3])}."
            
            results.append({
                "filename": resume_file.filename,
                "match_percentage": match_data['final_score'],
                "summary": summary,
                "years_of_experience": yoe,
                "top_strengths": match_data['top_strengths'],
                "match_details": {
                    "semantic_score": match_data['semantic_score'],
                    "skill_score": match_data['skill_score'],
                    "keyword_score": match_data['keyword_score'],
                    "matched_skills": match_data['matched_skills'],
                    "missing_skills": match_data['missing_skills'],
                    "section_breakdown": match_data['section_breakdown'],
                    "match_reasons": match_reasons
                }
            })
            
            logger.info(f"{resume_file.filename}: {match_data['final_score']}% match")
        
        # Sort results by match percentage (highest first)
        results.sort(key=lambda x: x.get('match_percentage', 0), reverse=True)
        
        return {
            "success": True,
            "total_resumes": len(results),
            "ranked_resumes": results
        }
        
    except Exception as e:
        logger.error(f"Error processing resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    finally:
        # Clean up temporary files
        for temp_file_path in temp_files:
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")


@app.post("/generate-questions")
async def generate_interview_questions(data: Dict[str, Any]):
    """
    Generate tailored interview questions based on match results
    """
    matched_skills = data.get("matched_skills", [])
    missing_skills = data.get("missing_skills", [])
    yoe = data.get("years_of_experience", 0)
    
    questions = []
    
    # Core technical questions based on missing skills (probing gaps)
    if missing_skills:
        skill = missing_skills[0]
        questions.append({
            "type": "technical",
            "skill": skill,
            "question": f"While your resume shows strong experience, we noticed {skill} is a key requirement. Can you describe your familiarity with it or a similar technology?",
            "expected": f"Demonstration of transferrable skills or a quick learning ability regarding {skill}."
        })
    
    # Deep dive into strengths
    if matched_skills:
        skill = matched_skills[0]
        questions.append({
            "type": "experience",
            "skill": skill,
            "question": f"Given your expertise in {skill}, what was the most challenging technical hurdle you faced in a recent project involving it?",
            "expected": "Detailed problem-solving approach and technical depth."
        })
        
    # Seniority/Role based
    if yoe >= 5:
        questions.append({
            "type": "leadership",
            "question": "With your extensive experience, how do you approach mentoring junior developers or architecting systems for scalability?",
            "expected": "Evidence of leadership qualities and architectural thinking."
        })
    else:
        questions.append({
            "type": "career",
            "question": "As someone early in their career, how do you keep up with rapidly evolving tech stacks like the ones mentioned in the job description?",
            "expected": "Curiosity, continuous learning habits, and resourcefulness."
        })
    
    # Scenario based
    if "agile" in [s.lower() for s in matched_skills]:
        questions.append({
            "type": "process",
            "question": "How do you handle scope creep or shifting priorities in an Agile sprint environment?",
            "expected": "Adaptability and communication skills within a team framework."
        })
    
    # Soft skills
    questions.append({
        "type": "soft_skill",
        "question": "Describe a time you had a technical disagreement with a teammate. How did you resolve it?",
        "expected": "Collaboration and maturity."
    })
    
    return {
        "success": True,
        "questions": questions[:5]
    }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "RecruitDesk AI API v2.0",
        "status": "running",
        "model_loaded": model is not None,
        "spacy_status": "loaded" if nlp else "not loaded"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model": "all-mpnet-base-v2" if model else "loading/failed",
        "spacy": "en_core_web_sm" if nlp else "loading/failed"
    }
