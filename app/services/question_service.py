from typing import Dict, List, Optional, Tuple
import json
import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import re
from app.schemas.question import (
    QuestionGradeRequest,
    QuestionGradeResponse,
    GradingCriterion
)


class QuestionService:
    """Service for question-related operations"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("Missing OpenAI API key")
            
        # Setup session with retry logic for API calls
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_maxsize=100, pool_connections=100)
        self.session.mount('https://', adapter)
        self.session.timeout = (10, 90)  # (connect timeout, read timeout)
        
        # Define grading criteria based on test examples analysis
        self.criteria = {
            "completeness": {
                "weight": 1.0,
                "description": "Question has all required parts (question stem, options, correct answer, explanations)"
            },
            "answer_quality": {
                "weight": 1.0,
                "description": "Answer options are appropriate, with one clearly correct answer and plausible distractors"
            },
            "explanation_quality": {
                "weight": 1.0,
                "description": "Explanations for right and wrong answers are thorough, accurate, and educational"
            },
            "language_quality": {
                "weight": 1.0,
                "description": "Language is grade-appropriate, clear, and unambiguous"
            }
        }
        
        # Initialize default rubric without depending on external DB
        self._create_default_rubric()
    
    async def grade_question(self, request: QuestionGradeRequest) -> QuestionGradeResponse:
        """Grade a question based on quality criteria"""
        
        # Perform grading on each criterion
        criterion_scores = {}
        failed_criteria = []
        improvement_suggestions = {}
        overall_feedback = []
        
        for criterion in self.criteria:
            score, feedback, suggestions = await self._evaluate_criterion(
                criterion, request.question
            )
            
            criterion_scores[criterion] = score
            if score < 0.99:  # Using 0.99 as passing threshold
                failed_criteria.append(criterion)
                improvement_suggestions[criterion] = suggestions
                overall_feedback.append(f"{criterion}: {feedback}")
        
        # Calculate overall score (weighted average)
        total_weight = sum(c["weight"] for c in self.criteria.values())
        overall_score = sum(
            criterion_scores[c] * self.criteria[c]["weight"] 
            for c in criterion_scores
        ) / total_weight
        
        # Determine overall pass/fail status
        passed = len(failed_criteria) == 0
        
        # Create detailed feedback
        feedback = "\n".join(overall_feedback) if overall_feedback else "All criteria passed!"
        
        return QuestionGradeResponse(
            passed=passed,
            overall_score=overall_score,
            criterion_scores=criterion_scores,
            failed_criteria=failed_criteria,
            feedback=feedback,
            improvement_suggestions=improvement_suggestions
        )
        
    def _create_default_rubric(self):
        """Create a default rubric"""
        self.rubric = {
            "completeness": {
                "requirements": [
                    "Question must have a clear passage or context",
                    "Question must have a clear prompt/stem",
                    "Must have exactly 4 answer options (A, B, C, D)",
                    "Must have a clearly marked correct answer",
                    "Must have explanations for all wrong answers",
                    "Must have a complete solution with steps"
                ],
                "common_issues": [
                    "Missing explanations for wrong answers",
                    "Incomplete solution steps",
                    "Unclear or ambiguous question stem"
                ]
            },
            "answer_quality": {
                "requirements": [
                    "Must have exactly one unambiguously correct answer",
                    "All distractors must be clearly incorrect but plausible",
                    "Distractors should represent common misconceptions or errors",
                    "Answer options should be similar in length and structure",
                    "Correct answer should not stand out visually or structurally"
                ],
                "common_issues": [
                    "Multiple potentially correct answers",
                    "Implausible or nonsensical distractors",
                    "Correct answer stands out (e.g., longest, most detailed)",
                    "Distractors too similar or too different from each other"
                ]
            },
            "explanation_quality": {
                "requirements": [
                    "Each wrong answer must have a specific explanation",
                    "Explanations must clarify why an answer is wrong",
                    "Explanations should be educational and reinforce correct concepts",
                    "Solution must provide clear step-by-step approach",
                    "Explanations must be accurate and factually correct"
                ],
                "common_issues": [
                    "Generic or vague explanations",
                    "Explanations that don't address the specific error",
                    "Missing steps in solution",
                    "Explanations that aren't educationally valuable"
                ]
            },
            "language_quality": {
                "requirements": [
                    "Language must be appropriate for Grade 4 students",
                    "Sentences should be clear, direct, and unambiguous",
                    "Complex terms must be explained or simplified",
                    "Grammar and spelling must be correct",
                    "Formatting must be consistent throughout"
                ],
                "common_issues": [
                    "Overly complex vocabulary",
                    "Long, complex sentences",
                    "Ambiguous wording or instructions",
                    "Technical terms without explanation"
                ]
            }
        }
    
    async def _evaluate_criterion(self, criterion: str, question: str) -> Tuple[float, str, List[str]]:
        """Evaluate a specific criterion using LLM and rubric"""
        
        system_prompt = f"""You are an expert evaluator of educational content for Grade 4 students.
You are analyzing a question specifically for the criterion: {criterion}.

The rubric for this criterion is:
Requirements:
{chr(10).join(f"- {req}" for req in self.rubric.get(criterion, {}).get("requirements", []))}

Common issues:
{chr(10).join(f"- {issue}" for issue in self.rubric.get(criterion, {}).get("common_issues", []))}

You will provide:
1. A score from 0.0 to 1.0, where 1.0 is perfect and 0.99+ is passing
2. Specific feedback on why the score was given
3. Concrete suggestions for improvement
"""

        user_prompt = f"""Analyze this Grade 4 question for {criterion}:

{question}

Evaluate thoroughly and provide:
1. SCORE: A precise score from 0.0 to 1.0 (e.g., 0.92, 0.97, 1.0)
2. FEEDBACK: Specific details on why this score was given
3. SUGGESTIONS: Concrete ways to improve if the score is below 0.99

Your response should be in JSON format with these exact keys:
{{
  "score": 0.0,
  "feedback": "detailed feedback here",
  "suggestions": ["suggestion 1", "suggestion 2"]
}}"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": "gpt-4-turbo-preview",
                    "messages": messages,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=(30, 120)  # Allow longer timeout for evaluation
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse the response content
            content = result["choices"][0]["message"]["content"]
            evaluation = json.loads(content)
            
            score = float(evaluation.get("score", 0))
            feedback = evaluation.get("feedback", "No feedback provided")
            suggestions = evaluation.get("suggestions", [])
            
            # Ensure score is within bounds
            score = max(0.0, min(1.0, score))
            
            return score, feedback, suggestions
            
        except Exception as e:
            print(f"Error evaluating criterion {criterion}: {str(e)}")
            return 0.0, f"Error during evaluation: {str(e)}", ["Try again later"] 