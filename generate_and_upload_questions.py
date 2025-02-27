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
    
    # Check for exact match first
    if lesson in lesson_descriptions:
        return lesson_descriptions[lesson]
    
    # If no exact match, try case-insensitive matching
    for key, description in lesson_descriptions.items():
        if key.lower() == lesson.lower():
            return description
    
    # If still no match, check if any key contains the lesson name (or vice versa)
    for key, description in lesson_descriptions.items():
        if lesson.lower() in key.lower() or key.lower() in lesson.lower():
            return description
    
    # No match found
    print(f"Warning: No description found for lesson '{lesson}'")
    return None


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
    
    # Print the raw content for debugging (first few lines)
    content_preview = "\n".join(raw_content.split("\n")[:10])
    print(f"Parsing raw content (preview):\n{content_preview}...")
    
    # Split content into lines for processing
    lines = raw_content.strip().split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    # Try to identify standard patterns first - most questions follow a standard format
    
    # Pattern 1: Content starts with "Read the following passage" followed by the passage in quotation marks
    passage_marker_indices = []
    for i, line in enumerate(non_empty_lines):
        if "passage" in line.lower() and "read" in line.lower():
            passage_marker_indices.append(i)
            
    if passage_marker_indices:
        # Found a passage marker, look for the passage (usually in quotes or in the next paragraph)
        marker_idx = passage_marker_indices[0]
        
        # Check if the passage is in quotes in the next line
        if marker_idx + 1 < len(non_empty_lines):
            next_line = non_empty_lines[marker_idx + 1]
            if next_line.startswith('"') or next_line.startswith('"'):
                # Extract the passage which might span multiple lines
                passage_text = []
                quote_type = '"' if next_line.startswith('"') else '"'
                in_passage = True
                
                for j in range(marker_idx + 1, len(non_empty_lines)):
                    line = non_empty_lines[j]
                    if in_passage:
                        passage_text.append(line)
                        if line.endswith(quote_type) or line.endswith('"'):
                            in_passage = False
                            # Look for the question after the passage
                            for k in range(j + 1, len(non_empty_lines)):
                                question_line = non_empty_lines[k]
                                if '?' in question_line:
                                    prompt = question_line.strip()
                                    # Now find answer choices after the prompt
                                    answer_start_idx = k + 1
                                    break
                
                stimuli = ' '.join(passage_text)
                # Clean up quotes
                stimuli = stimuli.strip('"').strip('"').strip()
    
    # If we still don't have the stimuli and prompt, try another approach
    if not stimuli or not prompt:
        # Look for the standard question format: stimuli followed by prompt followed by options
        for i, line in enumerate(non_empty_lines):
            if '?' in line and i > 0 and not prompt:
                # This line contains a question mark - likely the prompt
                prompt = line.strip()
                # Everything before this line might be the stimuli
                potential_stimuli = ' '.join(non_empty_lines[:i])
                
                # Don't include headers like "Read the following passage" in the stimuli
                skip_headers = ["read the following", "passage", "answer the question"]
                first_line = non_empty_lines[0].lower()
                
                if any(header in first_line for header in skip_headers) and len(non_empty_lines) > 1:
                    potential_stimuli = ' '.join(non_empty_lines[1:i])
                
                stimuli = potential_stimuli.strip()
                break
    
    # Find answer choices - look for A), B), C), D) pattern or A., B., C., D. pattern
    answer_section_start = -1
    
    # Loop through lines to find where answer choices begin
    for i, line in enumerate(non_empty_lines):
        stripped_line = line.strip()
        # Look for common answer choice patterns
        if (stripped_line.startswith(("A)", "A.")) or 
            stripped_line.startswith("A ") or 
            (stripped_line == "A" and i + 1 < len(non_empty_lines) and non_empty_lines[i+1].strip().startswith(")"))):
            answer_section_start = i
            break
    
    # If we found the start of answer choices
    if answer_section_start != -1:
        # Process answer choices - allow different formats
        choice_lines = []
        
        i = answer_section_start
        while i < len(non_empty_lines):
            line = non_empty_lines[i].strip()
            
            # Stop collecting answer choices when we hit the correct answer or explanation sections
            if any(marker in line.lower() for marker in ["correct answer", "explanation", "solution"]):
                break
                
            choice_lines.append(line)
            i += 1
        
        # Process the collected answer choice lines
        current_letter = None
        current_text = []
        
        for line in choice_lines:
            # Check for new answer choice
            for letter in ["A", "B", "C", "D"]:
                if (line.startswith(f"{letter})") or 
                    line.startswith(f"{letter}.") or 
                    line.startswith(f"{letter} ") or 
                    line == letter):
                    
                    # Save the previous answer choice if there was one
                    if current_letter and current_text:
                        answer_choices[current_letter] = " ".join(current_text).strip()
                        current_text = []
                    
                    # Start a new answer choice
                    current_letter = letter
                    
                    # Extract the text after the letter/punctuation
                    if ")" in line:
                        text = line.split(")", 1)[1].strip()
                    elif "." in line[:2]:  # Only check first two chars to avoid capturing sentences
                        text = line.split(".", 1)[1].strip()
                    elif line.startswith(f"{letter} "):
                        text = line[2:].strip()
                    else:
                        text = ""  # Letter only, content is in the next line
                        
                    if text:
                        current_text.append(text)
                    break
            else:
                # If no letter prefix found, continue the current answer choice
                if current_letter:
                    current_text.append(line)
        
        # Add the last answer choice
        if current_letter and current_text:
            answer_choices[current_letter] = " ".join(current_text).strip()
    
    # Process the correct answer
    for i, line in enumerate(non_empty_lines):
        stripped_line = line.lower().strip()
        if "correct answer" in stripped_line or "the correct answer is" in stripped_line:
            # Extract the letter of the correct answer using more precise patterns
            
            # Look for patterns like "Correct Answer: B" or "The correct answer is C"
            if ":" in line:
                parts = line.split(":", 1)
                answer_part = parts[1].strip()
                
                # Check if the first character is a letter (A, B, C, D)
                if answer_part and answer_part[0] in ["A", "B", "C", "D"]:
                    correct_answer = answer_part[0]
                    break
                    
                # Check for patterns like "B)" or "C."
                for letter in ["A", "B", "C", "D"]:
                    if answer_part.startswith(f"{letter})") or answer_part.startswith(f"{letter}."):
                        correct_answer = letter
                        break
                    
            # Try to find patterns with explicit mentions like "Answer B is correct"
            if not correct_answer:
                for letter in ["A", "B", "C", "D"]:
                    # Look for patterns where the letter is followed by specific delimiters
                    # to avoid matching A in "Answer"
                    if f" {letter})" in line or f" {letter}." in line or f" {letter} " in line:
                        correct_answer = letter
                        break
            break
    
    # If we still don't have a correct answer but have answer choices
    if not correct_answer and answer_choices:
        # Check for other instances of "correct" near option letters in the content
        for i, line in enumerate(non_empty_lines):
            if "correct" in line.lower():
                for letter in ["A", "B", "C", "D"]:
                    # Look for letter at the beginning of the line or after clear delimiters
                    if (line.strip().startswith(f"{letter})") or 
                        line.strip().startswith(f"{letter}.") or 
                        f" {letter})" in line or 
                        f" {letter}." in line):
                        correct_answer = letter
                        break
    
    # If we have answer choices but no prompt, and the stimuli might contain the prompt
    if answer_choices and not prompt and stimuli:
        # Try to find the prompt at the end of the stimuli
        lines = stimuli.split(". ")
        if len(lines) > 1 and "?" in lines[-1]:
            prompt = lines[-1].strip()
            # Remove the prompt from the stimuli
            stimuli = ". ".join(lines[:-1]) + "."
    
    # Process wrong answer explanations
    explanation_section_start = -1
    for i, line in enumerate(non_empty_lines):
        if "explanation for wrong" in line.lower() or "explanations for incorrect" in line.lower():
            explanation_section_start = i
            break
    
    if explanation_section_start != -1:
        # Process wrong answer explanations
        i = explanation_section_start + 1
        current_letter = None
        current_explanation = []
        
        while i < len(non_empty_lines):
            line = non_empty_lines[i].strip()
            
            # Stop at solution section
            if "solution" in line.lower() and (":" in line or i == 0 or non_empty_lines[i-1].strip() == ""):
                break
                
            # Check for new explanation
            for letter in ["A", "B", "C", "D"]:
                if line.startswith(f"{letter})") or line.startswith(f"{letter}."):
                    # Save the previous explanation if there was one
                    if current_letter and current_explanation:
                        wrong_answer_explanations[current_letter] = " ".join(current_explanation).strip()
                        current_explanation = []
                    
                    # Start a new explanation
                    current_letter = letter
                    
                    # Extract the text after the letter/punctuation
                    if ")" in line:
                        text = line.split(")", 1)[1].strip()
                    elif "." in line[:2]:
                        text = line.split(".", 1)[1].strip()
                    else:
                        text = ""
                        
                    if text:
                        current_explanation.append(text)
                    break
            else:
                # If no letter prefix found, continue the current explanation
                if current_letter:
                    current_explanation.append(line)
            
            i += 1
        
        # Add the last explanation
        if current_letter and current_explanation:
            wrong_answer_explanations[current_letter] = " ".join(current_explanation).strip()
    
    # Process solution
    solution_section_start = -1
    for i, line in enumerate(non_empty_lines):
        if line.lower().startswith("solution:") or line.lower() == "solution":
            solution_section_start = i
            break
    
    if solution_section_start != -1:
        # Gather all lines after "Solution:" until the end or next major section
        solution_lines = []
        i = solution_section_start
        
        # Skip the "Solution:" line itself
        if ":" in non_empty_lines[i]:
            solution_text = non_empty_lines[i].split(":", 1)[1].strip()
            if solution_text:
                solution_lines.append(solution_text)
        else:
            i += 1  # Skip the "Solution" header
            
        # Gather all remaining solution lines
        while i + 1 < len(non_empty_lines):
            i += 1
            line = non_empty_lines[i].strip()
            # Stop if we hit another section
            if any(line.lower().startswith(s) for s in ["full explanation:", "notes:", "additional information:"]):
                break
            solution_lines.append(line)
        
        solution = " ".join(solution_lines).strip()
    
    # Clean up and validate our extracted components
    
    # Ensure prompt is properly identified
    if not prompt:
        for line in non_empty_lines:
            if '?' in line and len(line) < 250:
                prompt = line.strip()
                break
    
    # If we still don't have a prompt, make a reasonable guess
    if not prompt:
        prompt = f"Question about {lesson}"
    
    # Ensure correct_answer is properly set
    if not correct_answer and answer_choices:
        # If there are explanations that indicate correct answer
        for line in non_empty_lines:
            if "correct answer" in line.lower():
                for letter in ["A", "B", "C", "D"]:
                    if f"{letter}" in line:
                        correct_answer = letter
                        break
    
    # Clean up stimuli if it's actually just repeating the prompt
    if stimuli and prompt and stimuli.strip() == prompt.strip():
        stimuli = ""
    
    # Combine wrong answer explanations and solution for full explanation
    full_explanation = ""
    if wrong_answer_explanations:
        full_explanation = "Wrong answer explanations: "
        for letter, explanation in wrong_answer_explanations.items():
            full_explanation += f"{letter}: {explanation}. "
    
    if solution:
        full_explanation += f"\nSolution: {solution}"
    
    # Print parsing results for debugging
    print(f"Parsing results:")
    print(f"Stimuli: {stimuli[:50]}{'...' if len(stimuli) > 50 else ''}")
    print(f"Prompt: {prompt}")
    print(f"Answer choices: {list(answer_choices.keys())}")
    print(f"Correct answer: {correct_answer}")
    
    # Return the structured question data
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
    Generate a question using the 'generate' endpoint.
    
    Args:
        lesson: The lesson name
        difficulty: The difficulty level (easy, medium, hard)
        additional_instructions: Any additional instructions for generation
        
    Returns:
        Dict containing the question data
    """
    if os.getenv("USE_SAMPLE", "False").lower() == "true":
        print(f"Using sample question for {lesson} at {difficulty} difficulty")
        return create_sample_question(lesson, difficulty)
    
    url = f"{API_BASE_URL}/api/v1/questions/generate"
    
    # Get the lesson description
    lesson_description = get_lesson_description(lesson)
    if lesson_description:
        print(f"Using lesson description: {lesson_description}")
    
    payload = {
        "type": "new",
        "lesson": lesson,
        "difficulty": difficulty
    }
    
    # Add the lesson description if available
    if lesson_description:
        payload["lesson_description"] = lesson_description
    
    if additional_instructions:
        payload["additional_instructions"] = additional_instructions
    
    print(f"Sending payload to API: {payload}")
    
    # Set up retry parameters
    max_retries = 5
    retry_count = 0
    backoff_factor = 2
    initial_wait = 1
    
    while retry_count < max_retries:
        try:
            # Add timeout parameter to prevent hanging requests
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 429:
                # API rate limit hit - implement exponential backoff
                wait_time = initial_wait * (backoff_factor ** retry_count)
                print(f"Rate limit hit, waiting for {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                retry_count += 1
                continue
                
            response.raise_for_status()  # Raise exception for 4XX/5XX status codes
            
            # Process the successful response
            if response.headers.get('content-type') == 'application/json':
                data = response.json()
                if "question" in data:
                    return data["question"]
                elif "content" in data:
                    return parse_question_content(data["content"], lesson, difficulty)
                else:
                    print(f"Unexpected API response format: {data}")
                    return parse_question_content(str(data), lesson, difficulty)
            else:
                raw_content = response.text
                print(f"API returned raw content of length {len(raw_content)}")
                return parse_question_content(raw_content, lesson, difficulty)
                
        except requests.exceptions.Timeout:
            wait_time = initial_wait * (backoff_factor ** retry_count)
            print(f"Request timed out, waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            retry_count += 1
            
        except requests.exceptions.RequestException as e:
            wait_time = initial_wait * (backoff_factor ** retry_count)
            print(f"API request error: {e}. Waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            retry_count += 1
    
    # If we get here, all retries failed
    print("Maximum retries reached. Using sample question instead.")
    return create_sample_question(lesson, difficulty)


def create_sample_question(lesson: str, difficulty: str) -> Dict[str, Any]:
    """
    Create a sample question for testing when the API is not available
    
    Args:
        lesson: The lesson name
        difficulty: Difficulty level
        
    Returns:
        A sample question data dictionary
    """
    # Get lesson description for more context-aware samples
    lesson_description = get_lesson_description(lesson)
    
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
    elif lesson == "Main Idea and Supporting Details" and lesson_description:
        return {
            "content": f"""Read the following passage and answer the question.

