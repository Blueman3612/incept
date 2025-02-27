# Educational Content Generation API for Language Arts Grade 4

## Project Overview
This API service specializes in generating high-quality educational content for Grade 4 Language Arts, with a focus on achieving 99%+ precision in content quality. The service leverages GPT-4 via OpenAI's API for content generation and utilizes existing content from the Common Core Crawl (CCC) database for training and validation.

Key Objectives:
- Generate Direct Instruction (DI) style articles optimized for Grade 4 Language Arts
- Create comprehensive question banks with 100+ questions per difficulty level
- Maintain 99%+ precision in content quality through automated QC
- Leverage existing CCC database content for training and validation
- Integrate with Common Core State Standards (CCSS) for Language Arts

Project Deliverables:
1. Working API endpoints for content generation, tagging, and grading
2. Generated course content displayed through a course visualizer
3. Complete test harness with regression testing capabilities
4. Integration with CCC database for content examples and validation

## Technical Stack
- **Backend Framework**: FastAPI
- **Database**: Supabase
- **AI Model**: OpenAI GPT-4
- **Deployment**: AWS EC2
- **Language**: Python 3.9+
- **Content Storage**: 1EdTech QTI 3.0 Implementation
- **Content Source**: Common Core Crawl (CCC) Database

## Core Features
1. **Article Generation System**
   - DI-style article generation for Grade 4 Language Arts
   - Worked examples integration
   - Quality control system with 99%+ precision
   - Integration with CCC database for examples
   
2. **Question Generation System**
   - Deep question banks (100+ per difficulty level)
   - Three-tiered difficulty system (easy, medium, hard)
   - Question variation generation
   - MCQ and FRQ support
   
3. **Quality Control System**
   - LLM-as-judge automated QC
   - Test harness with good/bad examples
   - Continuous quality improvement process
   - Mutation testing for quality criteria

## Data Sources
1. **Common Core Crawl (CCC) Database**
   - Pre-tagged content by source, type, subject, grade, and standard
   - Content types: questions, articles, videos
   - Question metadata: difficulty (1-3), interaction type (MCQ/FRQ)
   - Access via API or direct database connection

2. **Academic Team Course Definitions**
   - Lesson sequences by subject and grade level
   - Baseline quality examples
   - Educational standards mapping

## Content Storage (QTI Implementation)

### Course Structure in QTI
1. **Course (AssessmentTest)**
   - Complete Grade 4 Language Arts course
   - Organized sequence of lessons

2. **Lesson (TestPart)**
   - Contains Article and Question Bank sections
   - Maps to specific educational standards

3. **Article Section (Section)**
   - Contains worked example AssessmentItems
   - References shared AssessmentStimulus

4. **Question Bank Section**
   - Collection of AssessmentItems
   - Metadata for difficulty levels
   - Comprehensive coverage of lesson content

## API Endpoints

### Article Endpoints
1. **Tag Article**
- Endpoint: `/api/v1/articles/tag`
- Method: POST
- Description: Tags articles with subject (Language Arts), grade (4), standard, and lesson
- Request Body:
  ```json
  {
    "content": "string",
    "metadata": {
      "title": "string",
      "format": "string"
    }
  }
  ```

2. **Grade Article**
- Endpoint: `/api/v1/articles/grade`
- Method: POST
- Description: Assesses article quality against DI style requirements
- Request Body:
  ```json
  {
    "content": "string",
    "metadata": {
      "tags": ["string"],
      "grade_level": 4,
      "subject": "Language Arts"
    }
  }
  ```

3. **Generate Article**
- Endpoint: `/api/v1/articles/generate`
- Method: POST
- Description: Generates DI-style articles for Grade 4 Language Arts
- Request Body:
  ```json
  {
    "lesson": "string",
    "standard": "string",
    "additional_instructions": "string"
  }
  ```

### Question Endpoints
1. **Tag Question**
- Endpoint: `/api/v1/questions/tag`
- Method: POST
- Description: Tags questions with subject, grade, standard, lesson, and difficulty
- Request Body:
  ```json
  {
    "question": "string",
    "metadata": {
      "format": "string"
    }
  }
  ```

2. **Grade Question**
- Endpoint: `/api/v1/questions/grade`
- Method: POST
- Description: Assesses question quality and provides detailed feedback
- Request Body:
  ```json
  {
    "question": "string",
    "metadata": {
      "tags": ["string"],
      "difficulty": "string"
    }
  }
  ```

3. **Generate Question**
- Endpoint: `/api/v1/questions/generate`
- Method: POST
- Description: Generates questions or variations based on tags or example
- Request Body:
  ```json
  {
    "type": "new|variation",
    "lesson": "string",
    "difficulty": "string",
    "example_question": "string"
  }
  ```

## Content Requirements

### DI-Style Articles
- Clear, concise explanations
- Step-by-step instruction
- Embedded worked examples
- Grade-appropriate vocabulary
- Consistent terminology
- Clear learning objectives
- Factually accurate content
- Properly formatted with visual elements
- Consistent explanations across related lessons

### Question Components
- Stimuli (optional passage/context)
- Images/diagrams (when applicable)
- Clear prompt
- Interaction type (MCQ/FRQ)
- Answer choices (for MCQ)
- Correct answer
- Wrong answer explanations
- Step-by-step solution
- Full explanation
- Grading criteria (for FRQ)

