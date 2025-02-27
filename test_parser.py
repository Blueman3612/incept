import json
from generate_and_upload_questions import parse_question_content

test_content = '''Read the following passage and answer the question.

"Cultures around the world are very different. In Japan, people bow to say hello. In Mexico, people celebrate the Day of the Dead to honor their loved ones who have passed away. Many people think that Italian food is the tastiest."

Which of the following is a fact from the passage?

A) People bow to say hello in Japan.
B) Mexican culture is the most colorful.
C) Italian food is the tastiest.
D) Japanese people always prefer bowing to saying hello.

Correct Answer: A) People bow to say hello in Japan.

Explanation for wrong answers:
A) This is the correct answer. It's a fact stated in the passage.
B) The passage does not provide any information about Mexican culture being the most colorful. This is an opinion.
C) The statement that Italian food is the tastiest is an opinion, not a fact. Different people have different tastes in food.
D) The passage states that people in Japan bow to say hello, but it does not say that they always prefer this to saying hello verbally.

Solution:
1. Read the question carefully to understand what it's asking.
2. Read the passage again to find facts and separate them from opinions.
3. Compare the options with the facts in the passage.
4. Choose the option that is a fact stated in the passage.'''

# Test the parsing
result = parse_question_content(test_content, 'Reading Fluency', 'easy')

# Write results to a file
with open('parser_test_results.txt', 'w') as f:
    f.write(f"PARSED QUESTION COMPONENTS:\n\n")
    f.write(f"STIMULI:\n{result['stimuli']}\n\n")
    f.write(f"PROMPT:\n{result['prompt']}\n\n")
    f.write(f"ANSWER CHOICES:\n{json.dumps(result['answer_choices'], indent=2)}\n\n")
    f.write(f"CORRECT ANSWER:\n{result['correct_answer']}\n\n")
    f.write(f"WRONG ANSWER EXPLANATIONS:\n{json.dumps(result['wrong_answer_explanations'], indent=2)}\n\n")
    f.write(f"SOLUTION:\n{result['solution']}\n\n")

print("Results written to parser_test_results.txt") 