import os
from dotenv import load_dotenv
from app.services.quality_control import QualityControlService
from app.models.test_harness import (
    TestExample, 
    QualityStatus, 
    QualityCriterion, 
    MutationType, 
    DifficultyLevel,
    QualityCheckResult
)
from app.services.question_service import QuestionService
from app.schemas.question import QuestionGradeRequest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
from datetime import datetime
import random
import re
import asyncio

def create_session():
    """Create a requests session with retry logic and timeouts"""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=100, pool_connections=100)
    session.mount('https://', adapter)
    session.timeout = (10, 90)
    return session

def setup_supabase(session, supabase_url: str, headers: dict) -> None:
    """Check and validate test_examples table structure"""
    try:
        # First check if table exists and get its structure
        response = session.get(
            f"{supabase_url}/rest/v1/test_examples?select=*&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Database connected")
            return  # Table exists, don't try to create it
            
        elif response.status_code == 404:
            print("⚙️ Table not found, creating test_examples table...")
            # Create table with appropriate schema
            create_table_sql = """
            create table if not exists test_examples (
                id uuid default uuid_generate_v4() primary key,
                content text not null,
                quality_status text not null,
                quality_criterion text not null,
                mutation_type text not null,
                lesson text not null,
                difficulty_level text not null,
                metadata jsonb,
                created_at timestamp with time zone default timezone('utc'::text, now()),
                updated_at timestamp with time zone default timezone('utc'::text, now())
            );
            """
            response = session.post(
                f"{supabase_url}/rest/v1/rpc/create_table",
                headers=headers,
                json={"sql": create_table_sql}
            )
            if response.status_code in [200, 201]:
                print("✅ Table created successfully")
            else:
                print(f"❌ Failed to create table: {response.status_code}")
                print(response.text)
        else:
            print(f"❌ Unexpected status code when checking table: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        raise

def save_example(session, supabase_url: str, headers: dict, example: dict) -> dict:
    """Save a test example to Supabase"""
    try:
        # Convert lesson name to match existing format
        lesson_mapping = {
            "main_idea": "Main Idea and Supporting Details",
            "supporting_details": "Supporting Details",
            "authors_purpose": "Author's Purpose"
        }
        
        # Map quality criteria to database enums
        criterion_mapping = {
            "completeness": "question_stem",  # Completeness maps to question structure/stem
            "answer_quality": "correct_answer",  # Answer quality relates to correct answer validity
            "explanation_quality": "distractors",  # Explanation quality often relates to distractor explanations
            "language_quality": "grammar",  # Language issues map to grammar
            "vocabulary": "vocabulary",  # Direct mapping
            "standard_alignment": "standard_alignment"  # Direct mapping
        }
        
        # If there are failed criteria, use the first one as the quality criterion
        quality_criterion = "distractors"  # Default to distractors as fallback
        if example.get("metadata", {}).get("failed_criteria"):
            failed = example["metadata"]["failed_criteria"][0]
            quality_criterion = criterion_mapping.get(failed.lower(), "distractors")
        
        # Prepare metadata with feedback
        metadata = {
            "scores": example.get("metadata", {}).get("scores", {}),
            "failed_criteria": example.get("metadata", {}).get("failed_criteria", []),
            "feedback": example.get("metadata", {}).get("feedback", {}),
            "mutation_info": example.get("metadata", {}).get("mutation_from"),
            "mutation_type": example.get("metadata", {}).get("mutation_type"),
            "original_criterion": example.get("quality_criterion")  # Store original criterion for reference
        }
        
        # Prepare data for save
        data = {
            "content": example["content"],
            "quality_status": example["quality_status"].lower(),
            "quality_criterion": quality_criterion,
            "mutation_type": example["mutation_type"].lower(),
            "lesson": lesson_mapping.get(example["lesson"], example["lesson"]),
            "difficulty_level": example["difficulty_level"].lower(),
            "metadata": metadata
        }
        
        # First save with minimal return
        response = session.post(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            json=data
        )
            
        response.raise_for_status()
        
        # If we need the ID, make a separate request to get the latest record
        if data["quality_status"] == "good":  # Only fetch ID for good examples since we need it for mutations
            headers_with_return = headers.copy()
            headers_with_return["Prefer"] = "return=representation"
            response = session.get(
                f"{supabase_url}/rest/v1/test_examples?order=created_at.desc&limit=1",
                headers=headers_with_return
            )
            if response.status_code == 200:
                return response.json()[0]
        
        return data  # Return the data we saved as fallback
        
    except Exception as e:
        print(f"❌ Error saving example: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"Response text: {e.response.text}")
        return None

def get_historical_feedback(session, supabase_url: str, headers: dict, lesson: str, difficulty: str) -> dict:
    """Get detailed feedback and patterns from previous examples"""
    try:
        print(f"📚 Loading history for {lesson}/{difficulty}...")
        
        lesson_mapping = {
            "main_idea": "Main Idea and Supporting Details",
            "supporting_details": "Supporting Details",
            "authors_purpose": "Author's Purpose"
        }
        mapped_lesson = lesson_mapping.get(lesson, lesson)
        
        response = session.get(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            params={
                "lesson": f"eq.{mapped_lesson}",
                "difficulty_level": f"eq.{difficulty}",
                "select": "metadata,quality_status,content"
            }
        )
        
        if response.status_code == 200:
            examples = response.json()
            count = len(examples)
            success_count = sum(1 for e in examples if e.get("quality_status") == "good")
            print(f"  • Found {count} examples ({success_count} good, {count - success_count} bad)")
            
            # Extract successful language patterns
            successful_patterns = {
                "passages": [],
                "explanations": [],
                "solutions": []
            }
            
            # Analyze successful and failed examples separately
            language_rules = []  # Specific language rules
            common_issues = {}   # Track frequency of issues
            successful_sentences = []  # Examples of good sentence structures
            transformation_pairs = []  # Store specific before/after transformation examples

            # Track feedback patterns that consistently lead to 0.95 scores
            language_score_patterns = []
            
            for example in examples:
                metadata = example.get("metadata", {})
                scores = metadata.get("scores", {})
                content = example.get("content", "")
                
                # Extract successful patterns from high-scoring examples
                if scores.get("language_quality", 0) >= 0.98:
                    # Extract successful passage
                    passage_match = re.search(r'Read the following passage.*?\n\n(.*?)\n\n', content, re.DOTALL)
                    if passage_match:
                        successful_patterns["passages"].append(passage_match.group(1))
                    
                    # Extract and store good sentences (simple structure, grade-appropriate)
                    sentences = re.findall(r'[A-Z][^.!?]*[.!?]', content)
                    simple_sentences = [s for s in sentences if len(s.split()) < 12 and "," not in s]
                    successful_sentences.extend(simple_sentences[:3])  # Take a few examples
                
                # Extract specific before/after examples from language feedback
                feedback_data = metadata.get("feedback", {})
                if isinstance(feedback_data, dict) and "language_quality" in feedback_data:
                    feedback = feedback_data["language_quality"]
                    
                    # If the score is exactly 0.95, capture what issues led to that score
                    if scores.get("language_quality") == 0.95:
                        language_score_patterns.append(feedback[:100])  # Store truncated feedback
                    
                    # Look for specific transformation examples (consider X instead of Y)
                    if isinstance(feedback, str):
                        # Pattern for "instead of X, consider Y"
                        transformation_matches = re.finditer(r'instead of [\'"]([^\'"].*?)[\'"],?\s*consider [\'"]([^\'"].*?)[\'"]', feedback, re.IGNORECASE)
                        for match in transformation_matches:
                            before, after = match.group(1), match.group(2)
                            transformation_pairs.append((before.strip(), after.strip()))
                        
                        # Pattern for "X could be simplified to Y"
                        simplify_matches = re.finditer(r'[\'"]([^\'"].*?)[\'"] could be simplified to [\'"]([^\'"].*?)[\'"]', feedback, re.IGNORECASE)
                        for match in simplify_matches:
                            before, after = match.group(1), match.group(2)
                            transformation_pairs.append((before.strip(), after.strip()))
                        
                        # Pattern for "X could be Y" or "X could become Y"
                        could_be_matches = re.finditer(r'[\'"]([^\'"].*?)[\'"] could (?:be|become) [\'"]([^\'"].*?)[\'"]', feedback, re.IGNORECASE)
                        for match in could_be_matches:
                            before, after = match.group(1), match.group(2)
                            transformation_pairs.append((before.strip(), after.strip()))
                        
                        # Extract specific rules or suggestions
                        rules = re.findall(r'(?:avoid|use|keep|make|ensure|simplif|consider).*?(?:\.|\n)', feedback.lower())
                        language_rules.extend(rules)
                    
                    # Extract specific issues
                    issues = ["complex vocabulary", "complex sentence", "ambiguous", "technical terms", 
                              "grade level", "vocabulary complexity", "sentence structure", "simplify"]
                    
                    for issue in issues:
                        if issue in feedback.lower():
                            common_issues[issue] = common_issues.get(issue, 0) + 1
            
            # Create prioritized list of rules based on frequency of issues
            prioritized_rules = []
            for issue, count in sorted(common_issues.items(), key=lambda x: x[1], reverse=True):
                # Find rules related to this issue
                relevant_rules = [rule for rule in language_rules if issue in rule.lower()]
                if relevant_rules:
                    prioritized_rules.extend(relevant_rules[:2])  # Add top 2 rules for each issue
            
            # Extract patterns from content that consistently fails at 0.95
            common_patterns_095 = []
            if language_score_patterns:
                # Look for recurring phrases that appear in multiple 0.95 failures
                all_text = " ".join(language_score_patterns)
                common_words = ["could be", "simplified", "ambiguity", "option", "explanation", 
                               "grade level", "technical", "complex"]
                for word in common_words:
                    if all_text.count(word) >= 2:  # If appears multiple times
                        common_patterns_095.append(word)
            
            if language_rules:
                print(f"  • Extracted {len(language_rules)} language rules")
            if successful_sentences:
                print(f"  • Found {len(successful_sentences)} good sentence examples")
            if transformation_pairs:
                print(f"  • Captured {len(transformation_pairs)} specific transformations")
                
            return {
                "successful_patterns": successful_patterns,
                "successful_sentences": successful_sentences[:5],  # Limit to 5 examples
                "language_rules": prioritized_rules[:7] if prioritized_rules else language_rules[:7],  # Limit to 7 key rules
                "common_issues": common_issues,
                "transformation_pairs": transformation_pairs,
                "patterns_095": common_patterns_095
            }
            
        return {
            "successful_patterns": {}, 
            "language_rules": [], 
            "successful_sentences": [], 
            "common_issues": {},
            "transformation_pairs": [],
            "patterns_095": []
        }
            
    except Exception as e:
        print(f"❌ History loading error: {str(e)}")
        return {
            "successful_patterns": {}, 
            "language_rules": [], 
            "successful_sentences": [], 
            "common_issues": {},
            "transformation_pairs": [],
            "patterns_095": []
        }

def apply_language_simplification(content: str, historical_data: dict) -> str:
    """Apply specific language transformations to content based on historical feedback"""
    if not content or not historical_data:
        return content
    
    print("🔍 Applying language simplifications...")
    
    # Extract transformation pairs from historical data
    transformation_pairs = historical_data.get("transformation_pairs", [])
    patterns_095 = historical_data.get("patterns_095", [])
    
    # Count transformations applied
    transformations_applied = 0
    
    # Make a copy of the content to modify
    simplified_content = content
    
    # Apply specific transformations first (only those from historical feedback)
    for before, after in transformation_pairs:
        if before in simplified_content:
            simplified_content = simplified_content.replace(before, after)
            transformations_applied += 1
    
    # Apply gentler, targeted simplifications that preserve complete explanations
    
    # 1. Simplify explanations for wrong answers without truncating
    explanation_section = re.search(r'Explanation for wrong answers:(.*?)(?:Solution:|$)', simplified_content, re.DOTALL)
    if explanation_section:
        explanations = explanation_section.group(1)
        
        # Replace overly formal phrases with simpler ones without truncating
        formal_phrases = {
            "This is incorrect because": "This is wrong because",
            "This is not accurate because": "This is wrong because",
            "This option is incorrect because": "This is wrong because",
            "not the main idea of the passage": "not what the passage is mostly about",
            "does not accurately represent": "doesn't match",
            "does not reflect": "doesn't show",
            "This answer choice": "This answer",
            "focuses only on a minor detail": "is just one small part",
            "evidence from the text": "words from the story"
        }
        
        simplified_explanations = explanations
        for formal, simple in formal_phrases.items():
            simplified_explanations = simplified_explanations.replace(formal, simple)
        
        # Replace the original explanations with simplified ones
        simplified_content = simplified_content.replace(explanations, simplified_explanations)
        
    # 2. Simplify complex words throughout the content but preserve meaning
    complex_word_replacements = {
        "primary purpose": "main purpose",
        "narrative": "story",
        "intention": "purpose",
        "convey information": "give information",
        "demonstrate": "show",
        "illustrate": "show",
        "comprehend": "understand",
        "implement": "use",
        "initial": "first",
        "specifically": "exactly",
        "ambiguous": "unclear",
        "determine": "find out",
        "elaborate": "detailed",
        "incorporate": "include",
        "substantial": "major",
        "additional": "more",
        "sufficient": "enough",
        "extensively": "widely",
        "appropriate": "right",
        "comprehension": "understanding"
    }
    
    for complex_term, simple_term in complex_word_replacements.items():
        if complex_term in simplified_content.lower():
            # Replace the term with case preserved
            pattern = re.compile(re.escape(complex_term), re.IGNORECASE)
            simplified_content = pattern.sub(simple_term, simplified_content)
            transformations_applied += 1
    
    # 3. Handle incomplete explanation problem specifically
    # Check for truncated explanations and fix them
    truncated_explanations = re.finditer(r'This doesn\'t work because it\'s just a\.', simplified_content)
    for match in truncated_explanations:
        # Replace with a complete sentence that makes sense
        simplified_content = simplified_content.replace(
            "This doesn't work because it's just a.", 
            "This doesn't work because it's just a small detail, not the main point."
        )
        transformations_applied += 1
    
    if transformations_applied > 0:
        print(f"  • Applied {transformations_applied} gentle language simplifications")
    
    return simplified_content

async def generate_question(lesson: str, difficulty: str, historical_data: dict = None, example_question: str = None) -> dict:
    """
    Generate a new question using the QuestionService and historical data.
    This is the core function that can be used by both scripts and API endpoints.
    
    Args:
        lesson: Lesson topic
        difficulty: Difficulty level (easy, medium, hard)
        historical_data: Historical feedback data from previous examples
        example_question: Optional example question to generate a variation from
        
    Returns:
        dict: Result containing generated content and quality assessment
    """
    
    # Initialize question service for grading
    question_service = QuestionService()
    await question_service.load_good_examples()  # Ensure grading criteria are loaded
    
    # For API use, create a fallback QC service if needed
    qc_service = QualityControlService() 
    
    # Set up context options for variety
    contexts = [
        "a student's experience at school",
        "an interesting animal fact",
        "a historical event",
        "a scientific discovery",
        "a community event",
        "a family tradition",
        "a nature observation",
        "a problem-solving situation",
        "a cultural celebration",
        "a creative activity"
    ]
    
    # Track previously used topics to avoid repetition
    used_topics = []
    if historical_data and "successful_patterns" in historical_data:
        for passage in historical_data["successful_patterns"].get("passages", []):
            for context in contexts:
                if context.lower() in passage.lower():
                    used_topics.append(context)
    
    available_contexts = [c for c in contexts if c not in used_topics]
    if not available_contexts:
        available_contexts = contexts
    selected_context = random.choice(available_contexts)
    
    # Question structure options
    structures = [
        "What is the main idea of this passage?",
        "Which detail best supports the main idea?",
        "What is the author's purpose in writing this passage?",
        "What is the most important information in the passage?",
        "Which sentence best summarizes the passage?"
    ]
    
    # Extract language guidance from historical data
    language_guidance = ""
    if historical_data:
        language_rules = historical_data.get("language_rules", [])
        successful_sentences = historical_data.get("successful_sentences", [])
        common_issues = historical_data.get("common_issues", {})
        
        language_guidance = "Language Requirements:\n"
        
        if language_rules:
            language_guidance += "Based on previous feedback, FOLLOW THESE SPECIFIC RULES:\n"
            for i, rule in enumerate(language_rules[:5], 1):
                language_guidance += f"{i}. {rule.capitalize()}\n"
        
        # Add examples of good sentence structures if available
        if successful_sentences:
            language_guidance += "\nEXAMPLES OF GOOD SENTENCES FOR GRADE 4:\n"
            for i, sentence in enumerate(successful_sentences[:3], 1):
                language_guidance += f"Example {i}: \"{sentence.strip()}\"\n"
        
        # Add specific guidance based on common issues
        if common_issues:
            most_common = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)[:3]
            language_guidance += "\nSPECIAL FOCUS AREAS (based on previous mistakes):\n"
            for issue, _ in most_common:
                if "vocabulary" in issue:
                    language_guidance += "- Use simple, grade 4 vocabulary. Avoid technical terms without explanation.\n"
                if "sentence" in issue:
                    language_guidance += "- Use short, direct sentences. Break up complex sentences into multiple simple ones.\n"
                if "ambiguous" in issue:
                    language_guidance += "- Ensure explanations are specific and clear. Avoid vague descriptions.\n"
        
        # Add specific transformations learned from feedback
        if "transformation_pairs" in historical_data and historical_data["transformation_pairs"]:
            language_guidance += "\nSPECIFIC LANGUAGE TRANSFORMATIONS TO FOLLOW:\n"
            for i, (before, after) in enumerate(historical_data["transformation_pairs"][:5], 1):
                language_guidance += f"{i}. Use \"{after}\" instead of \"{before}\"\n"
    else:
        # Default language guidance if no history exists
        language_guidance = """Language Requirements:
SPECIAL FOCUS AREAS:
- Use simple, grade 4 vocabulary. Avoid technical terms without explanation.
- Use short, direct sentences. Break up complex sentences into multiple simple ones.
- Ensure explanations are specific and clear. Avoid vague descriptions.
- Keep all explanations concrete and directly related to the passage.
"""
    
    # Handle variation generation if example_question is provided
    if example_question:
        prompt = f"""Generate a Grade 4 Language Arts question variation for the lesson on "{lesson}" at {difficulty} difficulty level.
This is based on the following example question:

{example_question}

{language_guidance}

IMPORTANT:
1. Keep the same general structure and question type
2. Create a DIFFERENT passage with similar complexity
3. Maintain the same difficulty level
4. Use the same number of options
5. Keep all the required parts: passage, question, options, explanations, and solution

FORMAT THE QUESTION EXACTLY LIKE THE EXAMPLE ABOVE but with new content.
"""
    else:
        # Create a new question from scratch
        prompt = f"""Generate a Grade 4 Language Arts question for the lesson on "{lesson}" at {difficulty} difficulty level.

{language_guidance}

Content Requirements:
1. Write a passage about {selected_context}
2. Use {random.choice(structures)} as your question
3. Create 4 multiple choice options
4. Include COMPLETE explanations for each wrong answer 
5. Provide 3-4 solution steps

IMPORTANT LANGUAGE GUIDELINES FOR GRADE 4:
- Use simple words when possible, but don't sacrifice completeness
- Keep sentences under 15 words when you can
- Always write COMPLETE explanations that teach why an answer is right or wrong
- Each wrong answer explanation must be a complete thought with educational value
- Be historically and factually accurate in all content

FORMAT THE QUESTION EXACTLY LIKE THIS:
Read the following passage and answer the question.

[Write a simple, clear passage with short sentences]

[Question]

A) [Option]
B) [Option]
C) [Option]
D) [Option]

Correct Answer: [Letter]

Explanation for wrong answers:
A) [If incorrect: Clear explanation why this is wrong - must be a complete thought]
B) [If incorrect: Clear explanation why this is wrong - must be a complete thought]
C) [If incorrect: Clear explanation why this is wrong - must be a complete thought]
D) [If incorrect: Clear explanation why this is wrong - must be a complete thought]

Solution:
1. [Simple step]
2. [Simple step]
3. [Simple step]
4. [Optional simple step]"""

    # Generate content using OpenAI
    content = qc_service._generate_with_gpt(prompt)
    
    # Apply language simplifications based on historical data
    content = apply_language_simplification(content, historical_data)
    
    # Grade the generated question using our QuestionService
    # Create a proper QuestionGradeRequest object instead of using a dict
    request = QuestionGradeRequest(question=content)
    result = await question_service.grade_question(request)
    
    # Convert pydantic model to dict for easier handling
    result_dict = {
        "passed": result.passed,
        "overall_score": result.overall_score,
        "criterion_scores": result.criterion_scores,
        "failed_criteria": result.failed_criteria,
        "feedback": result.feedback,
        "improvement_suggestions": result.improvement_suggestions,
        "content": content
    }
    
    return result_dict

def extract_feedback(result: dict) -> list:
    """Extract actionable feedback from quality check results"""
    feedback = []
    
    # Extract passage topic for variety tracking
    content = result.get('content', "")
    if content:
        passage_match = re.search(r'Read the following passage.*?\n\n(.*?)\n\n', content, re.DOTALL)
        if passage_match:
            passage = passage_match.group(1)
            feedback.append(f"Previous passage about: {passage[:50]}...")
    
    # Extract specific feedback by criterion
    for criterion, score in result.get('criterion_scores', {}).items():
        if score < 0.99:
            criterion_feedback = result.get('feedback', '').split(f"{criterion}:", 1)
            if len(criterion_feedback) > 1:
                # For language feedback, extract specific issues
                if criterion == "language_quality":
                    issues = criterion_feedback[1].split(".")
                    for issue in issues:
                        if "sentence" in issue.lower() or "structure" in issue.lower():
                            feedback.append(f"Language pattern to improve: {issue.strip()}")
                else:
                    feedback.append(criterion_feedback[1].strip())
    
    return feedback

async def generate_question_for_api(lesson: str, difficulty: str, example_question: str = None, max_attempts: int = 3) -> dict:
    """
    API-ready function to generate a question with automatic retries for quality.
    This function can be called directly from an API endpoint.
    
    Args:
        lesson: The lesson to generate a question for
        difficulty: The difficulty level (easy, medium, hard)
        example_question: Optional example to create a variation from
        max_attempts: Maximum number of generation attempts
    
    Returns:
        dict: Contains the generated question and its quality assessment
    """
    
    # First, get historical feedback for this lesson/difficulty combo
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        # Fallback to generation without historical data
        historical_data = None
    else:
        # Get historical data
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        session = create_session()
        historical_data = get_historical_feedback(session, supabase_url, headers, lesson, difficulty)
    
    attempts = 0
    best_result = None
    highest_score = 0
    
    # Try to generate a high-quality question with retries
    while attempts < max_attempts:
        attempts += 1
        result = await generate_question(lesson, difficulty, historical_data, example_question)
        
        # If we got a passing result, return it immediately
        if result["passed"]:
            return {
                "content": result["content"],
                "quality": {
                    "passed": True,
                    "scores": result["criterion_scores"],
                    "overall_score": result["overall_score"]
                },
                "metadata": {
                    "lesson": lesson,
                    "difficulty": difficulty,
                    "attempts": attempts
                }
            }
        
        # Otherwise, keep track of the best result so far
        if result["overall_score"] > highest_score:
            highest_score = result["overall_score"]
            best_result = result
    
    # If we couldn't generate a passing question after max attempts,
    # return the best one we found with appropriate feedback
    return {
        "content": best_result["content"],
        "quality": {
            "passed": False,
            "scores": best_result["criterion_scores"],
            "overall_score": best_result["overall_score"],
            "failed_criteria": best_result["failed_criteria"],
            "feedback": best_result["feedback"]
        },
        "metadata": {
            "lesson": lesson,
            "difficulty": difficulty,
            "attempts": attempts
        }
    }

async def main():
    """Generate and test questions with improved output"""
    load_dotenv()
    
    # Initialize services
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    session = create_session()
    
    # Setup Supabase
    setup_supabase(session, supabase_url, headers)
    
    lessons = ["main_idea", "supporting_details", "authors_purpose"]
    difficulties = ["easy", "medium", "hard"]
    target_per_combination = 5
    
    total_generated = 0
    total_passed = 0
    
    try:
        print("\n🚀 Starting question generation with learning feedback")
        print("=" * 60)
        
        for lesson in lessons:
            for difficulty in difficulties:
                print(f"\n🎯 {lesson.upper()} - {difficulty.upper()}")
                print("-" * 40)
                
                historical_data = get_historical_feedback(session, supabase_url, headers, lesson, difficulty)
                
                good_examples = 0
                attempts = 0
                max_attempts = 20
                feedback_history = []
                
                while good_examples < target_per_combination and attempts < max_attempts:
                    attempts += 1
                    total_generated += 1
                    
                    print(f"\n[{attempts}/{max_attempts}] 🔄 Generating question... ({good_examples}/{target_per_combination} ✓)")
                    
                    try:
                        # Use the new generation function
                        result = await generate_question(lesson, difficulty, historical_data)
                        
                        # Very compact score display
                        scores = result["criterion_scores"]
                        score_display = " ".join([
                            f"{'✓' if scores.get('completeness', 0) >= 0.99 else '✗'}{scores.get('completeness', 0):.2f}",
                            f"{'✓' if scores.get('answer_quality', 0) >= 0.99 else '✗'}{scores.get('answer_quality', 0):.2f}",
                            f"{'✓' if scores.get('explanation_quality', 0) >= 0.99 else '✗'}{scores.get('explanation_quality', 0):.2f}",
                            f"{'✓' if scores.get('language_quality', 0) >= 0.99 else '✗'}{scores.get('language_quality', 0):.2f}"
                        ])
                        
                        if result["passed"]:
                            print(f"✅ PASSED! Scores: {score_display}")
                        else:
                            print(f"❌ FAILED: {score_display}")
                            print(f"   Issues: {', '.join(result['failed_criteria'])}")
                            
                            # Extract specific transformation pairs from language quality feedback
                            if "language_quality" in result["failed_criteria"] and result["feedback"]:
                                language_feedback = ""
                                for line in result["feedback"].split("\n"):
                                    if "language_quality:" in line.lower():
                                        language_feedback = line
                                        break
                                
                                # Look for specific transformation examples
                                transformation_matches = re.finditer(
                                    r'instead of [\'"]([^\'"].*?)[\'"],?\s*consider [\'"]([^\'"].*?)[\'"]', 
                                    language_feedback, 
                                    re.IGNORECASE
                                )
                                for match in transformation_matches:
                                    before, after = match.group(1), match.group(2)
                                    if not any(b == before for b, a in historical_data.get("transformation_pairs", [])):
                                        historical_data.setdefault("transformation_pairs", []).append((before, after))
                                        print(f"   ⚡ Learned: Use \"{after}\" instead of \"{before}\"")
                        
                        # Save example
                        example = {
                            "content": result["content"],
                            "quality_status": "good" if result["passed"] else "bad",
                            "quality_criterion": "completeness",
                            "mutation_type": "original",
                            "lesson": lesson,
                            "difficulty_level": difficulty,
                            "metadata": {
                                "scores": {k: round(v, 2) for k, v in scores.items()},
                                "failed_criteria": result["failed_criteria"],
                                "feedback": result["feedback"]
                            }
                        }
                        
                        # Save to database
                        saved_example = save_example(session, supabase_url, headers, example)
                        
                        if result["passed"]:
                            good_examples += 1
                            total_passed += 1
                            
                            # Generate mutations with simplified output
                            print("🧬 Generating mutations...")
                            qc_service = QualityControlService()
                            mutations = qc_service.generate_mutations(TestExample(**example))
                            mutation_count = len(mutations)
                            
                            for i, mutation in enumerate(mutations, 1):
                                mutation_dict = mutation.dict()
                                mutation_dict.pop('id', None)
                                if saved_example and saved_example.get("id"):
                                    mutation_dict["metadata"] = {
                                        "mutation_from": saved_example["id"],
                                        "mutation_type": mutation_dict["mutation_type"].lower()
                                    }
                                save_example(session, supabase_url, headers, mutation_dict)
                            
                            print(f"   ✓ Saved {mutation_count} mutations")
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"❌ Error: {str(e)}")
                        continue
                
                print(f"\n📋 {lesson}/{difficulty}: {good_examples}/{target_per_combination} examples generated")
        
        # Final stats
        print("\n🏁 Generation complete!")
        print(f"📊 Success rate: {(total_passed/total_generated)*100:.1f}% ({total_passed}/{total_generated})")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 