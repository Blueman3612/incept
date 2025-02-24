from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from app.api.v1.articles import router as articles_router
from app.services.openai_service import OpenAIService

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

# Include routers
app.include_router(articles_router, prefix="/api/v1")

# Initialize OpenAI service
openai_service = OpenAIService()

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "title": API_TITLE,
        "version": API_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 