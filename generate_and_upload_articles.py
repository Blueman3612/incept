import os
import json
import time
import argparse
import requests
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase_secret_key = os.environ.get("SUPABASE_SECRET_KEY")  # Get service role key

# Use service key for operations that require elevated permissions
supabase: Client = create_client(supabase_url, supabase_secret_key or supabase_key)

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
GENERATE_ENDPOINT = f"{API_BASE_URL}/api/v1/articles/generate"
GRADE_ENDPOINT = f"{API_BASE_URL}/api/v1/articles/grade"


def get_lesson_description(lesson: str) -> Optional[str]:
    """
    Get the detailed description for a specific lesson based on PROJECT.md curriculum.
    
    Args:
        lesson: The name of the lesson
        
    Returns:
        The lesson description or None if not found
    """
    # Map of lesson names to their descriptions
    lesson_descriptions = {
        # Reading Fundamentals
        "Reading Fluency": "Developing accuracy, appropriate reading rate, and expression when reading aloud and silently",
        "Vocabulary Acquisition": "Learning strategies to determine meanings of unknown words and phrases",
        "Academic Vocabulary": "Understanding domain-specific terminology and academic language used in texts",
        "Genre Studies": "Recognizing and analyzing characteristics of different text types (poetry, drama, prose, informational)",
        
        # Reading Comprehension
        "Main Idea and Supporting Details": "Identifying central messages and key details that support them",
        "Textual Details": "Analyzing specific elements within text that contribute to meaning",
        "Text Structure and Organization": "Recognizing different organizational patterns like chronology, cause/effect, and problem/solution",
        "Integration of Knowledge": "Connecting and synthesizing information across multiple texts or sources",
        "Point of View": "Distinguishing between first and third-person narrations and comparing different perspectives",
        "Character Analysis": "Examining character traits, motivations, and development throughout texts",
        "Theme and Summary": "Determining central themes and creating concise summaries of texts",
        "Figurative Language": "Understanding metaphors, similes, idioms, and other non-literal language",
        
        # Language Conventions
        "Grammar and Usage": "Understanding standard English grammar rules and applying them to reading contexts",
        "Capitalization and Punctuation": "Recognizing proper use of capitals and punctuation marks in text",
        "Language Conventions": "Mastering standard English usage rules including spelling patterns and word relationships"
    }
    
    return lesson_descriptions.get(lesson)


def get_standard_for_lesson(lesson: str) -> str:
    """
    Get the appropriate Common Core standard for a given lesson.
    
    Args:
        lesson: The name of the lesson
        
    Returns:
        The corresponding CCSS standard
    """
    # This is a simplified mapping - in a real implementation, 
    # this would be more comprehensive and possibly stored in a database
    standards_mapping = {
        # Reading Fundamentals
        "Reading Fluency": "CCSS.ELA-LITERACY.RF.4.4",
        "Vocabulary Acquisition": "CCSS.ELA-LITERACY.RI.4.4",
        "Academic Vocabulary": "CCSS.ELA-LITERACY.L.4.4",
        "Genre Studies": "CCSS.ELA-LITERACY.RL.4.5",
        
        # Reading Comprehension
        "Main Idea and Supporting Details": "CCSS.ELA-LITERACY.RI.4.2",
        "Textual Details": "CCSS.ELA-LITERACY.RL.4.1",
        "Text Structure and Organization": "CCSS.ELA-LITERACY.RI.4.5",
        "Integration of Knowledge": "CCSS.ELA-LITERACY.RI.4.9",
        "Point of View": "CCSS.ELA-LITERACY.RL.4.6",
        "Character Analysis": "CCSS.ELA-LITERACY.RL.4.3",
        "Theme and Summary": "CCSS.ELA-LITERACY.RL.4.2",
        "Figurative Language": "CCSS.ELA-LITERACY.L.4.5",
        
        # Language Conventions
        "Grammar and Usage": "CCSS.ELA-LITERACY.L.4.1",
        "Capitalization and Punctuation": "CCSS.ELA-LITERACY.L.4.2",
        "Language Conventions": "CCSS.ELA-LITERACY.L.4.3"
    }
    
    return standards_mapping.get(lesson, "CCSS.ELA-LITERACY.RL.4")


