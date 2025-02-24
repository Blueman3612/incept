from typing import List, Dict, Optional, Tuple
import json
import requests
from datetime import datetime
from app.models.test_harness import (
    TestExample,
    QualityCheckResult,
    QualityMetrics,
    QualityCriterion,
    QualityStatus,
    MutationType
)
import os
from dotenv import load_dotenv

class QualityControlService:
    """Service for evaluating question quality against strict criteria"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing OpenAI API key")
        self.metrics = QualityMetrics()
        
        # Define evaluation criteria and their weights
        self.criteria = {
            "completeness": {
                "weight": 1.0,
                "prompt": """Evaluate if the question has all required parts:
                1. Clear question stem
                2. Multiple choice options (A, B, C, D)
                3. Designated correct answer
                4. Wrong answer explanations
                5. Step-by-step solution
                
                Return a JSON with:
                {
                    "score": float between 0-1,
                    "missing_parts": list of missing elements,
                    "feedback": specific improvement suggestions
                }
                """
            },
            "answer_quality": {
                "weight": 1.0,
                "prompt": """Evaluate the quality of answers:
                1. Correct answer is accurate for the question
                2. No distractors can be considered correct
                3. At least 2 distractors are plausible
                4. Correct answer doesn't stand out (length, format, etc.)
                
                Return a JSON with:
                {
                    "score": float between 0-1,
                    "issues": list of identified issues,
                    "feedback": specific improvement suggestions
                }
                """
            },
            "explanation_quality": {
                "weight": 1.0,
                "prompt": """Evaluate the quality of explanations:
                1. Clear explanation for each wrong answer
                2. Students can learn from wrong answer explanations
                3. Solution provides clear step-by-step guidance
                
                Return a JSON with:
                {
                    "score": float between 0-1,
                    "weak_points": list of areas needing improvement,
                    "feedback": specific improvement suggestions
                }
                """
            },
            "language_quality": {
                "weight": 1.0,
                "prompt": """Evaluate the language quality for Grade 4:
                1. Grade-level appropriate vocabulary
                2. Clear and unambiguous wording
                3. Grammatically correct
                4. Properly formatted
                
                Return a JSON with:
                {
                    "score": float between 0-1,
                    "issues": list of language issues,
                    "feedback": specific improvement suggestions
                }
                """
            }
        }
    
    def _call_openai(self, messages, temperature=0.2, response_format=None):
        """Make a request to OpenAI's chat completions API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4-turbo-preview",
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            data["response_format"] = response_format
            
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def check_quality(self, content: str) -> QualityCheckResult:
        """
        Check the quality of a question against all criteria
        Returns a QualityCheckResult with detailed feedback
        """
        result = QualityCheckResult()
        total_score = 0
        all_feedback = []
        
        for criterion, config in self.criteria.items():
            # Construct the evaluation prompt
            prompt = f"""As a strict educational content evaluator for Grade 4 Language Arts, evaluate this question:

{content}

{config['prompt']}"""
            
            try:
                completion = self._call_openai(
                    messages=[
                        {"role": "system", "content": "You are a strict educational content evaluator that ensures 99% precision in content quality."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={ "type": "json_object" }
                )
                
                # Parse the JSON response
                response_data = json.loads(completion['choices'][0]['message']['content'])
                score = float(response_data.get("score", 0))
                feedback = response_data.get("feedback", "No specific feedback provided")
                
                # Weight the score
                weighted_score = score * config["weight"]
                total_score += weighted_score
                result.criterion_scores[criterion] = score
                
                if score < 0.9:  # We require very high quality
                    result.failed_criteria.append(criterion)
                    all_feedback.append(f"{criterion}: {feedback}")
            
            except Exception as e:
                print(f"Error evaluating {criterion}: {str(e)}")
                result.criterion_scores[criterion] = 0
                result.failed_criteria.append(criterion)
                all_feedback.append(f"Error evaluating {criterion}")
        
        # Calculate final score (average of weighted scores)
        final_score = total_score / len(self.criteria)
        
        # We require 99% precision, so the threshold is very high
        result.passed = final_score >= 0.99
        result.feedback = "\n".join(all_feedback) if all_feedback else "All quality criteria passed!"
        
        return result
    
    def generate_mutations(self, example: TestExample) -> List[TestExample]:
        """
        Generate bad examples by mutating a good example
        Returns a list of mutated examples
        """
        mutations = []
        
        mutation_prompts = {
            MutationType.VOCABULARY_MUTATION: """
                Modify this question to use inappropriate vocabulary for Grade 4:
                {content}
            """,
            MutationType.STEM_MUTATION: """
                Make this question stem unclear or ambiguous:
                {content}
            """,
            # Add other mutation prompts...
        }
        
        for mutation_type, prompt in mutation_prompts.items():
            formatted_prompt = prompt.format(content=example.content)
            completion = self._call_openai(
                messages=[
                    {"role": "system", "content": "You are an educational content generator for Grade 4 Language Arts."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.7
            )
            mutated_content = completion['choices'][0]['message']['content']
            
            mutations.append(
                TestExample(
                    content=mutated_content,
                    quality_status=QualityStatus.BAD,
                    quality_criterion=example.quality_criterion,
                    mutation_type=mutation_type,
                    lesson=example.lesson,
                    difficulty_level=example.difficulty_level,
                    metadata={"original_id": example.id}
                )
            )
        
        return mutations
    
    def update_metrics(self, check_result: QualityCheckResult):
        """Update quality metrics based on a new check result"""
        self.metrics.total_examples += 1
        if check_result.passed:
            self.metrics.good_examples += 1
        else:
            self.metrics.bad_examples += 1
            
        # Update precision, recall, and F1 score
        if self.metrics.total_examples > 0:
            self.metrics.precision = self.metrics.good_examples / self.metrics.total_examples
            # Note: Recall would require ground truth data
            if self.metrics.precision > 0:  # Avoid division by zero
                self.metrics.f1_score = 2 * (self.metrics.precision * self.metrics.recall) / (self.metrics.precision + self.metrics.recall)
        
        # Update criterion-specific metrics
        for criterion, score in check_result.criterion_scores.items():
            if criterion not in self.metrics.metrics_by_criterion:
                self.metrics.metrics_by_criterion[criterion] = {"total": 0, "passed": 0}
            self.metrics.metrics_by_criterion[criterion]["total"] += 1
            if score >= 0.9:
                self.metrics.metrics_by_criterion[criterion]["passed"] += 1
                
        self.metrics.last_updated = datetime.utcnow()
    
    def _generate_with_gpt(self, prompt: str) -> str:
        """Generate content using GPT-4"""
        try:
            response = self._call_openai(
                messages=[
                    {"role": "system", "content": "You are an educational content generator for Grade 4 Language Arts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            raise Exception(f"Error generating with GPT: {str(e)}") 