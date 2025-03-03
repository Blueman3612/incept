# Article Generator and Grader Test Scripts

This folder contains scripts for testing and validating the educational article generator and grader.

## Overview

These scripts allow you to:

1. Test single article generation and grading with detailed logging
2. Run batch tests on multiple lessons and compile results
3. Analyze quality metrics and performance statistics

## Test Scripts

### Single Article Test

`test_article_generator.py` generates and grades a single article with comprehensive logging.

```powershell
# Basic usage
python scripts/test_article_generator.py --lesson "main_idea" --grade 4 --subject "Language" --difficulty easy

# With keywords and custom retries
python scripts/test_article_generator.py --lesson "character_analysis" --grade 4 --subject "Language" --difficulty medium --keywords "protagonist,setting,traits" --max-retries 5

# With lesson description
python scripts/test_article_generator.py --lesson "context_clues" --grade 4 --subject "Language" --difficulty easy --lesson-description "Using surrounding text to determine the meaning of unfamiliar words"

# Without saving output files
python scripts/test_article_generator.py --lesson "context_clues" --grade 4 --subject "Language" --difficulty easy --no-save
```

#### Arguments:

- `--lesson`: Lesson topic (e.g., main_idea, supporting_details) (required)
- `--grade`: Target grade level, 1-8 (required)
- `--subject`: Subject area (required)
- `--difficulty`: Difficulty level: easy, medium, or hard (required)
- `--keywords`: Comma-separated list of keywords to include (optional)
- `--lesson-description`: Detailed description of learning objectives (optional)
- `--max-retries`: Maximum generation improvement attempts (default: 3)
- `--no-save`: Flag to prevent saving output files (optional)

### PowerShell Wrapper

`test_article.ps1` provides a simple PowerShell wrapper for the Python script:

```powershell
# Basic usage
.\scripts\test_article.ps1 -Lesson "main_idea"

# With custom parameters
.\scripts\test_article.ps1 -Lesson "character_analysis" -Grade 5 -Subject "Language" -Difficulty medium

# With lesson description
.\scripts\test_article.ps1 -Lesson "context_clues" -LessonDescription "Using surrounding text to determine meaning"
```

### Batch Testing

`batch_test_articles.py` runs tests on multiple lesson topics and compiles the results into CSV and JSON files.

```powershell
# Test 3 random lessons (default)
python scripts/batch_test_articles.py

# Test 5 specific lessons
python scripts/batch_test_articles.py --count 5 --lessons "main_idea,supporting_details,context_clues,text_structure,figurative_language"

# More customization
python scripts/batch_test_articles.py --count 10 --grade 4 --subject "Language" --difficulty medium --max-retries 2 --output-dir "my_test_results"
```

#### Arguments:

- `--count`: Number of articles to generate (default: 3)
- `--grade`: Target grade level, 1-8 (default: 4)
- `--subject`: Subject area (default: "Language")
- `--difficulty`: Difficulty level (default: "easy")
- `--lessons`: Comma-separated list of lesson topics (optional, will randomly select if not provided)
- `--max-retries`: Maximum generation improvement attempts (default: 3)
- `--output-dir`: Directory to save results (default: "batch_results")

### PowerShell Batch Wrapper

`batch_test.ps1` provides a simple PowerShell wrapper for the batch testing script:

```powershell
# Basic usage
.\scripts\batch_test.ps1

# With custom parameters
.\scripts\batch_test.ps1 -Count 5 -Difficulty medium -Lessons "main_idea,supporting_details,context_clues"
```

### Question Testing

`test_question.ps1` provides a script for testing the question generation API:

```powershell
# Basic usage
.\scripts\test_question.ps1 -Lesson "main_idea"

# With custom parameters
.\scripts\test_question.ps1 -Lesson "supporting_details" -Difficulty medium -LessonDescription "Identify key supporting details in informational text"

# With custom maximum retries
.\scripts\test_question.ps1 -Lesson "context_clues" -MaxRetries 5
```

#### Arguments:

- `Lesson`: Lesson topic (e.g., main_idea, supporting_details) (required)
- `Difficulty`: Difficulty level: easy, medium, or hard (default: easy)
- `LessonDescription`: Detailed description of learning objectives (optional)
- `MaxRetries`: Maximum number of improvement attempts (default: 3)

## Output Files

The scripts generate several output files:

- **Article Files**: Generated articles saved as Markdown (`.md`) files
- **Question Files**: Generated questions saved as text or JSON files
- **Grading Results**: Detailed grading results saved as JSON files
- **Log Files**: Comprehensive logs of the testing process
- **CSV Reports**: Batch test results in CSV format for easy analysis
- **Summary JSON**: Batch test summary with statistics

## Required Environment Variables

These scripts require the following environment variables to be set:

```
OPENAI_API_KEY=your_openai_api_key
GPT_MODEL=gpt-4  # or another suitable model
```

## Example Workflow

1. Run a single article test to verify setup:
   ```powershell
   .\scripts\test_article.ps1 -Lesson "main_idea"
   ```

2. Run a batch test on multiple lessons:
   ```powershell
   .\scripts\batch_test.ps1 -Count 5 -Difficulty easy
   ```

3. Test question generation:
   ```powershell
   .\scripts\test_question.ps1 -Lesson "main_idea" -Difficulty medium
   ```

4. Run comprehensive tests across different difficulties:
   ```powershell
   foreach ($difficulty in @("easy", "medium", "hard")) {
       .\scripts\batch_test.ps1 -Count 3 -Difficulty $difficulty -Lessons "main_idea,summarizing,context_clues"
   }
   ```

5. Analyze the results in the generated CSV and JSON files

## Troubleshooting

- If you encounter API rate limit errors, add delays between tests or reduce batch size
- For memory issues, reduce the number of test articles or run tests sequentially
- Check the log files for detailed error information
- If a script fails to import modules, make sure you're running it from the project root directory
- To debug generation issues, examine the full results JSON files for detailed error messages 