def parse_article_content(raw_content: str, lesson: str) -> Dict[str, Any]:
    """
    Parse the raw article content from API response into a structured format.
    
    Args:
        raw_content: Raw article content from generation API
        lesson: The lesson the article is for
        
    Returns:
        Structured article data
    """
    try:
        # If the content is already in JSON format, parse it
        if isinstance(raw_content, dict):
            article_data = raw_content
        else:
            # Try to convert from string to JSON
            article_data = json.loads(raw_content)
        
        # Add metadata
        article_data["lesson"] = lesson
        article_data["standard"] = get_standard_for_lesson(lesson)
        article_data["subject"] = "Language Arts"
        article_data["grade"] = 4
        
        return article_data
    except json.JSONDecodeError:
        # If not JSON, assume it's plain text and structure it
        return {
            "title": f"Grade 4 Language Arts: {lesson}",
            "content": raw_content,
            "lesson": lesson,
            "standard": get_standard_for_lesson(lesson),
            "subject": "Language Arts",
            "grade": 4
        }


def generate_article(lesson: str, additional_instructions: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an article using the API.
    
    Args:
        lesson: The lesson to generate an article for
        additional_instructions: Optional instructions for the generator
        
    Returns:
        The generated article data
    """
    print(f"Generating article for lesson: {lesson}")
    
    # Get lesson description
    lesson_description = get_lesson_description(lesson)
    standard = get_standard_for_lesson(lesson)
    
    # Prepare request data
    request_data = {
        "lesson": lesson,
        "standard": standard,
        "course": "Language",
        "grade_level": 4,
        "additional_instructions": additional_instructions or ""
    }
    
    if lesson_description:
        # Add lesson description to additional instructions
        if request_data["additional_instructions"]:
            request_data["additional_instructions"] += f" Lesson description: {lesson_description}"
        else:
            request_data["additional_instructions"] = f"Lesson description: {lesson_description}"
    
    try:
        # Call the generate endpoint
        response = requests.post(
            GENERATE_ENDPOINT,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Success codes: 200 OK or 201 Created
        if response.status_code in [200, 201]:
            # For debugging
            print(f"Successfully generated article with status code: {response.status_code}")
            
            result = response.json()
            
            # Fields we want to keep from the API response
            allowed_fields = [
                "title", "content", "lesson", "standard", "subject", "grade",
                "status", "quality_score", "feedback", "examples", "key_concepts"
            ]
            
            # If the response is already the article data, use it directly
            if "title" in result and "content" in result:
                # Filter to only needed fields
                filtered_result = {k: v for k, v in result.items() if k in allowed_fields}
                
                # Add lesson and standard if not present
                if "lesson" not in filtered_result:
                    filtered_result["lesson"] = lesson
                if "standard" not in filtered_result:
                    filtered_result["standard"] = standard
                    
                return filtered_result
            
            # Otherwise, parse content from the response
            if "content" in result:
                raw_content = result.get("content", "")
                return parse_article_content(raw_content, lesson)
            else:
                # If neither format matches, return filtered result with required fields
                filtered_result = {k: v for k, v in result.items() if k in allowed_fields}
                filtered_result["lesson"] = lesson
                filtered_result["standard"] = standard
                return filtered_result
        else:
            print(f"Error generating article: {response.status_code} - {response.text}")
            return {"error": f"Failed to generate article: {response.text}"}
    
    except Exception as e:
        print(f"Exception while generating article: {str(e)}")
        return {"error": str(e)}


def grade_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade an article using the API.
    
    Args:
        article_data: The article data to grade
        
    Returns:
        Grading results
    """
    try:
        # Prepare request data
        request_data = {
            "content": article_data.get("content", ""),
            "metadata": {
                "tags": [article_data.get("lesson", ""), article_data.get("standard", "")],
                "grade_level": 4,
                "subject": "Language",
                "course": "Language Grade 4"
            }
        }
        
        # Call the grade endpoint
        response = requests.post(
            GRADE_ENDPOINT,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error grading article: {response.status_code} - {response.text}")
            return {
                "passed": False,
                "score": 0,
                "feedback": f"Error: {response.text}",
                "details": {}
            }
    
    except Exception as e:
        print(f"Exception while grading article: {str(e)}")
        return {
            "passed": False,
            "score": 0,
            "feedback": f"Error: {str(e)}",
            "details": {}
        }


def upload_to_supabase(article_data: Dict[str, Any]) -> str:
    """
    Upload an article to Supabase.
    
    Args:
        article_data: The article data to upload
        
    Returns:
        The ID of the uploaded article
    """
    try:
        # Remove any error keys
        if "error" in article_data:
            del article_data["error"]
        
        # Define allowed fields based on our table schema
        allowed_fields = [
            "title", "content", "lesson", "standard", "subject", "grade",
            "status", "quality_score", "feedback", "created_at", "updated_at"
        ]
        
        # Filter to only include fields that exist in our table
        filtered_data = {k: v for k, v in article_data.items() if k in allowed_fields}
        
        # Ensure required fields are present
        required_fields = {
            "title": article_data.get("title", f"Grade 4 Language: {article_data.get('lesson', 'Lesson')}"),
            "content": article_data.get("content", ""),
            "lesson": article_data.get("lesson", ""),
            "standard": article_data.get("standard", ""),
            "subject": article_data.get("subject", "Language"),
            "grade": article_data.get("grade", 4),
            "status": article_data.get("status", "draft")
        }
        
        # Merge required fields with filtered data
        upload_data = {**required_fields, **filtered_data}
        
        # Print the data being sent to Supabase for debugging
        print(f"Uploading article with title: {upload_data.get('title')}")
        
        # Insert into Supabase
        result = supabase.table("articles").insert(upload_data).execute()
        
        # Extract and return the article ID
        if result.data and len(result.data) > 0:
            return result.data[0].get("id")
        else:
            print("Warning: No ID returned from Supabase insert")
            print(f"Supabase response: {result}")
            return "unknown_id"
    
    except Exception as e:
        print(f"Exception while uploading to Supabase: {str(e)}")
        return f"error: {str(e)}"


def generate_and_upload_article(lesson: str, additional_instructions: Optional[str] = None) -> str:
    """
    Generate an article and upload it to Supabase.
    
    Args:
        lesson: The lesson to generate an article for
        additional_instructions: Optional instructions for the generator
        
    Returns:
        The ID of the uploaded article
    """
    # Generate the article
    article_data = generate_article(lesson, additional_instructions)
    
    if "error" in article_data:
        print(f"Failed to generate article: {article_data['error']}")
        return f"error: {article_data['error']}"
    
    # Grade the article if it wasn't already graded
    if "quality_score" not in article_data or "feedback" not in article_data:
        grade_result = grade_article(article_data)
        
        # Add grading results
        article_data["quality_score"] = grade_result.get("score", 0)
        article_data["feedback"] = grade_result.get("feedback", "")
        article_data["status"] = "ready" if grade_result.get("passed", False) else "needs_revision"
    
    # Upload to Supabase
    article_id = upload_to_supabase(article_data)
    
    print(f"Article generated and uploaded with ID: {article_id}")
    return article_id


def get_available_lessons() -> List[str]:
    """
    Get the list of available lessons for Grade 4 Language Arts.
    
    Returns:
        List of lesson names
    """
    return [
        # Reading Fundamentals
        "Reading Fluency",
        "Vocabulary Acquisition",
        "Academic Vocabulary",
        "Genre Studies",
        
        # Reading Comprehension
        "Main Idea and Supporting Details",
        "Textual Details",
        "Text Structure and Organization",
        "Integration of Knowledge",
        "Point of View",
        "Character Analysis",
        "Theme and Summary",
        "Figurative Language",
        
        # Language Conventions
        "Grammar and Usage",
        "Capitalization and Punctuation",
        "Language Conventions"
    ]


def main():
    parser = argparse.ArgumentParser(description="Generate and upload articles for Grade 4 Language Arts")
    parser.add_argument(
        "--lesson", 
        type=str, 
        choices=get_available_lessons(),
        help="Specific lesson to generate an article for"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate articles for all available lessons"
    )
    parser.add_argument(
        "--instructions",
        type=str,
        default=None,
        help="Additional instructions for the article generator"
    )
    
    args = parser.parse_args()
    
    if args.all:
        print("Generating articles for all lessons...")
        lessons = get_available_lessons()
        article_ids = []
        
        for lesson in lessons:
            print(f"\n=== Generating article for: {lesson} ===")
            article_id = generate_and_upload_article(lesson, args.instructions)
            article_ids.append(article_id)
            # Add a short delay between requests to avoid rate limiting
            time.sleep(2)
        
        print("\nCompleted generating all articles!")
        print(f"Generated {len(article_ids)} articles")
    
    elif args.lesson:
        article_id = generate_and_upload_article(args.lesson, args.instructions)
        print(f"Article ID: {article_id}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 