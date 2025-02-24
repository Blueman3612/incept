# Educational Content Generation API

## Project Overview
This API service generates and manages educational content for K-8 students, providing capabilities for article generation, question generation, content tagging, and grading.

## Technical Stack
- **Backend Framework**: FastAPI
- **Database**: Supabase
- **Deployment**: AWS EC2
- **Language**: Python 3.9+

## Core Features
1. **Content Generation**
   - Article generation for K-8 educational topics
   - Question generation based on educational content
   
2. **Content Tagging**
   - Automated tagging of articles
   - Automated tagging of questions
   
3. **Content Grading**
   - Article quality assessment
   - Question quality and difficulty assessment

## API Endpoints

### 1. Generate Articles
- Endpoint: `/api/v1/articles/generate`
- Method: POST
- Description: Generates educational articles based on provided parameters

### 2. Generate Questions
- Endpoint: `/api/v1/questions/generate`
- Method: POST
- Description: Generates questions based on educational content

### 3. Tag Articles
- Endpoint: `/api/v1/articles/tag`
- Method: POST
- Description: Automatically tags articles with relevant metadata

### 4. Tag Questions
- Endpoint: `/api/v1/questions/tag`
- Method: POST
- Description: Automatically tags questions with relevant metadata

### 5. Grade Articles
- Endpoint: `/api/v1/articles/grade`
- Method: POST
- Description: Assesses the quality and appropriateness of articles

### 6. Grade Questions
- Endpoint: `/api/v1/questions/grade`
- Method: POST
- Description: Assesses the quality and difficulty level of questions

## Project Structure
```
.
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── articles.py
│   │   │   └── questions.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── article.py
│   │   └── question.py
│   ├── schemas/
│   │   ├── article.py
│   │   └── question.py
│   └── services/
│       ├── article_service.py
│       └── question_service.py
├── tests/
│   ├── api/
│   ├── services/
│   └── conftest.py
├── .env
├── .gitignore
├── main.py
├── requirements.txt
└── README.md
```

## Development Guidelines
1. All new features should include appropriate tests
2. Follow PEP 8 style guidelines
3. Use type hints for better code maintainability
4. Include comprehensive docstrings for all functions and classes
5. Implement proper error handling and validation
6. Use environment variables for configuration

## Setup Instructions
1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in required values
6. Run the application: `uvicorn main:app --reload`

## Testing
- Run tests: `pytest`
- Run with coverage: `pytest --cov=app tests/`

## Deployment
Deployment instructions for AWS EC2 will be added as the project progresses.

## API Documentation
Once the server is running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 