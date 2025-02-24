import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Example questions for test harness
GOOD_EXAMPLE = {
    "content": """What is the main idea of the following paragraph?

The rainforest is home to many different types of animals. Colorful birds fly through the tall trees. Monkeys swing from branch to branch. Jaguars hunt on the forest floor. All these animals depend on the rainforest for food and shelter.

A) The rainforest has tall trees
B) Many animals live in the rainforest and depend on it
C) Jaguars are good hunters
D) Birds are colorful in the rainforest

Correct Answer: B
Wrong Answer Explanations:
A) While the text mentions tall trees, this is just one detail supporting the main idea about animals living in the rainforest.
C) The text only briefly mentions jaguars hunting, which is one example supporting the main idea about animals living in the rainforest.
D) The text mentions colorful birds, but this is just one detail supporting the main idea about animals living in the rainforest.

Solution:
1. Read the paragraph carefully
2. Look for what most sentences are about (animals in the rainforest)
3. Notice that each sentence gives an example of an animal living in the rainforest
4. The last sentence summarizes that all these animals depend on the rainforest
5. Choose the answer that captures what most sentences discuss: many animals living in and depending on the rainforest""",
    "quality_status": "good",
    "quality_criterion": "question_stem",
    "mutation_type": "original",
    "lesson": "Main Idea and Supporting Details",
    "difficulty_level": "medium"
}

BAD_EXAMPLES = [
    {
        # Bad vocabulary example
        "content": """What is the predominant thesis of the subsequent exposition?

The rainforest accommodates a plethora of diverse fauna. Chromatic avians traverse the towering arbors. Primates oscillate betwixt branches. Panthera onca conduct predation on the forest substrate. All these organisms are contingent upon the rainforest for sustenance and sanctuary.

A) The rainforest possesses elevated arbors
B) Manifold creatures inhabit and rely upon the rainforest
C) Panthera onca demonstrate proficient hunting aptitude
D) Avians exhibit chromatic characteristics

Correct Answer: B""",
        "quality_status": "bad",
        "quality_criterion": "vocabulary",
        "mutation_type": "vocabulary_mutation",
        "lesson": "Main Idea and Supporting Details",
        "difficulty_level": "medium"
    },
    {
        # Unclear question stem
        "content": """Read this and tell me what you think it's talking about maybe?

The rainforest is home to many different types of animals. Colorful birds fly through the tall trees. Monkeys swing from branch to branch. Jaguars hunt on the forest floor. All these animals depend on the rainforest for food and shelter.

A) The rainforest has tall trees
B) Many animals live in the rainforest
C) Jaguars are good hunters
D) Birds are colorful

Correct Answer: B""",
        "quality_status": "bad",
        "quality_criterion": "question_stem",
        "mutation_type": "stem_mutation",
        "lesson": "Main Idea and Supporting Details",
        "difficulty_level": "medium"
    },
    {
        # Poor distractors
        "content": """What is the main idea of the following paragraph?

The rainforest is home to many different types of animals. Colorful birds fly through the tall trees. Monkeys swing from branch to branch. Jaguars hunt on the forest floor. All these animals depend on the rainforest for food and shelter.

A) The sky is blue
B) Many animals live in the rainforest
C) Pizza is delicious
D) Computers use electricity

Correct Answer: B""",
        "quality_status": "bad",
        "quality_criterion": "distractors",
        "mutation_type": "distractor_mutation",
        "lesson": "Main Idea and Supporting Details",
        "difficulty_level": "medium"
    }
]

def seed_test_examples():
    """Seed the database with test examples"""
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials. Please check your .env file.")
    
    client: Client = create_client(supabase_url, supabase_key)
    
    try:
        # Insert good example
        print("Adding good example...")
        result = client.table("test_examples").insert(GOOD_EXAMPLE).execute()
        print(f"Added good example with ID: {result.data[0]['id']}")
        
        # Insert bad examples
        print("\nAdding bad examples...")
        for example in BAD_EXAMPLES:
            result = client.table("test_examples").insert(example).execute()
            print(f"Added bad example for {example['quality_criterion']} with ID: {result.data[0]['id']}")
            
        print("\nSeeding completed successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        raise

if __name__ == "__main__":
    seed_test_examples() 