### Question Banks
- Minimum 100 questions per difficulty level
- Three difficulty tiers:
  - Easy: Basic comprehension
  - Medium: Application
  - Hard: Analysis and synthesis
- Varied question types
- Comprehensive coverage of lesson content
- Cannot be easily gamed
- Consistent with teaching articles
- Clear explanations for wrong answers
- Grade-appropriate language
- Proper formatting

## Development Approach

### Phase 0: Setup
1. Configure CCC database access
2. Set up QTI storage implementation
3. Initialize test harness framework

### Phase 1: Question Generator
1. Implement test harness
2. Develop QC system
3. Start with single lesson/difficulty
4. Achieve 99% precision
5. Expand to all difficulty levels
6. Scale to additional lessons

### Phase 2: Article Generator
1. Implement DI style templates
2. Develop worked examples
3. Integrate with question banks
4. Achieve 99% precision

### Phase 3: Integration
1. Combine articles and question banks
2. Implement lesson sequencing
3. Deploy complete system

## Quality Control

### Test Harness
- Store examples in QTI database
- Maintain good/bad example pairs
- Track precision metrics
- Automated regression testing
- Mutation testing for quality criteria
- Immediate feedback loop for failures

### QC System
- LLM-as-judge implementation
- Rubric-based assessment
- Immediate feedback loop
- Continuous improvement process
- Bootstrap with known good/bad examples
- Mutation testing for edge cases

### Quality Metrics
- Primary: 99%+ precision
- Secondary: Recall optimization
- Tracking: F1 score
- Continuous monitoring and improvement

### Error Handling
- Failed content added to test harness
- Automatic quality regression detection
- Systematic quality improvements
- Clear error feedback and suggestions

## Setup Instructions
1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure:
   ```
   OPENAI_API_KEY=your_key
   GPT_MODEL=gpt-4-turbo-preview
   SUPABASE_URL=your_url
   SUPABASE_KEY=your_key
   ```
6. Run the application: `uvicorn main:app --reload`

## Testing
- Run tests: `pytest`
- Run with coverage: `pytest --cov=app tests/`
- View test harness metrics: `python scripts/test_harness_metrics.py`

## Documentation
- API Documentation: `http://localhost:8000/docs`
- ReDoc Interface: `http://localhost:8000/redoc`

## Project Structure
```
.
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── articles.py
│   │   │   └── questions.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── article.py
│   │   │   └── question.py
│   │   ├── schemas/
│   │   │   ├── article.py
│   │   │   └── question.py
│   │   └── services/
│   │       ├── openai_service.py
│   │       ├── article_service.py
│   │       └── question_service.py
│   ├── tests/
│   │   ├── api/
│   │   ├── services/
│   │   └── conftest.py
│   ├── .env
│   ├── .gitignore
│   ├── main.py
│   └── README.md
```

## Development Guidelines
1. All new features should include appropriate tests
2. Follow PEP 8 style guidelines
3. Use type hints for better code maintainability
4. Include comprehensive docstrings for all functions and classes
5. Implement proper error handling and validation
6. Use environment variables for configuration

## Environment Variables
Required environment variables in `.env`:
```
# API Settings
API_VERSION=v1
API_TITLE="Educational Content Generation API"
API_DESCRIPTION="API for generating and managing educational content for K-8 students"
DEBUG=True

# OpenAI Settings
OPENAI_API_KEY=your_openai_api_key
GPT_MODEL=gpt-4-turbo-preview  # or gpt-4

# Supabase Settings
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SECRET_KEY=your_supabase_service_role_key

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Deployment
Deployment instructions for AWS EC2 will be added as the project progresses.

## API Documentation
Once the server is running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 

## Grade 4 Language Arts Curriculum

The curriculum for Grade 4 Language Arts is organized into three main categories:

### Reading Fundamentals (Start here to build core skills)
- Reading Fluency: Developing accuracy, appropriate reading rate, and expression when reading aloud and silently
- Vocabulary Acquisition: Learning strategies to determine meanings of unknown words and phrases
- Academic Vocabulary: Understanding domain-specific terminology and academic language used in texts
- Genre Studies: Recognizing and analyzing characteristics of different text types (poetry, drama, prose, informational)

### Reading Comprehension (Build on fundamentals with deeper analysis)
- Main Idea and Supporting Details: Identifying central messages and key details that support them
- Textual Details: Analyzing specific elements within text that contribute to meaning
- Text Structure and Organization: Recognizing different organizational patterns like chronology, cause/effect, and problem/solution
- Integration of Knowledge: Connecting and synthesizing information across multiple texts or sources
- Point of View: Distinguishing between first and third-person narrations and comparing different perspectives
- Character Analysis: Examining character traits, motivations, and development throughout texts
- Theme and Summary: Determining central themes and creating concise summaries of texts
- Figurative Language: Understanding metaphors, similes, idioms, and other non-literal language

### Language Conventions (Apply language skills to strengthen comprehension)
- Grammar and Usage: Understanding standard English grammar rules and applying them to reading contexts
- Capitalization and Punctuation: Recognizing proper use of capitals and punctuation marks in text
- Language Conventions: Mastering standard English usage rules including spelling patterns and word relationships

Each lesson includes DI-style articles with worked examples and comprehensive question banks with at least 100 questions per difficulty level (easy, medium, hard). 