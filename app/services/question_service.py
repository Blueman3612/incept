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
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.api_key:
            raise ValueError("Missing OpenAI API key")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials")
            
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
        
        # Pre-calculated calibration curves from good examples
        # These values will be replaced with the results from calibration_results.json
        self.calibration_curves = {
            "completeness": 0.05,  # Example values, will update after calibration script runs
            "answer_quality": 0.05,
            "explanation_quality": 0.08,
            "language_quality": 0.10
        }
        
        # Mark as already calibrated since we're using pre-calculated values
        self.is_calibrated = True
        
        # Passing threshold (score needed to pass a criterion)
        self.passing_threshold = 0.99
        
        # Only run auto-calibration if specifically requested and we're not already using pre-calculated values
        self.auto_calibrate = False  # Disabled by default since we're using pre-calculated values
        
        # Initialize rubric with empty values, will be populated on first use
        self.rubric = {}
        self.example_patterns = {}
        self.good_examples_loaded = False
    
    async def calibrate_against_good_examples(self, sample_size=50, min_examples=10):
        """
        Calibrate the grading system by evaluating existing good examples and computing
        adjustment curves for each criterion.
        
        Args:
            sample_size: Maximum number of good examples to evaluate
            min_examples: Minimum number of examples needed for valid calibration
            
        Returns:
            dict: The computed calibration curves for each criterion
        """
        if self.is_calibrated:
            print("Grading system already calibrated")
            return self.calibration_curves
            
        print(f"Calibrating grading system against good examples...")
        
        # Get good examples from Supabase
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Query for good examples
            response = self.session.get(
                f"{self.supabase_url}/rest/v1/test_examples",
                headers=headers,
                params={
                    "quality_status": "eq.good",
                    "select": "content",
                    "limit": sample_size,
                    "order": "created_at.desc"  # Get the most recent examples
                }
            )
            
            if response.status_code != 200:
                print(f"Failed to fetch good examples: {response.status_code}")
                return self.calibration_curves
                
            examples = response.json()
            
            if len(examples) < min_examples:
                print(f"Not enough good examples for calibration (found {len(examples)}, need {min_examples})")
                return self.calibration_curves
                
            print(f"Found {len(examples)} good examples for calibration")
            
            # Collect scores for each criterion
            criterion_scores = {
                "completeness": [],
                "answer_quality": [],
                "explanation_quality": [],
                "language_quality": []
            }
            
            # Grade each example and collect scores
            for i, example in enumerate(examples):
                content = example.get("content")
                if not content:
                    continue
                
                # Create a request object for grading
                request = QuestionGradeRequest(question=content)
                
                # Temporarily disable calibration curves for this evaluation
                original_curves = self.calibration_curves.copy()
                self.calibration_curves = {k: 0.0 for k in self.calibration_curves}
                
                # Grade the example
                try:
                    # We want the raw scores without calibration applied
                    raw_scores = await self._evaluate_criteria(request.question)
                    
                    # Collect raw scores for each criterion
                    for criterion, score in raw_scores.items():
                        criterion_scores[criterion].append(score)
                        
                except Exception as e:
                    print(f"Error grading example {i}: {str(e)}")
                    continue
                
                # Restore original calibration curves
                self.calibration_curves = original_curves
                
            # Calculate average scores for each criterion
            avg_scores = {}
            for criterion, scores in criterion_scores.items():
                if scores:
                    avg_scores[criterion] = sum(scores) / len(scores)
                else:
                    avg_scores[criterion] = 0.0
                    
            # Calculate calibration curves (difference between threshold and average)
            for criterion, avg_score in avg_scores.items():
                # Only apply positive curves (we don't want to make scores worse)
                curve = max(0.0, self.passing_threshold - avg_score)
                self.calibration_curves[criterion] = round(curve, 3)
                
            print("Calibration completed. Adjustment curves:")
            for criterion, curve in self.calibration_curves.items():
                print(f"  • {criterion}: +{curve:.3f} (avg score was {avg_scores.get(criterion, 0):.3f})")
                
            self.is_calibrated = True
            return self.calibration_curves
            
        except Exception as e:
            print(f"Calibration error: {str(e)}")
            return self.calibration_curves
    
    async def _evaluate_criteria(self, question_text: str) -> Dict[str, float]:
        """Evaluate a question against all criteria.
        
        This internal method performs the raw evaluation without applying the calibration curve.
        """
        criterion_scores = {}
        
        for criterion in self.criteria:
            # Use the existing evaluation method but extract only the score
            score, _, _ = await self._evaluate_criterion(criterion, question_text)
            criterion_scores[criterion] = score
            
        return criterion_scores
    
    async def _get_scores_with_calibration(self, question_text: str) -> Dict[str, float]:
        """Evaluate a question against all criteria and apply calibration curves."""
        # Get raw scores
        raw_scores = await self._evaluate_criteria(question_text)
        
        # Apply calibration curves
        calibrated_scores = {}
        for criterion, score in raw_scores.items():
            # Apply the curve but cap at 1.0
            calibrated_score = min(1.0, score + self.calibration_curves.get(criterion, 0.0))
            calibrated_scores[criterion] = calibrated_score
            
        return calibrated_scores
    
    async def grade_question(self, request: QuestionGradeRequest) -> QuestionGradeResponse:
        """Grade a question based on quality criteria."""
        try:
            # Ensure rubric is initialized from good examples
            if not self.good_examples_loaded:
                await self.load_good_examples()
            
            # Get scores using the calibrated system
            raw_scores = await self._evaluate_criteria(request.question)
            
            # Apply calibration curves
            scores = {}
            for criterion, score in raw_scores.items():
                # Apply the curve but cap at 1.0
                scores[criterion] = min(1.0, score + self.calibration_curves.get(criterion, 0.0))
            
            # Collect detailed feedback and suggestions
            failed_criteria = []
            improvement_suggestions = {}
            overall_feedback = []
            
            # Evaluate each criterion for detailed feedback
            for criterion in self.criteria:
                # We've already calculated the score, but we need the feedback and suggestions
                raw_score, feedback, suggestions = await self._evaluate_criterion(criterion, request.question)
                calibrated_score = scores[criterion]
                
                if calibrated_score < self.passing_threshold:
                    failed_criteria.append(criterion)
                    improvement_suggestions[criterion] = suggestions
                
                # Include both raw and calibrated scores in feedback
                adjustment = self.calibration_curves.get(criterion, 0.0)
                if adjustment > 0:
                    score_info = f"(raw: {raw_score:.2f}, curve: +{adjustment:.2f}, final: {calibrated_score:.2f})"
                else:
                    score_info = f"(score: {calibrated_score:.2f})"
                    
                overall_feedback.append(f"{criterion} {score_info}: {feedback}")
            
            # Calculate overall score (weighted average of calibrated scores)
            total_weight = sum(c["weight"] for c in self.criteria.values())
            overall_score = sum(
                scores[c] * self.criteria[c]["weight"] 
                for c in scores
            ) / total_weight
            
            # Determine pass/fail
            passed = len(failed_criteria) == 0
            
            # Create detailed feedback
            feedback = "\n".join(overall_feedback) if overall_feedback else "All criteria passed!"
            
            # Add calibration information to feedback
            if any(curve > 0 for curve in self.calibration_curves.values()):
                calibration_info = "Calibration applied: "
                calibration_info += ", ".join([f"{c}: +{curve:.2f}" for c, curve in self.calibration_curves.items() if curve > 0])
                feedback = f"{calibration_info}\n\n{feedback}"
            
            return QuestionGradeResponse(
                passed=passed,
                overall_score=overall_score,
                criterion_scores=scores,
                failed_criteria=failed_criteria,
                feedback=feedback,
                improvement_suggestions=improvement_suggestions
            )
            
        except Exception as e:
            print(f"Error grading question: {str(e)}")
            return QuestionGradeResponse(
                passed=False,
                overall_score=0.0,
                criterion_scores={},
                failed_criteria=["error"],
                feedback=f"Error during grading: {str(e)}",
                improvement_suggestions={}
            )
    
    async def load_good_examples(self):
        """Load and analyze good examples from the test_examples table using direct REST API calls"""
        print("Loading good examples for rubric development...")
        
        # Skip calibration since we're using pre-calculated values
        # Comment out this block since calibration is now handled separately
        # if not self.is_calibrated:
        #     await self.calibrate_against_good_examples()
        
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Direct REST API call to Supabase (no client library needed)
            response = self.session.get(
                f"{self.supabase_url}/rest/v1/test_examples",
                headers=headers,
                params={
                    "quality_status": "eq.good",
                    "select": "content,quality_criterion,lesson,difficulty_level,metadata"
                }
            )
            
            response.raise_for_status()
            good_examples = response.json()
            
            if not good_examples:
                print("Warning: No good examples found in database")
                self._create_default_rubric()
                return
                
            print(f"Found {len(good_examples)} good examples for analysis")
            
            # Group examples by criterion for analysis
            examples_by_criterion = {}
            for example in good_examples:
                criterion = example.get("quality_criterion")
                if criterion not in examples_by_criterion:
                    examples_by_criterion[criterion] = []
                examples_by_criterion[criterion].append(example)
            
            # Generate rubric from examples
            self.rubric = self._generate_rubric_from_examples(examples_by_criterion)
            
            # Extract patterns for each criterion
            self.example_patterns = self._extract_patterns_from_examples(good_examples)
            
            self.good_examples_loaded = True
            print("Rubric and patterns generated successfully")
            
        except Exception as e:
            print(f"Error loading good examples: {str(e)}")
            # Create a basic rubric if loading fails
            self._create_default_rubric()
    
    def _generate_rubric_from_examples(self, examples_by_criterion):
        """Generate a detailed rubric from the analyzed examples"""
        rubric = {}
        
        # Analyze completeness examples
        completeness_examples = examples_by_criterion.get("question_stem", [])
        rubric["completeness"] = {
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
            ],
            "patterns": self._extract_specific_patterns(completeness_examples, "completeness")
        }
        
        # Analyze answer quality examples
        answer_examples = examples_by_criterion.get("correct_answer", []) + examples_by_criterion.get("distractors", [])
        rubric["answer_quality"] = {
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
            ],
            "patterns": self._extract_specific_patterns(answer_examples, "answer_quality")
        }
        
        # Analyze explanation quality examples
        explanation_examples = examples_by_criterion.get("distractors", [])
        rubric["explanation_quality"] = {
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
            ],
            "patterns": self._extract_specific_patterns(explanation_examples, "explanation_quality")
        }
        
        # Analyze language quality examples
        language_examples = examples_by_criterion.get("grammar", []) + examples_by_criterion.get("vocabulary", [])
        rubric["language_quality"] = {
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
            ],
            "patterns": self._extract_specific_patterns(language_examples, "language_quality")
        }
        
        return rubric
    
    def _extract_specific_patterns(self, examples, criterion_type):
        """Extract specific patterns from examples for a given criterion"""
        patterns = {
            "good_examples": [],
            "word_patterns": {},
            "structure_patterns": []
        }
        
        if not examples:
            return patterns
            
        for example in examples[:5]:  # Analyze up to 5 examples
            content = example.get("content", "")
            if content:
                # For language quality, extract sentence patterns
                if criterion_type == "language_quality":
                    sentences = re.findall(r'[A-Z][^.!?]*[.!?]', content)
                    good_sentences = [s for s in sentences if len(s.split()) < 15 and "," not in s]
                    patterns["good_examples"].extend(good_sentences[:3])
                    
                    # Count word frequency for vocabulary patterns
                    words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
                    for word in words:
                        if word not in patterns["word_patterns"]:
                            patterns["word_patterns"][word] = 0
                        patterns["word_patterns"][word] += 1
                
                # For other criteria, extract structural elements
                elif criterion_type == "completeness":
                    # Check for passage, question, options, explanation structure
                    has_passage = "Read the following passage" in content
                    has_mcq = all(f"{opt})" in content for opt in ["A", "B", "C", "D"])
                    has_solution = "Solution:" in content
                    
                    if has_passage and has_mcq and has_solution:
                        patterns["structure_patterns"].append({
                            "has_passage": has_passage,
                            "has_mcq": has_mcq,
                            "has_solution": has_solution
                        })
                
                # For answer quality, analyze distractors
                elif criterion_type == "answer_quality":
                    explanations = re.findall(r'[A-D]\) ([^\n]+)', content)
                    if explanations and len(explanations) >= 3:
                        # Check for similarity in option length
                        lengths = [len(exp) for exp in explanations]
                        if max(lengths) - min(lengths) < 20:  # Reasonable similarity
                            patterns["structure_patterns"].append({
                                "option_length_similarity": True,
                                "option_count": len(explanations)
                            })
                
                # For explanation quality, analyze explanation patterns
                elif criterion_type == "explanation_quality":
                    explanation_section = re.search(r'Explanation for wrong answers:(.*?)(?:Solution:|$)', 
                                                    content, re.DOTALL)
                    if explanation_section:
                        explanations = explanation_section.group(1)
                        patterns["good_examples"].append(explanations[:150])  # First 150 chars as sample
        
        # Extract most common words for vocabulary reference
        if criterion_type == "language_quality" and patterns["word_patterns"]:
            patterns["common_words"] = sorted(
                patterns["word_patterns"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20]
            
        return patterns
    
    def _extract_patterns_from_examples(self, examples):
        """Extract various patterns from all good examples"""
        patterns = {
            "passage_patterns": [],
            "question_patterns": [],
            "explanation_patterns": [],
            "solution_patterns": []
        }
        
        for example in examples[:20]:  # Analyze up to 20 examples
            content = example.get("content", "")
            
            # Extract passage examples
            passage_match = re.search(r'Read the following passage.*?\n\n(.*?)\n\n', content, re.DOTALL)
            if passage_match:
                passages = passage_match.group(1)
                if len(passages) > 20:  # Simple validation
                    patterns["passage_patterns"].append(passages[:150])  # Store first 150 chars
            
            # Extract question pattern
            question_match = re.search(r'\n\n([A-Za-z\s\',?]+\?)\n\n', content)
            if question_match:
                question = question_match.group(1)
                if len(question) > 10:
                    patterns["question_patterns"].append(question)
            
            # Extract explanation pattern
            explanation_match = re.search(r'Explanation for wrong answers:(.*?)(?:Solution:|$)', 
                                        content, re.DOTALL)
            if explanation_match:
                explanation = explanation_match.group(1)
                if len(explanation) > 20:
                    patterns["explanation_patterns"].append(explanation[:200])
            
            # Extract solution pattern
            solution_match = re.search(r'Solution:(.*?)(?:$)', content, re.DOTALL)
            if solution_match:
                solution = solution_match.group(1)
                if len(solution) > 20:
                    patterns["solution_patterns"].append(solution[:200])
        
        return patterns
        
    def _create_default_rubric(self):
        """Create a default rubric if no examples are available"""
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
                ],
                "patterns": {"good_examples": [], "structure_patterns": []}
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
                ],
                "patterns": {"good_examples": [], "structure_patterns": []}
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
                ],
                "patterns": {"good_examples": [], "structure_patterns": []}
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
                ],
                "patterns": {"good_examples": [], "structure_patterns": []}
            }
        }
        self.good_examples_loaded = True
    
    def _generate_feedback(self, question: str, scores: Dict[str, float]) -> str:
        """Generate a detailed feedback string based on the scores"""
        feedback = []
        for criterion, score in scores.items():
            feedback.append(f"{criterion}: {score:.2f}")
        return "\n".join(feedback)
    
    async def _evaluate_criterion(self, criterion: str, question: str) -> Tuple[float, str, List[str]]:
        """Evaluate a specific criterion using LLM and rubric"""
        
        # Include examples from our analysis if available
        example_text = ""
        if self.example_patterns:
            if criterion == "completeness" and self.example_patterns.get("question_patterns"):
                example_text += "\n\nExample good question patterns:\n" + "\n".join(
                    self.example_patterns.get("question_patterns", [])[:2]
                )
            elif criterion == "explanation_quality" and self.example_patterns.get("explanation_patterns"):
                example_text += "\n\nExample good explanation patterns:\n" + "\n".join(
                    self.example_patterns.get("explanation_patterns", [])[:1]
                )
            elif criterion == "language_quality" and self.rubric.get("language_quality", {}).get("patterns", {}).get("good_examples"):
                example_text += "\n\nExample good language patterns:\n" + "\n".join(
                    self.rubric.get("language_quality", {}).get("patterns", {}).get("good_examples", [])[:3]
                )
        
        system_prompt = f"""You are an expert evaluator of educational content for Grade 4 students.
You are analyzing a question specifically for the criterion: {criterion}.

The rubric for this criterion is:
Requirements:
{chr(10).join(f"- {req}" for req in self.rubric.get(criterion, {}).get("requirements", []))}

Common issues:
{chr(10).join(f"- {issue}" for issue in self.rubric.get(criterion, {}).get("common_issues", []))}
{example_text}

You will provide:
1. A score from 0.0 to 1.0, where 1.0 is perfect and 0.99+ is passing
2. Specific feedback on why the score was given
3. Concrete suggestions for improvement

IMPORTANT FOR LANGUAGE QUALITY: To score 0.99 or higher, the language must be exceptionally clear and consistently appropriate for Grade 4 students. Even minor ambiguities or complex sentences will result in scores of 0.95 or lower.
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