The school garden project has been a big success this year. Students planted vegetables in the spring. Throughout summer, they took turns watering the plants. By fall, they harvested tomatoes, carrots, and lettuce. The vegetables were used in the school cafeteria. Teachers said it was a great way for students to learn about plant growth and healthy eating.

What is the main idea of this passage?

A) Students planted vegetables in the spring.
B) The school garden project was successful and educational.
C) Vegetables from the garden were used in the cafeteria.
D) Teachers thought the garden was a good learning experience.

Correct Answer: B

Explanation for wrong answers:
A) This is incorrect because it only mentions one detail from the passage (planting in spring) rather than the central message.
C) This is incorrect because it focuses on just one supporting detail about how the vegetables were used, not the main point of the passage.
D) This is incorrect because the teachers' opinions are just one supporting detail, not the main idea of the entire passage.

Solution:
1. Read the entire passage carefully.
2. Identify what the passage is mainly about (the school garden project's success).
3. Determine which sentence captures the central message that ties together all the details.
4. Choose the option that expresses this central message rather than just a supporting detail.""",
            "lesson": lesson,
            "grade": 4,
            "course": "Language",
            "difficulty": difficulty,
            "interaction_type": "MCQ",
            "stimuli": "The school garden project has been a big success this year. Students planted vegetables in the spring. Throughout summer, they took turns watering the plants. By fall, they harvested tomatoes, carrots, and lettuce. The vegetables were used in the school cafeteria. Teachers said it was a great way for students to learn about plant growth and healthy eating.",
            "prompt": "What is the main idea of this passage?",
            "answer_choices": {
                "A": "Students planted vegetables in the spring.",
                "B": "The school garden project was successful and educational.", 
                "C": "Vegetables from the garden were used in the cafeteria.", 
                "D": "Teachers thought the garden was a good learning experience."
            },
            "correct_answer": "B",
            "wrong_answer_explanations": {
                "A": "This is incorrect because it only mentions one detail from the passage (planting in spring) rather than the central message.",
                "C": "This is incorrect because it focuses on just one supporting detail about how the vegetables were used, not the main point of the passage.",
                "D": "This is incorrect because the teachers' opinions are just one supporting detail, not the main idea of the entire passage."
            },
            "solution": "1. Read the entire passage carefully. 2. Identify what the passage is mainly about (the school garden project's success). 3. Determine which sentence captures the central message that ties together all the details. 4. Choose the option that expresses this central message rather than just a supporting detail.",
            "full_explanation": "The main idea is the central point or message of a passage. In this passage, all the details support the idea that the school garden project was successful and educational. The other options only represent supporting details that help develop this main idea.",
            "status": "active"
        }
    else:
        # For other lessons, create a more targeted sample based on lesson description
        sample_passage = f"This is a sample passage about {lesson.lower()} concepts."
        sample_prompt = f"What is the main concept illustrated in this passage about {lesson.lower()}?"
        
        if lesson_description:
            sample_passage = f"This sample passage demonstrates {lesson_description.lower()}."
            sample_prompt = f"Based on {lesson_description.lower()}, what does this passage show?"
        
        return {
            "content": f"Sample question for {lesson} at {difficulty} difficulty. {sample_prompt}\n\nA) First option\nB) Second option\nC) Third option\nD) Fourth option\n\nCorrect Answer: A\n\nExplanation for wrong answers:\nB) This is incorrect because...\nC) This is incorrect because...\nD) This is incorrect because...\n\nSolution:\nThe correct approach is to analyze the passage by focusing on {lesson_description if lesson_description else lesson}...",
            "lesson": lesson,
            "grade": 4,
            "course": "Language",
            "difficulty": difficulty,
            "interaction_type": "MCQ",
            "stimuli": sample_passage,
            "prompt": sample_prompt,
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
            "solution": f"The correct approach is to analyze the passage by focusing on {lesson_description if lesson_description else lesson}...",
            "full_explanation": f"A detailed explanation relating to {lesson_description if lesson_description else lesson}.",
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
    Generate a batch of questions and upload them to Supabase.
    
    Args:
        lesson: The lesson name
        difficulty: The difficulty level
        count: Number of questions to generate
        use_sample: Whether to use sample data instead of the API
        
    Returns:
        List of question IDs that were successfully uploaded
    """
    if use_sample:
        os.environ["USE_SAMPLE"] = "True"
    else:
        os.environ["USE_SAMPLE"] = "False"
        
    question_ids = []
    
    # Get the lesson description - print it once for the batch
    lesson_description = get_lesson_description(lesson)
    if lesson_description:
        print(f"\nGenerating questions for lesson: {lesson}")
        print(f"Lesson description: {lesson_description}")
    
    for i in range(count):
        try:
            print(f"\nGenerating {difficulty} question {i+1}/{count} for {lesson}...")
            
            # Generate the question
            question_data = generate_question(lesson, difficulty)
            
            # Upload to Supabase
            question_id = upload_to_supabase(question_data)
            question_ids.append(question_id)
            
            print(f"Successfully uploaded question {i+1}. ID: {question_id}")
            
            # Add delay between requests to avoid overwhelming the API
            if i < count - 1 and not use_sample:
                wait_time = 3  # Increased delay between API calls
                print(f"Waiting {wait_time} seconds before next request...")
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"Error processing question {i+1}: {str(e)}")
    
    return question_ids


