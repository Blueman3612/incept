import os
import json
import requests
from typing import Dict, Any, List, Optional
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
GENERATE_ENDPOINT = f"{API_BASE_URL}/api/v1/questions/generate"
GRADE_ENDPOINT = f"{API_BASE_URL}/api/v1/questions/grade"


def parse_question_content(raw_content: str, lesson: str, difficulty: str) -> Dict[str, Any]:
    """
    Parse the raw question content into a structured format.
    Extracts components from the consistent question format.
    
    Args:
        raw_content: The raw content returned by the API
        lesson: The lesson name
        difficulty: The difficulty level
        
    Returns:
        A structured question dictionary
    """
    # Initialize components
    stimuli = ""
    prompt = ""
    answer_choices = {}
    correct_answer = ""
    wrong_answer_explanations = {}
    solution = ""
    full_explanation = ""
    
    # Split content into lines for processing
    lines = raw_content.strip().split('\n')
    
    # Track the current section being processed
    current_section = "preamble"  # Start with preamble (can be skipped)
    answer_section_lines = []
    wrong_explanation_lines = []
    solution_lines = []
    
    # Process each line to identify and extract components
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        # Skip empty lines
        if not stripped_line:
            continue
            
        # Identify section transitions
        if "Read the following" in stripped_line or "passage" in stripped_line and i < 3:
            current_section = "preamble"
            continue
            
        # Detect the prompt (the actual question)
        elif any(stripped_line.endswith(c) for c in ["?", "."]) and current_section in ["preamble", "stimuli"]:
            if current_section == "stimuli" and len(stimuli) > 0:
                prompt = stripped_line
                current_section = "prompt"
            elif current_section == "preamble":
                # If we haven't found a stimuli yet, this might be the start of it
                stimuli = stripped_line
                current_section = "stimuli"
            continue
                
        # Detect the start of answer choices
        elif stripped_line.startswith(("A)", "A.")) and current_section in ["stimuli", "prompt"]:
            current_section = "answers"
            answer_section_lines.append(stripped_line)
            continue
            
        # Detect the correct answer marker
        elif "Correct Answer:" in stripped_line or "The correct answer is" in stripped_line:
            current_section = "correct_answer"
            # Extract the letter of the correct answer
            if ":" in stripped_line:
                correct_part = stripped_line.split(":", 1)[1].strip()
                # Extract just the letter
                for letter in ["A", "B", "C", "D"]:
                    if letter in correct_part[:3]:  # Look in just the first few characters
                        correct_answer = letter
                        break
            continue
                
        # Detect wrong answer explanations
        elif "Explanation for wrong answers" in stripped_line or "Explanations for incorrect choices" in stripped_line:
            current_section = "wrong_explanations"
            continue
            
        # Detect the solution section
        elif stripped_line.startswith("Solution:"):
            current_section = "solution"
            continue
            
        # Process content based on current section
        if current_section == "stimuli":
            stimuli += stripped_line + " "
            
        elif current_section == "answers":
            answer_section_lines.append(stripped_line)
            
        elif current_section == "wrong_explanations":
            wrong_explanation_lines.append(stripped_line)
            
        elif current_section == "solution":
            solution_lines.append(stripped_line)
    
    # Process collected answer choices
    for line in answer_section_lines:
        for letter in ["A", "B", "C", "D"]:
            if line.startswith(f"{letter})") or line.startswith(f"{letter}."):
                answer_text = line.split(")", 1)[1].strip() if ")" in line else line.split(".", 1)[1].strip()
                answer_choices[letter] = answer_text
    
    # Process wrong answer explanations
    for line in wrong_explanation_lines:
        for letter in ["A", "B", "C", "D"]:
            if line.startswith(f"{letter})") or line.startswith(f"{letter}."):
                # This is a wrong answer explanation
                explanation = line.split(")", 1)[1].strip() if ")" in line else line.split(".", 1)[1].strip()
                wrong_answer_explanations[letter] = explanation
    
    # Join solution lines
    solution = " ".join(solution_lines).strip()
    if solution.startswith("Solution:"):
        solution = solution[9:].strip()  # Remove the "Solution:" prefix
    
    # If the wrong explanations aren't properly formatted by letter, try to structure them
    if not wrong_answer_explanations and wrong_explanation_lines:
        wrong_answer_text = " ".join(wrong_explanation_lines)
        full_explanation = wrong_answer_text
        
        # For each incorrect answer, try to find its explanation
        for letter in ["A", "B", "C", "D"]:
            if letter != correct_answer:
                letter_pattern = f"{letter})"
                if letter_pattern in wrong_answer_text:
                    try:
                        start_idx = wrong_answer_text.index(letter_pattern)
                        end_idx = -1
                        # Find the end of this explanation (start of next letter or end of text)
                        for next_letter in ["A", "B", "C", "D"]:
                            if next_letter != letter:
                                next_pattern = f"{next_letter})"
                                next_idx = wrong_answer_text.find(next_pattern, start_idx + 2)
                                if next_idx > -1 and (end_idx == -1 or next_idx < end_idx):
                                    end_idx = next_idx
                        
                        if end_idx == -1:  # This is the last explanation
                            explanation = wrong_answer_text[start_idx:].strip()
                        else:
                            explanation = wrong_answer_text[start_idx:end_idx].strip()
                            
                        wrong_answer_explanations[letter] = explanation
                    except Exception as e:
                        print(f"Error parsing wrong answer explanation for {letter}: {e}")
    
    # Combine wrong answer explanations and solution for full explanation
    full_explanation = "Wrong answer explanations: "
    for letter, explanation in wrong_answer_explanations.items():
        full_explanation += f"{letter}: {explanation}. "
    
    full_explanation += f"\nSolution: {solution}"
    
    # Clean up stimuli if it's the same as the prompt
    if stimuli and prompt and stimuli.strip() == prompt.strip():
        stimuli = ""
        
    # If stimuli is empty but there should be one, try to extract it from earlier in the content
    if not stimuli and "passage" in raw_content.lower():
        try:
            passage_start = raw_content.lower().find("passage")
            if passage_start > -1:
                # Find the next paragraph which is likely the stimuli
                next_para_start = raw_content.find("\n\n", passage_start)
                if next_para_start > -1:
                    next_para_end = raw_content.find("\n\n", next_para_start + 2)
                    if next_para_end > -1:
                        stimuli = raw_content[next_para_start:next_para_end].strip()
                    else:
                        # Maybe it's the rest of the content until the prompt
                        prompt_start = raw_content.find(prompt)
                        if prompt_start > -1:
                            stimuli = raw_content[next_para_start:prompt_start].strip()
        except Exception as e:
            print(f"Error extracting stimuli: {e}")
            
    # Fall back to the original parsing for the prompt if needed
    if not prompt:
        for line in lines[:15]:  # Look in first several lines
            if '?' in line and len(line) < 250:
                prompt = line.strip()
                break
    
    # Ensure we have a reasonable prompt
    if not prompt:
        prompt = f"Question about {lesson}"
        
    # Print extracted components for debugging
    print(f"Extracted prompt: {prompt[:50]}...")
    print(f"Extracted answer choices: {list(answer_choices.keys())}")
    print(f"Extracted correct answer: {correct_answer}")
    
    return {
        "content": raw_content[:5000],  # Keep the full content, limited to 5000 chars
        "lesson": lesson,
        "grade": 4,
        "course": "Language",
        "difficulty": difficulty,
        "interaction_type": "MCQ",
        "stimuli": stimuli.strip(),
        "prompt": prompt,
        "answer_choices": answer_choices,
        "correct_answer": correct_answer,
        "wrong_answer_explanations": wrong_answer_explanations,
        "solution": solution,
        "full_explanation": full_explanation,
        "status": "active"
    }


