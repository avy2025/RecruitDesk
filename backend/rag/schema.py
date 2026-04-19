from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DocumentMetadata(BaseModel):
    type: str = Field(..., description="Type of document, e.g., 'resume' or 'job_description'")
    source: str = Field("resume", description="Source of the document")
    candidate_id: Optional[str] = Field(None, description="Unique ID for the candidate")
    name: Optional[str] = Field(None, description="Name of the candidate")
    skills: List[str] = Field(default_factory=list, description="List of detected skills")
    experience: float = Field(default=0.0, description="Total years of experience")
    confidence: float = Field(default=0.0, description="Confidence score for metadata extraction (0.0 - 1.0)")
    chunk_id: Optional[str] = Field(None, description="Unique ID for this specific chunk")
    chunk_index: Optional[int] = Field(None, description="Index of this chunk in the parent document")

class RAGDocument(BaseModel):
    id: str = Field(..., description="Unique identifier for the document chunk")
    text: str = Field(..., description="The text content of this chunk")
    metadata: DocumentMetadata = Field(..., description="Structured metadata for the chunk")
