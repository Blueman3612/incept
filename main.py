from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from app.services.openai_service import OpenAIService
from pydantic import BaseModel

# Get settings
API_TITLE = "Educational Content Generation API"
API_DESCRIPTION = "API for generating and managing educational content for K-8 students"
API_VERSION = "v1"

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI service
openai_service = OpenAIService()

class ContentRequest(BaseModel):
    topic: str
    grade_level: str
    content_type: str
    additional_instructions: Optional[str] = ""

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "title": API_TITLE,
        "version": API_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.post("/api/v1/generate-content")
async def generate_content(request: ContentRequest):
    """
    Generate educational content using GPT-4.
    
    Parameters:
    - topic: The main topic for the content
    - grade_level: Target grade level (K-8)
    - content_type: Type of content (article, quiz, lesson_plan)
    - additional_instructions: Optional specific requirements
    """
    try:
        content = await openai_service.generate_educational_content(
            topic=request.topic,
            grade_level=request.grade_level,
            content_type=request.content_type,
            additional_instructions=request.additional_instructions
        )
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 