def generate_question(lesson: str, difficulty: str, additional_instructions: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a question using the API
    
    Args:
        lesson: The lesson name (e.g., "Reading Fluency")
        difficulty: Difficulty level (easy, medium, hard)
        additional_instructions: Optional additional instructions for generation
        
    Returns:
        The generated question data
    """
    payload = {
        "type": "new",
        "lesson": lesson,
        "difficulty": difficulty
    }
    
    if additional_instructions:
        payload["additional_instructions"] = additional_instructions
    
    print(f"Generating question for lesson: {lesson}, difficulty: {difficulty}...")
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(GENERATE_ENDPOINT, json=payload)
        
        # Print full response for debugging
        print(f"Response status code: {response.status_code}")
        
        # Try to parse as JSON for better error reporting
        try:
            response_data = response.json()
            print(f"Response data keys: {list(response_data.keys())}")
        except json.JSONDecodeError:
            print(f"Response is not JSON: {response.text[:500]}")
            response_data = {}
            
        if response.status_code != 200:
            print(f"Error generating question: {response.status_code}")
            print(response.text)
            raise Exception(f"Failed to generate question: {response.text[:500]}")
        
        # Parse the content into a structured question format
        if "content" in response_data:
            raw_content = response_data["content"]
            print(f"Received raw content of length: {len(raw_content)}")
            
            # Parse the raw content into a structured question
            return parse_question_content(raw_content, lesson, difficulty)
        else:
            print("Warning: Unknown response format. Using default structure.")
            return create_sample_question(lesson, difficulty)
            
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        raise


def create_sample_question(lesson: str, difficulty: str) -> Dict[str, Any]:
    """
    Create a sample question for testing when the API is not available
    
    Args:
        lesson: The lesson name
        difficulty: Difficulty level
        
    Returns:
        A sample question data dictionary
    """
    # Sample content matching the expected format for testing the parser
    if lesson == "Reading Fluency":
        return {
            "content": """Read the following passage and answer the question.

Clouds come in many types. There are three main kinds: cumulus, stratus, and cirrus. Cumulus clouds are puffy and white. They often look like cotton balls in the sky. Stratus clouds are flat and gray, often covering the whole sky. Cirrus clouds are thin and wispy, high up in the sky. All three types of clouds help predict the weather.

Is the following sentence a fact or an opinion: "Cumulus clouds are the most beautiful type of cloud."

A) Fact
B) Opinion
C) Neither a fact nor an opinion
D) Both a fact and an opinion

