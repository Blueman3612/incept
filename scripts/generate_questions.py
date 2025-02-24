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
import random
import re

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

def save_example(session, supabase_url: str, headers: dict, example: dict) -> dict:
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
        
        # First save with minimal return
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
        print(f"✗ Error saving example: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"Response text: {e.response.text}")
        return None

def get_historical_feedback(session, supabase_url: str, headers: dict, lesson: str, difficulty: str) -> dict:
    """Get feedback and successful patterns from previous examples"""
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
            
            # Extract successful language patterns
            successful_patterns = {
                "passages": [],
                "explanations": [],
                "solutions": []
            }
            
            language_rules = set()  # Cumulative language rules
            
            for example in examples:
                metadata = example.get("metadata", {})
                scores = metadata.get("scores", {})
                
                # If language_quality score is high, extract the patterns
                if scores.get("language_quality", 0) >= 0.99:
                    content = example.get("content", "")
                    
                    # Extract successful passage
                    passage_match = re.search(r'Read the following passage.*?\n\n(.*?)\n\n', content, re.DOTALL)
                    if passage_match:
                        successful_patterns["passages"].append(passage_match.group(1))
                    
                    # Extract successful explanations
                    explanation_match = re.search(r'Explanation for wrong answers:\n(.*?)\n\nSolution:', content, re.DOTALL)
                    if explanation_match:
                        successful_patterns["explanations"].append(explanation_match.group(1))
                    
                    # Extract successful solutions
                    solution_match = re.search(r'Solution:\n(.*?)$', content, re.DOTALL)
                    if solution_match:
                        successful_patterns["solutions"].append(solution_match.group(1))
                
                # Collect language rules from feedback
                if metadata.get("feedback", {}).get("language_quality"):
                    feedback = metadata["feedback"]["language_quality"]
                    rules = re.findall(r'(?:avoid|use|keep|make|ensure).*?(?:\.|\n)', feedback.lower())
                    language_rules.update(rules)
            
            return {
                "successful_patterns": successful_patterns,
                "language_rules": list(language_rules)
            }
            
        return {"successful_patterns": {}, "language_rules": []}
            
    except Exception as e:
        print(f"❌ History loading error: {str(e)}")
        return {"successful_patterns": {}, "language_rules": []}

def generate_question(qc_service: QualityControlService, lesson: str, difficulty: str, feedback_history: list, historical_data: dict = None) -> str:
    """Generate a new question using GPT-4 with improved language learning"""
    
    # Extract language patterns from history
    successful_patterns = historical_data.get("successful_patterns", {})
    language_rules = historical_data.get("language_rules", [])
    
    # Build language guidance from successful patterns and rules
    language_guidance = "Language Requirements:\n"
    
    if language_rules:
        language_guidance += "Follow these specific rules:\n"
        language_guidance += "\n".join(f"- {rule}" for rule in language_rules[:5])
        language_guidance += "\n"
    
    if successful_patterns.get("passages"):
        language_guidance += "\nExample of good passage structure:\n"
        language_guidance += successful_patterns["passages"][-1]  # Use most recent successful passage
    
    # Rest of the context selection logic...
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
    
    structures = [
        "What is the main idea of this passage?",
        "Which detail best supports the main idea?",
        "What is the author's purpose in writing this passage?",
        "What is the most important information in the passage?",
        "Which sentence best summarizes the passage?"
    ]
    
    prompt = f"""Generate a Grade 4 Language Arts question for the lesson on "{lesson}" at {difficulty} difficulty level.

{language_guidance}

Content Requirements:
1. Write a passage about {selected_context}
2. Use {random.choice(structures)} as your question
3. Create 4 multiple choice options
4. Include brief explanations
5. Provide 3-4 solution steps

Format:
Read the following passage and answer the question.

[Passage]

[Question]

A) [Option]
B) [Option]
C) [Option]
D) [Option]

Correct Answer: [Letter]

Explanation for wrong answers:
[One clear sentence per wrong answer]

Solution:
[3-4 simple steps]"""

    return qc_service._generate_with_gpt(prompt)

def extract_feedback(result: QualityCheckResult) -> list:
    """Extract actionable feedback from quality check results"""
    feedback = []
    
    # Extract passage topic for variety tracking
    content = result.content if hasattr(result, 'content') else ""
    if content:
        passage_match = re.search(r'Read the following passage.*?\n\n(.*?)\n\n', content, re.DOTALL)
        if passage_match:
            passage = passage_match.group(1)
            feedback.append(f"Previous passage about: {passage}")
    
    # Extract specific feedback by criterion
    for criterion, score in result.criterion_scores.items():
        if score < 0.99:
            criterion_feedback = result.feedback.split(f"{criterion}:", 1)
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

def main():
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
    qc_service = QualityControlService()
    
    # Setup Supabase
    setup_supabase(session, supabase_url, headers)
    
    lessons = ["main_idea", "supporting_details", "authors_purpose"]
    difficulties = ["easy", "medium", "hard"]
    target_per_combination = 5
    
    total_generated = 0
    total_passed = 0
    
    try:
        for lesson in lessons:
            for difficulty in difficulties:
                print(f"\n🎯 {lesson.upper()} - {difficulty.upper()}")
                print("=" * 40)
                
                historical_data = get_historical_feedback(session, supabase_url, headers, lesson, difficulty)
                
                good_examples = 0
                attempts = 0
                max_attempts = 20
                feedback_history = []
                
                while good_examples < target_per_combination and attempts < max_attempts:
                    attempts += 1
                    total_generated += 1
                    
                    print(f"\n📝 Attempt {attempts}/{max_attempts} ({good_examples}/{target_per_combination} passed)")
                    
                    try:
                        content = generate_question(qc_service, lesson, difficulty, feedback_history, historical_data)
                        
                        # Check quality
                        result = qc_service.check_quality(content)
                        
                        # Simplified results display
                        scores = result.criterion_scores
                        print("\n📊 Scores:")
                        for criterion, score in scores.items():
                            status = "✅" if score >= 0.99 else "❌"
                            print(f"{status} {criterion}: {score:.2f}")
                        
                        if not result.passed:
                            print("\n❗ Failed criteria:", ", ".join(result.failed_criteria))
                        
                        # Save example
                        example = {
                            "content": content,
                            "quality_status": "good" if result.passed else "bad",
                            "quality_criterion": "completeness",
                            "mutation_type": "original",
                            "lesson": lesson,
                            "difficulty_level": difficulty,
                            "metadata": {
                                "scores": {k: round(v, 2) for k, v in scores.items()},
                                "failed_criteria": result.failed_criteria,
                                "feedback": {
                                    criterion: feedback.strip()
                                    for criterion, feedback in [f.split(':', 1) for f in result.feedback.split('\n') if ':' in f]
                                } if result.feedback else {}
                            }
                        }
                        
                        saved_example = save_example(session, supabase_url, headers, example)
                        
                        if result.passed:
                            good_examples += 1
                            total_passed += 1
                            print("\n✨ Question passed!")
                            
                            # Generate mutations (simplified output)
                            print("🧬 Generating mutations...")
                            mutations = qc_service.generate_mutations(TestExample(**example))
                            for mutation in mutations:
                                mutation_dict = mutation.dict()
                                mutation_dict.pop('id', None)
                                if saved_example and saved_example.get("id"):
                                    mutation_dict["metadata"] = {
                                        "mutation_from": saved_example["id"],
                                        "mutation_type": mutation_dict["mutation_type"].lower()
                                    }
                                save_example(session, supabase_url, headers, mutation_dict)
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"❌ Error: {str(e)}")
                        continue
                
                print(f"\n📋 Summary for {lesson}/{difficulty}:")
                print(f"✓ Generated {good_examples}/{target_per_combination} good examples")
        
        # Final stats
        print("\n🏁 Generation complete!")
        print(f"📊 Success rate: {(total_passed/total_generated)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 