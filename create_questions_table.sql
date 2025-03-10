-- Questions Table Schema for Grade 4 Language Arts
CREATE TABLE public.questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    lesson VARCHAR(100) NOT NULL,
    grade INTEGER NOT NULL DEFAULT 4,
    course VARCHAR(50) NOT NULL DEFAULT 'Language Arts',
    
    -- Question Metadata
    difficulty VARCHAR(10) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    interaction_type VARCHAR(10) NOT NULL CHECK (interaction_type IN ('MCQ', 'FRQ')),
    standard VARCHAR(50),
    
    -- Question Components
    stimuli TEXT,
    prompt TEXT NOT NULL,
    answer_choices JSONB,
    correct_answer TEXT NOT NULL,
    wrong_answer_explanations JSONB,
    solution TEXT NOT NULL,
    full_explanation TEXT NOT NULL,
    grading_criteria TEXT,
    
    -- Additional Metadata
    metadata JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('draft', 'active', 'archived', 'needs_review')),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX questions_lesson_idx ON public.questions(lesson);
CREATE INDEX questions_difficulty_idx ON public.questions(difficulty);
CREATE INDEX questions_interaction_type_idx ON public.questions(interaction_type);
CREATE INDEX questions_standard_idx ON public.questions(standard);
CREATE INDEX questions_status_idx ON public.questions(status);

-- Enable Row Level Security (RLS)
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;

-- Create a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_questions_timestamp
BEFORE UPDATE ON public.questions
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Create policies
-- Allow all operations for authenticated users (more permissive for testing)
CREATE POLICY "Allow authenticated users full access to questions"
ON public.questions
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

COMMENT ON TABLE public.questions IS 'Table storing Grade 4 Language Arts questions for educational content generation';