if __name__ == "__main__":
    # Configuration for our batch
    lesson = "Reading Fluency"
    difficulty = "easy"
    batch_size = 10  # Reduced batch size to avoid rate limits
    use_sample = False  # Use real API calls
    
    print(f"Starting generation and upload of {batch_size} questions for {lesson} at {difficulty} difficulty")
    print(f"Using sample questions: {use_sample}")
    
    # Get the lesson description for the main output
    lesson_description = get_lesson_description(lesson)
    if lesson_description:
        print(f"Lesson description: {lesson_description}")
    
    # Generate and upload questions for easy difficulty
    easy_ids = generate_and_upload_batch(lesson, difficulty, batch_size, use_sample)
    print(f"Successfully generated and uploaded {len(easy_ids)} easy questions")
    print(f"Question IDs: {easy_ids}")
    
    # Add longer delay between difficulty levels
    wait_time = 10
    print(f"\nWaiting {wait_time} seconds before processing medium difficulty questions...")
    time.sleep(wait_time)
    
    # Generate medium difficulty questions
    print("\nGenerating medium difficulty questions...")
    medium_ids = generate_and_upload_batch(lesson, "medium", batch_size, use_sample)
    print(f"Successfully generated and uploaded {len(medium_ids)} medium questions")
    
    # Add longer delay between difficulty levels
    print(f"\nWaiting {wait_time} seconds before processing hard difficulty questions...")
    time.sleep(wait_time)
    
    # Generate hard difficulty questions
    print("\nGenerating hard difficulty questions...")
    hard_ids = generate_and_upload_batch(lesson, "hard", batch_size, use_sample)
    print(f"Successfully generated and uploaded {len(hard_ids)} hard questions")
    
    # Summary
    total_questions = len(easy_ids) + len(medium_ids) + len(hard_ids)
    print(f"\nTotal questions generated and uploaded: {total_questions}")
    print(f"Easy: {len(easy_ids)}, Medium: {len(medium_ids)}, Hard: {len(hard_ids)}") 