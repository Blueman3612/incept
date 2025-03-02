import os
import json
import logging
import openai
from typing import Dict, List, Tuple, Any, Optional
import re
from datetime import datetime

logger = logging.getLogger(__name__)

def preprocess_article_content(content: str) -> str:
    """
    Preprocesses article content to ensure consistent formatting and structure.
    
    Args:
        content: The raw article content
        
    Returns:
        Preprocessed article content
    """
    # Remove excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r' {2,}', ' ', content)
    
    # Ensure content ends with a newline
    if not content.endswith('\n'):
        content += '\n'
        
    return content.strip()


class ArticleQualityGrader:
    """
    Evaluates the quality of educational articles based on predefined criteria.
    Uses OpenAI's GPT-4 to analyze content and provide quality scores and feedback.
    """
    
    def __init__(self):
        """Initialize the ArticleQualityGrader with API settings."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.model = os.getenv("GPT_MODEL", "gpt-4")
        
        # Strict thresholds for quality assurance
        self.passing_threshold = 0.85  # Overall passing threshold
        self.minimum_criterion_threshold = 0.75  # Any criterion below this fails automatically
        self.critical_criteria = ["instructional_style", "worked_examples", "content_accuracy"]
        self.critical_threshold = 0.90  # Higher threshold for critical criteria
        
        # Define the scoring rubric for each quality criterion
        self.rubric = {
            "categorization": {
                "description": "Appropriate subject, grade, standard, and lesson categorization",
                "components": [
                    "Subject accuracy",
                    "Grade level accuracy", 
                    "Standard alignment", 
                    "Lesson specificity"
                ],
                "critical_issues": [
                    "Incorrect subject area",
                    "Wrong grade level",
                    "Misaligned with standard",
                    "Not specific to lesson objectives"
                ],
                "weight": 1.0
            },
            "instructional_style": {
                "description": "Explicitly teaches in Direct Instruction style with clear procedures",
                "components": [
                    "Direct instruction approach",
                    "Clear conceptual explanations",
                    "Procedural guidance",
                    "Scaffolded learning structure"
                ],
                "critical_issues": [
                    "Uses inquiry-based approach instead of direct instruction",
                    "Concepts explained vaguely or incompletely",
                    "Missing step-by-step procedures",
                    "No scaffolding for complex concepts"
                ],
                "weight": 1.2  # Weighted higher as critical criterion
            },
            "worked_examples": {
                "description": "Contains effective worked examples for all difficulty levels",
                "components": [
                    "Step breakdown for lower working memory",
                    "Examples for easy concepts",
                    "Examples for medium concepts",
                    "Examples for hard concepts"
                ],
                "critical_issues": [
                    "Steps not broken down adequately",
                    "Missing examples for key concepts",
                    "Examples don't prepare for all difficulty levels",
                    "Examples too complex for grade level"
                ],
                "weight": 1.2  # Weighted higher as critical criterion
            },
            "content_accuracy": {
                "description": "Content is factually accurate and free of misconceptions",
                "components": [
                    "Factual correctness",
                    "No conceptual errors",
                    "Accurate definitions",
                    "Correct procedures"
                ],
                "critical_issues": [
                    "Contains factual errors",
                    "Presents misconceptions",
                    "Incorrect definitions",
                    "Erroneous procedures"
                ],
                "weight": 1.2  # Weighted higher as critical criterion
            },
            "language_appropriateness": {
                "description": "Grade-level vocabulary and sentence structure",
                "components": [
                    "Age-appropriate vocabulary",
                    "Appropriate sentence complexity",
                    "Defined technical terms",
                    "Consistent terminology"
                ],
                "critical_issues": [
                    "Vocabulary too advanced for grade level",
                    "Overly complex sentence structures",
                    "Undefined technical terms",
                    "Inconsistent terminology"
                ],
                "weight": 1.0
            },
            "clarity": {
                "description": "Clear, direct, and unambiguous explanations",
                "components": [
                    "Clear explanations",
                    "Direct language",
                    "Unambiguous terminology",
                    "Logical flow"
                ],
                "critical_issues": [
                    "Confusing explanations",
                    "Indirect or vague language",
                    "Ambiguous terminology",
                    "Illogical organization"
                ],
                "weight": 1.0
            },
            "formatting": {
                "description": "Properly formatted with visual organization",
                "components": [
                    "Consistent headings",
                    "Appropriate paragraph breaks",
                    "Visual aids when needed",
                    "Clean layout"
                ],
                "critical_issues": [
                    "Inconsistent heading structure",
                    "Wall of text without breaks",
                    "Missing visual aids where needed",
                    "Cluttered or disorganized layout"
                ],
                "weight": 0.8  # Slightly lower weight as less critical
            },
            "content_consistency": {
                "description": "Uniform explanations across related lessons",
                "components": [
                    "Consistent terminology with prerequisites",
                    "Builds on previous concepts",
                    "Consistent explanation methods",
                    "Reinforces key principles"
                ],
                "critical_issues": [
                    "Terminology differs from related lessons",
                    "Contradicts previous lesson content",
                    "Inconsistent explanation methods",
                    "Fails to reinforce key principles"
                ],
                "weight": 1.0
            }
        }
    
    def grade_content(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluates the quality of educational article content.
        
        Args:
            content: The article content to evaluate
            metadata: Optional metadata about the article (grade level, subject, etc.)
            
        Returns:
            Dictionary containing evaluation results, including:
            - overall_score: Float representing overall quality score
            - criterion_scores: Dictionary of individual criterion scores
            - criterion_feedback: Dictionary of feedback for each criterion
            - critical_issues: List of critical issues found
            - passing: Boolean indicating if content meets quality standards
            - feedback: String containing overall feedback and improvement suggestions
        """
        try:
            # Preprocess the content
            content = preprocess_article_content(content)
            
            # Extract metadata
            grade_level = metadata.get("grade_level", 4) if metadata else 4
            subject = metadata.get("subject", "Language Arts") if metadata else "Language Arts"
            
            # Evaluate content with LLM
            criterion_scores, criterion_feedback, critical_issues, overall_score = self._evaluate_with_llm(
                content, grade_level, subject
            )
            
            # Determine if content passes quality standards
            passing = self._determine_passing(criterion_scores, overall_score, critical_issues)
            
            # Generate overall feedback
            feedback = self._generate_feedback(criterion_scores, criterion_feedback, critical_issues, passing)
            
            # Format and return results
            return {
                "overall_score": round(overall_score, 2),
                "criterion_scores": {k: round(v, 2) for k, v in criterion_scores.items()},
                "criterion_feedback": criterion_feedback,
                "critical_issues": critical_issues,
                "passing": passing,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in grading article content: {str(e)}")
            return self._default_error_response()
    
    def _evaluate_with_llm(self, content: str, grade_level: int, subject: str) -> Tuple[Dict[str, float], Dict[str, str], List[str], float]:
        """
        Uses LLM to evaluate content quality based on defined criteria.
        
        Args:
            content: The article content to evaluate
            grade_level: The target grade level of the content
            subject: The subject area of the content
            
        Returns:
            Tuple containing:
            - criterion_scores: Dictionary mapping criteria to scores
            - criterion_feedback: Dictionary mapping criteria to feedback
            - critical_issues: List of critical issues identified
            - overall_score: Weighted average of criterion scores
        """
        try:
            # Build the evaluation prompt
            prompt = self._build_evaluation_prompt(content, grade_level, subject)
            
            # Call the OpenAI API
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educational content evaluator with deep knowledge of Direct Instruction teaching methods and language arts curriculum for elementary education."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent evaluations
                max_tokens=3000
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            # Parse the evaluation results
            return self._parse_evaluation_response(response_text)
        except Exception as e:
            logger.error(f"Error in LLM evaluation: {str(e)}")
            return self._default_error_response()
    
    def _build_evaluation_prompt(self, content: str, grade_level: int, subject: str) -> str:
        """
        Builds a detailed prompt for the LLM to evaluate article quality.
        
        Args:
            content: The article content to evaluate
            grade_level: The target grade level of the content
            subject: The subject area of the content
            
        Returns:
            Formatted prompt string
        """
        # Construct criteria-specific evaluation instructions
        criteria_instructions = ""
        for criterion, details in self.rubric.items():
            criteria_instructions += f"""
### {criterion.replace('_', ' ').title()} (0.0-1.0):
Description: {details['description']}
Components to evaluate:
{chr(10).join([f"- {comp}" for comp in details['components']])}

Critical issues to identify:
{chr(10).join([f"- {issue}" for issue in details['critical_issues']])}

"""
        
        # Build the complete evaluation prompt
        prompt = f"""
You are evaluating a Grade {grade_level} {subject} educational article against strict quality criteria.

EVALUATION TASK:
Analyze the educational article below meticulously against each criterion, providing:
1. A numerical score (0.0-1.0) for each criterion
2. Brief, specific justification for each score
3. Critical issues identified, if any

ARTICLE TO EVALUATE:
```
{content}
```

EVALUATION CRITERIA:
{criteria_instructions}

RESPONSE FORMAT:
For each criterion, provide:
- Score: [numerical value between 0.0-1.0]
- Justification: [brief explanation]
- Issues: [list specific issues, if any]

Then provide:
- Critical Issues: [list all critical issues identified across criteria]
- Overall Weighted Score: [calculated weighted average]

Your evaluation should be detailed, specific, and actionable. Focus especially on the Direct Instruction style, worked examples quality, and content accuracy.
"""
        return prompt
    
    def _parse_evaluation_response(self, response_text: str) -> Tuple[Dict[str, float], Dict[str, str], List[str], float]:
        """
        Parses the LLM response to extract scores, feedback, and issues.
        
        Args:
            response_text: The raw text response from the LLM
            
        Returns:
            Tuple containing criterion scores, feedback, critical issues, and overall score
        """
        try:
            # Initialize dictionaries and lists
            criterion_scores = {}
            criterion_feedback = {}
            critical_issues = []
            
            # Extract scores and feedback for each criterion
            for criterion in self.rubric.keys():
                # Create patterns to match scores and justifications
                criterion_title = criterion.replace('_', ' ').title()
                score_pattern = rf"{criterion_title}.*?Score:\s*([0-9]\.[0-9]+)"
                justification_pattern = rf"{criterion_title}.*?Justification:\s*(.*?)(?=Issues:|$|[A-Z][a-z]+:)"
                issues_pattern = rf"{criterion_title}.*?Issues:\s*(.*?)(?=\n\n|\n[A-Z]|$)"
                
                # Extract score
                score_match = re.search(score_pattern, response_text, re.DOTALL | re.IGNORECASE)
                if score_match:
                    criterion_scores[criterion] = float(score_match.group(1))
                else:
                    criterion_scores[criterion] = 0.5  # Default score if not found
                
                # Extract justification
                justification_match = re.search(justification_pattern, response_text, re.DOTALL | re.IGNORECASE)
                if justification_match:
                    criterion_feedback[criterion] = justification_match.group(1).strip()
                else:
                    criterion_feedback[criterion] = "No specific feedback provided."
                
                # Extract issues for this criterion
                issues_match = re.search(issues_pattern, response_text, re.DOTALL | re.IGNORECASE)
                if issues_match and issues_match.group(1).strip() and "none" not in issues_match.group(1).lower():
                    criterion_issues = [issue.strip() for issue in issues_match.group(1).split('-') if issue.strip()]
                    critical_issues.extend(criterion_issues)
            
            # Extract overall list of critical issues
            overall_issues_pattern = r"Critical Issues:\s*(.*?)(?=\n\n|Overall Weighted Score:|$)"
            overall_issues_match = re.search(overall_issues_pattern, response_text, re.DOTALL | re.IGNORECASE)
            if overall_issues_match:
                issues_text = overall_issues_match.group(1).strip()
                if issues_text and "none" not in issues_text.lower():
                    # Split by bullet points or numbers
                    extracted_issues = re.findall(r'(?:^|\n)(?:\-|\d+\.)\s*(.*?)(?=$|\n)', issues_text)
                    if extracted_issues:
                        for issue in extracted_issues:
                            if issue.strip() and issue.strip() not in critical_issues:
                                critical_issues.append(issue.strip())
            
            # Calculate weighted overall score
            total_weight = sum(self.rubric[criterion]['weight'] for criterion in criterion_scores.keys())
            weighted_sum = sum(criterion_scores[criterion] * self.rubric[criterion]['weight'] 
                              for criterion in criterion_scores.keys())
            overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
            
            return criterion_scores, criterion_feedback, critical_issues, overall_score
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {str(e)}")
            return self._default_error_response()
    
    def _determine_passing(self, criterion_scores: Dict[str, float], overall_score: float, critical_issues: List[str]) -> bool:
        """
        Determines if the content passes quality standards based on scores and critical issues.
        
        Args:
            criterion_scores: Dictionary of scores for each criterion
            overall_score: Overall weighted score
            critical_issues: List of critical issues identified
            
        Returns:
            Boolean indicating if content passes quality standards
        """
        # Check if overall score meets passing threshold
        if overall_score < self.passing_threshold:
            return False
        
        # Check if any criterion is below minimum threshold
        for criterion, score in criterion_scores.items():
            if score < self.minimum_criterion_threshold:
                return False
        
        # Check if any critical criterion is below critical threshold
        for criterion in self.critical_criteria:
            if criterion in criterion_scores and criterion_scores[criterion] < self.critical_threshold:
                return False
        
        # Check if any critical issues were identified
        if critical_issues:
            return False
        
        return True
    
    def _generate_feedback(self, 
                          criterion_scores: Dict[str, float], 
                          criterion_feedback: Dict[str, str], 
                          critical_issues: List[str], 
                          passing: bool) -> str:
        """
        Generates comprehensive feedback about the content quality.
        
        Args:
            criterion_scores: Dictionary of scores for each criterion
            criterion_feedback: Dictionary of feedback for each criterion
            critical_issues: List of critical issues identified
            passing: Boolean indicating if content passes quality standards
            
        Returns:
            Formatted feedback string
        """
        # Start with overall assessment
        if passing:
            feedback = "✅ This article meets the quality standards for educational content.\n\n"
        else:
            feedback = "❌ This article does not meet the quality standards for educational content.\n\n"
        
        # Add strengths
        strengths = [f"{criterion.replace('_', ' ').title()}: {criterion_feedback[criterion]}" 
                    for criterion, score in criterion_scores.items() 
                    if score >= self.passing_threshold]
        
        if strengths:
            feedback += "Strengths:\n" + "\n".join([f"- {strength}" for strength in strengths]) + "\n\n"
        
        # Add areas for improvement
        improvements = [f"{criterion.replace('_', ' ').title()} ({score:.2f}): {criterion_feedback[criterion]}" 
                       for criterion, score in criterion_scores.items() 
                       if score < self.passing_threshold]
        
        if improvements:
            feedback += "Areas for Improvement:\n" + "\n".join([f"- {improvement}" for improvement in improvements]) + "\n\n"
        
        # Add critical issues
        if critical_issues:
            feedback += "Critical Issues to Address:\n" + "\n".join([f"- {issue}" for issue in critical_issues]) + "\n\n"
        
        # Add guidance for improvement
        if not passing:
            feedback += """
Improvement Guidelines:
1. Focus first on addressing the critical issues identified above
2. Pay special attention to Instructional Style, Worked Examples, and Content Accuracy
3. Ensure the article follows Direct Instruction principles with explicit teaching
4. Break down worked examples into clear steps for students with lower working memory
5. Verify that all content is factually accurate and grade-level appropriate
"""
        
        return feedback
    
    def _default_error_response(self) -> Tuple[Dict[str, float], Dict[str, str], List[str], float]:
        """
        Provides default values in case of evaluation error.
        
        Returns:
            Default tuple of empty criterion scores, feedback, critical issues, and zero overall score
        """
        default_scores = {criterion: 0.0 for criterion in self.rubric.keys()}
        default_feedback = {criterion: "Evaluation error" for criterion in self.rubric.keys()}
        default_issues = ["Evaluation could not be completed"]
        return default_scores, default_feedback, default_issues, 0.0


def grade_article(content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main function to grade article content.
    
    Args:
        content: The article content to evaluate
        metadata: Optional metadata about the article
        
    Returns:
        Evaluation results dictionary
    """
    grader = ArticleQualityGrader()
    return grader.grade_content(content, metadata) 