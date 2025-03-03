<#
.SYNOPSIS
    Quick test script for article generation and grading.
    
.DESCRIPTION
    This script runs a single article generation and grading test with default parameters.
    
.PARAMETER Lesson
    Main lesson topic (e.g., "Main Idea", "Character Analysis").
    
.PARAMETER Grade
    Target grade level (1-8).
    
.PARAMETER Course
    Course name (e.g., "Language", "Math", "Science").
    
.PARAMETER LessonDescription
    Optional detailed description of the lesson objectives.
    
.EXAMPLE
    .\test_article.ps1 -Lesson "Main Idea"
    
.EXAMPLE
    .\test_article.ps1 -Lesson "Character Analysis" -Grade 5
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$Lesson,
    
    [Parameter(Mandatory=$false)]
    [ValidateRange(1, 8)]
    [int]$Grade = 4,
    
    [Parameter(Mandatory=$false)]
    [string]$Course = "Language",
    
    [Parameter(Mandatory=$false)]
    [string]$LessonDescription = ""
)

# Check if OPENAI_API_KEY is set
if (-not $env:OPENAI_API_KEY) {
    Write-Error "OPENAI_API_KEY environment variable not set"
    exit 1
}

# Set GPT_MODEL if not already set
if (-not $env:GPT_MODEL) {
    $env:GPT_MODEL = "gpt-4"
    Write-Host "Setting GPT_MODEL to default: gpt-4"
}

# Print test information
Write-Host "==== ARTICLE GENERATOR TEST ====" -ForegroundColor Cyan
Write-Host "Lesson:      $Lesson" -ForegroundColor Yellow
Write-Host "Grade:       $Grade" -ForegroundColor Yellow
Write-Host "Course:      $Course" -ForegroundColor Yellow
if ($LessonDescription) {
    Write-Host "Description: $LessonDescription" -ForegroundColor Yellow
}
Write-Host "================================" -ForegroundColor Cyan

# Build command arguments
$args = @(
    "$PSScriptRoot/test_article_generator.py",
    "--lesson", "`"$Lesson`"",
    "--grade", "$Grade",
    "--course", "`"$Course`""
)

# Add lesson description if provided
if ($LessonDescription) {
    $args += "--lesson-description"
    $args += "`"$LessonDescription`""
}

# Construct the command
$command = "python " + ($args -join " ")
Write-Host "Running command: $command" -ForegroundColor DarkGray

# Run the test
try {
    Invoke-Expression $command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Test completed successfully" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "Test completed with issues (exit code: $LASTEXITCODE)" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
} catch {
    Write-Error "Error running test: $_"
    exit 1
} 