Correct Answer: B) Opinion

Explanation for wrong answers:
A) This is incorrect because the statement is not a proven truth that can be verified. It is based on personal preference.
B) This is the correct answer.
C) This is incorrect because the statement is expressing a viewpoint, which makes it an opinion.
D) This is incorrect because the statement cannot be both a fact and an opinion. It is an opinion, not a factual statement that can be proven true or false.

Solution:
1. Read the question carefully.
2. Understand that a fact is a statement that can be proven true or false, while an opinion is a personal viewpoint or feeling.
3. Apply this understanding to the statement "Cumulus clouds are the most beautiful type of cloud."
4. Determine that this statement is an opinion because it is based on personal preference and cannot be proven true or false.""",
            "lesson": lesson,
            "grade": 4,
            "course": "Language",
            "difficulty": difficulty,
            "interaction_type": "MCQ",
            "stimuli": "Clouds come in many types. There are three main kinds: cumulus, stratus, and cirrus. Cumulus clouds are puffy and white. They often look like cotton balls in the sky. Stratus clouds are flat and gray, often covering the whole sky. Cirrus clouds are thin and wispy, high up in the sky. All three types of clouds help predict the weather.",
            "prompt": "Is the following sentence a fact or an opinion: \"Cumulus clouds are the most beautiful type of cloud.\"",
            "answer_choices": {
                "A": "Fact",
                "B": "Opinion", 
                "C": "Neither a fact nor an opinion", 
                "D": "Both a fact and an opinion"
            },
            "correct_answer": "B",
            "wrong_answer_explanations": {
                "A": "This is incorrect because the statement is not a proven truth that can be verified. It is based on personal preference.",
                "C": "This is incorrect because the statement is expressing a viewpoint, which makes it an opinion.",
                "D": "This is incorrect because the statement cannot be both a fact and an opinion. It is an opinion, not a factual statement that can be proven true or false."
            },
            "solution": "1. Read the question carefully. 2. Understand that a fact is a statement that can be proven true or false, while an opinion is a personal viewpoint or feeling. 3. Apply this understanding to the statement \"Cumulus clouds are the most beautiful type of cloud.\" 4. Determine that this statement is an opinion because it is based on personal preference and cannot be proven true or false.",
            "full_explanation": "The statement \"Cumulus clouds are the most beautiful type of cloud\" is an opinion because it expresses a subjective judgment about beauty, which is based on personal preference and cannot be proven true or false.",
            "status": "active"
        }
    else:
        # For other lessons, create a generic sample
        return {
            "content": f"Sample question for {lesson} at {difficulty} difficulty. This is a question to test reading comprehension. What is the main idea?\n\nA) First option\nB) Second option\nC) Third option\nD) Fourth option\n\nCorrect Answer: A\n\nExplanation for wrong answers:\nB) This is incorrect because...\nC) This is incorrect because...\nD) This is incorrect because...\n\nSolution:\nThe correct approach is to identify the main idea by...",
            "lesson": lesson,
            "grade": 4,
            "course": "Language",
            "difficulty": difficulty,
            "interaction_type": "MCQ",
            "stimuli": f"Sample passage for testing {lesson} comprehension. This is a short paragraph that covers key concepts in {lesson}.",
            "prompt": f"What is the main idea of the {lesson} passage?",
            "answer_choices": {
                "A": "First option",
                "B": "Second option", 
                "C": "Third option", 
                "D": "Fourth option"
            },
            "correct_answer": "A",
            "wrong_answer_explanations": {
                "B": "This is incorrect because...",
                "C": "This is incorrect because...",
                "D": "This is incorrect because..."
            },
            "solution": "The correct approach is to identify the main idea by...",
            "full_explanation": "A detailed explanation of the correct answer and why the others are wrong.",
            "status": "active"
        }


def upload_to_supabase(question_data: Dict[str, Any]) -> str:
    """
    Upload a question to Supabase
    
    Args:
        question_data: The question data to upload
        
    Returns:
        The ID of the inserted question
    """
    print("Uploading question to Supabase...")
    print(f"Question data structure: {json.dumps(list(question_data.keys()), indent=2)}")
    
    # Ensure the required fields are present
    required_fields = ["content", "lesson", "difficulty", "interaction_type", 
                       "prompt", "correct_answer", "solution", "full_explanation"]
    
    # Check if required fields are missing
    missing_fields = [field for field in required_fields if field not in question_data]
    if missing_fields:
        print(f"Warning: Missing required fields: {missing_fields}")
        
        # For testing purposes, add missing fields with placeholder values
        for field in missing_fields:
            if field == "content":
                question_data[field] = f"Sample content for {question_data.get('lesson', 'unknown lesson')}"
            elif field == "interaction_type":
                question_data[field] = "MCQ"
            else:
                question_data[field] = f"Placeholder for {field}"
    
    try:
        # Insert the question into Supabase
        result = supabase.table("questions").insert(question_data).execute()
        
        if hasattr(result, 'error') and result.error is not None:
            print(f"Error uploading question: {result.error}")
            raise Exception(f"Failed to upload question: {result.error}")
        
        if hasattr(result, 'data') and result.data and len(result.data) > 0:
            inserted_id = result.data[0].get('id')
            print(f"Question uploaded successfully with ID: {inserted_id}")
            return inserted_id
        else:
            print(f"Warning: No data returned from Supabase: {result}")
            return "unknown_id"
    except Exception as e:
        print(f"Exception during Supabase upload: {str(e)}")
        raise


def generate_and_upload_batch(lesson: str, difficulty: str, count: int = 5, use_sample: bool = False) -> List[str]:
    """
    Generate and upload a batch of questions
    
    Args:
        lesson: The lesson name
        difficulty: Difficulty level
        count: Number of questions to generate
        use_sample: Whether to use sample questions instead of calling the API
        
    Returns:
        List of inserted question IDs
    """
    question_ids = []
    
    for i in range(count):
        try:
            # Generate the question
            if use_sample:
                question_data = create_sample_question(lesson, difficulty)
                print(f"Created sample question for {lesson}, difficulty: {difficulty}")
            else:
                question_data = generate_question(lesson, difficulty)
            
            # Upload to Supabase
            question_id = upload_to_supabase(question_data)
            question_ids.append(question_id)
            
            print(f"Completed {i+1}/{count} questions")
            
            # Add a small delay to avoid rate limiting
            if i < count - 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"Error processing question {i+1}: {str(e)}")
    
    return question_ids


if __name__ == "__main__":
    # Configuration for our batch
    lesson = "Reading Fluency"
    difficulty = "easy"
    batch_size = 5  # Generate 5 questions per difficulty level
    use_sample = False  # Use real API calls
    
    print(f"Starting generation and upload of {batch_size} questions for {lesson} at {difficulty} difficulty")
    print(f"Using sample questions: {use_sample}")
    
    # Generate and upload questions for easy difficulty
    easy_ids = generate_and_upload_batch(lesson, difficulty, batch_size, use_sample)
    print(f"Successfully generated and uploaded {len(easy_ids)} easy questions")
    print(f"Question IDs: {easy_ids}")
    
    # Generate medium difficulty questions
    print("\nGenerating medium difficulty questions...")
    medium_ids = generate_and_upload_batch(lesson, "medium", batch_size, use_sample)
    print(f"Successfully generated and uploaded {len(medium_ids)} medium questions")
    
    # Generate hard difficulty questions
    print("\nGenerating hard difficulty questions...")
    hard_ids = generate_and_upload_batch(lesson, "hard", batch_size, use_sample)
    print(f"Successfully generated and uploaded {len(hard_ids)} hard questions")
    
    # Summary
    total_questions = len(easy_ids) + len(medium_ids) + len(hard_ids)
    print(f"\nTotal questions generated and uploaded: {total_questions}")
    print(f"Easy: {len(easy_ids)}, Medium: {len(medium_ids)}, Hard: {len(hard_ids)}") 