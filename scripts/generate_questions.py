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
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
from datetime import datetime

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
        print("Checking test_examples table...")
        # First check if table exists and get its structure
        response = session.get(
            f"{supabase_url}/rest/v1/test_examples?select=*&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✓ Test examples table exists")
            print("\nChecking recent entries:")
            # Check recent entries to verify structure
            response = session.get(
                f"{supabase_url}/rest/v1/test_examples?select=*&order=created_at.desc&limit=1",
                headers=headers
            )
            if response.status_code == 200:
                entries = response.json()
                if entries:
                    print("Found existing entries. Example structure:")
                    print(json.dumps(entries[0], indent=2))
                else:
                    print("Table exists but is empty")
            else:
                print("Could not fetch recent entries")
            
            return  # Table exists, don't try to create it
            
        elif response.status_code == 404:
            print("Table not found, creating test_examples table...")
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
                print("✓ Table created successfully")
            else:
                print(f"✗ Failed to create table: {response.status_code}")
                print(response.text)
        else:
            print(f"✗ Unexpected status code when checking table: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"✗ Error checking/setting up Supabase: {str(e)}")
        raise

def save_example(session, supabase_url: str, headers: dict, example: dict) -> None:
    """Save a test example to Supabase"""
    try:
        print("\nSaving example to Supabase...")
        
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
        
        # Print request data for debugging
        print("\nRequest data:")
        data = {
            "content": example["content"],
            "quality_status": example["quality_status"].lower(),
            "quality_criterion": quality_criterion,
            "mutation_type": example["mutation_type"].lower(),
            "lesson": lesson_mapping.get(example["lesson"], example["lesson"]),
            "difficulty_level": example["difficulty_level"].lower(),
            "metadata": metadata
        }
        print(json.dumps(data, indent=2))
        
        response = session.post(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            json=data
        )
        
        # Print response details for debugging
        print(f"\nResponse status: {response.status_code}")
        if response.text:
            print(f"Response body: {response.text}")
            
        response.raise_for_status()
        print(f"✓ Saved example with quality_status: {data['quality_status']}")
        return response.json()  # Return the created record to get its ID
    except Exception as e:
        print(f"✗ Error saving example: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"Response text: {e.response.text}")
        return None

def get_historical_feedback(session, supabase_url: str, headers: dict, lesson: str, difficulty: str) -> list:
    """Get feedback from previous examples for this lesson and difficulty level"""
    try:
        print(f"\nLoading historical feedback for {lesson} at {difficulty} level...")
        
        # Convert lesson name to match database format
        lesson_mapping = {
            "main_idea": "Main Idea and Supporting Details",
            "supporting_details": "Supporting Details",
            "authors_purpose": "Author's Purpose"
        }
        mapped_lesson = lesson_mapping.get(lesson, lesson)
        
        # Query Supabase for relevant examples
        query_params = {
            "lesson": f"eq.{mapped_lesson}",
            "difficulty_level": f"eq.{difficulty}",
            "select": "metadata,quality_status"
        }
        
        response = session.get(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            params=query_params
        )
        
        if response.status_code == 200:
            examples = response.json()
            
            # Collect feedback patterns
            feedback_patterns = {
                "common_issues": [],
                "successful_patterns": [],
                "improvement_suggestions": []
            }
            
            for example in examples:
                metadata = example.get("metadata", {})
                
                if example["quality_status"] == "bad":
                    # Extract feedback from failed examples
                    if metadata.get("feedback"):
                        for criterion, feedback in metadata["feedback"].items():
                            if isinstance(feedback, str) and feedback.strip():
                                feedback_patterns["common_issues"].append(f"{criterion}: {feedback}")
                else:
                    # Learn from successful examples
                    scores = metadata.get("scores", {})
                    high_scoring_criteria = [k for k, v in scores.items() if v >= 0.99]
                    if high_scoring_criteria:
                        feedback_patterns["successful_patterns"].extend(high_scoring_criteria)
            
            # Deduplicate and format feedback
            feedback_summary = []
            
            if feedback_patterns["common_issues"]:
                # Get unique issues, prioritize most frequent
                from collections import Counter
                issue_counter = Counter(feedback_patterns["common_issues"])
                common_issues = [issue for issue, count in issue_counter.most_common(5)]
                feedback_summary.extend([
                    "Common issues to avoid:",
                    *[f"- {issue}" for issue in common_issues]
                ])
            
            if feedback_patterns["successful_patterns"]:
                # Get most common success patterns
                pattern_counter = Counter(feedback_patterns["successful_patterns"])
                success_patterns = [pattern for pattern, count in pattern_counter.most_common(3)]
                feedback_summary.extend([
                    "\nStrengths to maintain:",
                    *[f"- Strong {pattern}" for pattern in success_patterns]
                ])
            
            print(f"✓ Loaded feedback from {len(examples)} previous examples")
            return feedback_summary
            
        else:
            print(f"✗ Failed to load historical feedback: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error loading historical feedback: {str(e)}")
        return []

def generate_question(qc_service: QualityControlService, lesson: str, difficulty: str, feedback_history: list, historical_feedback: list = None) -> str:
    """Generate a new question using GPT-4, incorporating both recent and historical feedback"""
    
    # Combine historical and recent feedback
    feedback_guidance = ""
    if historical_feedback:
        feedback_guidance += "\n\nBased on analysis of previous questions:\n" + "\n".join(historical_feedback)
    
    if feedback_history:
        feedback_guidance += "\n\nBased on recent attempts, please address:\n" + "\n".join(
            f"- {feedback}" for feedback in feedback_history[-3:]
        )
    
    prompt = f"""Generate a Grade 4 Language Arts question for the lesson on "{lesson}" at {difficulty} difficulty level.
    The question should:
    1. Include a short passage (2-4 sentences)
    2. Ask about the main idea or key details
    3. Have 4 multiple choice options (A, B, C, D)
    4. Include explanations for wrong answers
    5. Provide a step-by-step solution
    6. Use grade-appropriate vocabulary
    7. Have clear and unambiguous wording
    8. Use simple sentence structures appropriate for Grade 4
    9. Ensure options are clearly distinct and not ambiguous
    {feedback_guidance}
    
    Format the question exactly like this example:
    Read the following passage and answer the question.
    
    [Your 2-4 sentence passage here]
    
    [Your question here]
    
    A) [First option]
    B) [Second option]
    C) [Third option]
    D) [Fourth option]
    
    Correct Answer: [Letter]
    
    Explanation for wrong answers:
    A) [Explanation why A is wrong - skip if A is correct]
    B) [Explanation why B is wrong - skip if B is correct]
    C) [Explanation why C is wrong - skip if C is correct]
    D) [Explanation why D is wrong - skip if D is correct]
    
    Solution:
    [Step-by-step guidance on how to solve this question]"""

    return qc_service._generate_with_gpt(prompt)

def extract_feedback(result: QualityCheckResult) -> list:
    """Extract actionable feedback from quality check results"""
    feedback = []
    for criterion, score in result.criterion_scores.items():
        if score < 0.99:
            # Extract the actual feedback message after the criterion name
            criterion_feedback = result.feedback.split(f"{criterion}:", 1)
            if len(criterion_feedback) > 1:
                feedback.append(criterion_feedback[1].strip())
    return feedback

def main():
    """Generate and test questions, building our test harness"""
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
    qc_service = QualityControlService()
    
    # Setup Supabase
    setup_supabase(session, supabase_url, headers)
    
    # Define our test matrix
    lessons = ["main_idea", "supporting_details", "authors_purpose"]
    difficulties = ["easy", "medium", "hard"]
    target_per_combination = 5  # Number of good examples to generate per lesson/difficulty combo
    
    total_generated = 0
    total_passed = 0
    
    try:
        for lesson in lessons:
            for difficulty in difficulties:
                print(f"\nGenerating questions for lesson: {lesson}, difficulty: {difficulty}")
                print("=" * 80)
                
                # Load historical feedback at the start of each lesson/difficulty combination
                historical_feedback = get_historical_feedback(session, supabase_url, headers, lesson, difficulty)
                
                good_examples = 0
                attempts = 0
                max_attempts = 20
                feedback_history = []
                
                while good_examples < target_per_combination and attempts < max_attempts:
                    attempts += 1
                    total_generated += 1
                    
                    print(f"\nAttempt {attempts}/{max_attempts} (Good examples: {good_examples}/{target_per_combination})")
                    
                    try:
                        # Generate a question with both historical and recent feedback
                        content = generate_question(qc_service, lesson, difficulty, feedback_history, historical_feedback)
                        print("\nGenerated question:")
                        print("-" * 40)
                        print(content)
                        print("-" * 40)
                        
                        # Check its quality
                        print("\nChecking quality...")
                        result = qc_service.check_quality(content)
                        
                        # Extract feedback for future generations
                        if not result.passed:
                            new_feedback = extract_feedback(result)
                            feedback_history.extend(new_feedback)
                        
                        # Save the example regardless of whether it passed or failed
                        example = {
                            "content": content,
                            "quality_status": "good" if result.passed else "bad",
                            "quality_criterion": "completeness",  # Default to completeness for generated
                            "mutation_type": "original",
                            "lesson": lesson,
                            "difficulty_level": difficulty,
                            "metadata": {
                                "scores": {k: round(v, 2) for k, v in result.criterion_scores.items()},
                                "failed_criteria": result.failed_criteria,
                                "feedback": {
                                    criterion: feedback
                                    for criterion, feedback in [f.split(':', 1) for f in result.feedback.split('\n') if ':' in f]
                                } if result.feedback else {},
                                "generation_attempt": attempts,
                                "feedback_history": feedback_history[-3:] if feedback_history else []  # Keep last 3 pieces of feedback
                            }
                        }
                        
                        # Save example once and get its ID
                        saved_example = save_example(session, supabase_url, headers, example)
                        
                        if result.passed:
                            good_examples += 1
                            total_passed += 1
                            print("✓ Question passed quality check!")
                            
                            # Generate mutations from good examples
                            print("\nGenerating mutations...")
                            mutations = qc_service.generate_mutations(TestExample(**example))
                            for mutation in mutations:
                                mutation_dict = mutation.dict()
                                mutation_dict.pop('id', None)  # Remove id as it will be generated by Supabase
                                
                                # Keep track of which good example this was mutated from
                                if saved_example and saved_example.get("id"):
                                    mutation_dict["metadata"] = {
                                        "mutation_from": saved_example["id"],
                                        "mutation_type": mutation_dict["mutation_type"].lower(),
                                        "original_scores": example.get("metadata", {}).get("scores", {}),
                                        "feedback": mutation.feedback if hasattr(mutation, 'feedback') else {},
                                        "original_content": example["content"]  # Store the original content for reference
                                    }
                                
                                save_example(session, supabase_url, headers, mutation_dict)
                        else:
                            print("✗ Question failed quality check")
                            print("\nFailed criteria:", ", ".join(result.failed_criteria))
                            print("\nFeedback:")
                            print(result.feedback)
                        
                        # Avoid rate limits
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Error in generation/testing loop: {str(e)}")
                        print(f"Full error: {type(e).__name__}: {str(e)}")
                        continue
                
                print(f"\nCompleted {lesson} {difficulty}: {good_examples}/{target_per_combination} good examples")
                if feedback_history:
                    print("\nFeedback collected for improvement:")
                    for idx, feedback in enumerate(feedback_history, 1):
                        print(f"{idx}. {feedback}")
        
        # Print final statistics
        print("\nGeneration complete!")
        print(f"Total questions generated: {total_generated}")
        print(f"Questions that passed QC: {total_passed}")
        print(f"Success rate: {(total_passed/total_generated)*100:.2f}%")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main() 