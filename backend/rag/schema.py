from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DocumentMetadata(BaseModel):
    type: str = Field(..., description="Type of document, e.g., 'resume' or 'job_description'")
    candidate_id: Optional[str] = Field(None, description="Optional ID of the candidate")
    skills: List[str] = Field(default_factory=list, description="List of skills mentioned in the document")
    experience: float = Field(default=0.0, description="Years of experience associated with the document")

class RAGDocument(BaseModel):
    id: str = Field(..., description="Unique identifier for the document")
    text: str = Field(..., description="The main text content of the document")
    metadata: DocumentMetadata = Field(..., description="Structured metadata for the document")
