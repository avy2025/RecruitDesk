"""
RecruitDesk AI - Backend API
FastAPI application for AI-powered resume ranking using sentence transformers
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pdfplumber
import tempfile
import os
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RecruitDesk AI",
    description="AI-powered resume ranking system",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the model (loaded once at startup)
model = None


@app.on_event("startup")
async def load_model():
    """Load the sentence transformer model at startup"""
    global model
    logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Model loaded successfully")


def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract text content from a PDF file using pdfplumber
    
    Args:
        pdf_file: File-like object containing PDF data
        
    Returns:
        Extracted text as string
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


@app.post("/rank-resumes")
async def rank_resumes(
    job_description: str = Form(...),
    resumes: List[UploadFile] = File(...)
):
    """
    Rank resumes based on similarity to job description
    
    Args:
        job_description: The job description text
        resumes: List of PDF resume files (max 10)
        
    Returns:
        JSON with ranked resumes sorted by match percentage
    """
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")
    
    if not resumes or len(resumes) == 0:
        raise HTTPException(status_code=400, detail="At least one resume is required")
    
    if len(resumes) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 resumes allowed")
    
    temp_files = []
    results = []
    
    try:
        # Generate embedding for job description
        logger.info("Generating embedding for job description")
        job_embedding = model.encode([job_description])
        
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
            logger.info(f"Processing resume: {resume_file.filename}")
            resume_text = extract_text_from_pdf(temp_file_path)
            
            if not resume_text or len(resume_text.strip()) < 50:
                logger.warning(f"Insufficient text extracted from {resume_file.filename}")
                results.append({
                    "filename": resume_file.filename,
                    "match_percentage": 0,
                    "error": "Insufficient text content in resume"
                })
                continue
            
            # Generate embedding for resume
            resume_embedding = model.encode([resume_text])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(job_embedding, resume_embedding)[0][0]
            
            # Convert to percentage (0-100)
            match_percentage = round(float(similarity) * 100, 2)
            
            results.append({
                "filename": resume_file.filename,
                "match_percentage": match_percentage
            })
            
            logger.info(f"{resume_file.filename}: {match_percentage}% match")
        
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
                    logger.debug(f"Deleted temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "RecruitDesk AI API",
        "status": "running",
        "model_loaded": model is not None
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model": "all-MiniLM-L6-v2",
        "model_loaded": model is not None
    }
