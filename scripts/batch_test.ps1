<#
.SYNOPSIS
    Batch test script for article generation and grading.
    
.DESCRIPTION
    This script runs batch tests for article generation and grading with configurable parameters.
    
.PARAMETER Count
    Number of articles to generate.
    
.PARAMETER Grade
    Target grade level (1-8).
    
.PARAMETER Course
    Course name (e.g., "Language", "Math", "Science").
    
.PARAMETER Lessons
    Comma-separated list of lesson topics (will randomly select if not provided).
    
.PARAMETER MaxRetries
    Maximum number of improvement attempts per article.
    
.PARAMETER OutputDir
    Directory to save results.
    
.EXAMPLE
    .\batch_test.ps1 -Count 3
    
.EXAMPLE
    .\batch_test.ps1 -Count 5 -Lessons "Main Idea,Character Analysis,Point of View"
#>

param (
    [Parameter(Mandatory=$false)]
    [int]$Count = 3,
    
    [Parameter(Mandatory=$false)]
    [ValidateRange(1, 8)]
    [int]$Grade = 4,
    
    [Parameter(Mandatory=$false)]
    [string]$Course = "Language",
    
    [Parameter(Mandatory=$false)]
    [string]$Lessons = "",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxRetries = 3,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "batch_results"
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
Write-Host "==== BATCH ARTICLE GENERATOR TEST ====" -ForegroundColor Cyan
Write-Host "Count:       $Count" -ForegroundColor Yellow
Write-Host "Grade:       $Grade" -ForegroundColor Yellow
Write-Host "Course:      $Course" -ForegroundColor Yellow
Write-Host "Lessons:     $Lessons" -ForegroundColor Yellow
Write-Host "Max retries: $MaxRetries" -ForegroundColor Yellow
Write-Host "Output dir:  $OutputDir" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Cyan

# Build command arguments
$args = @(
    "$PSScriptRoot/batch_test_articles.py",
    "--count", "$Count",
    "--grade", "$Grade",
    "--course", "`"$Course`"",
    "--max-retries", "$MaxRetries",
    "--output-dir", "`"$OutputDir`""
)

# Add lessons if provided
if ($Lessons) {
    $args += "--lessons"
    $args += "`"$Lessons`""
}

# Construct the command
$command = "python " + ($args -join " ")
Write-Host "Running command: $command" -ForegroundColor DarkGray

# Run the batch test
try {
    Invoke-Expression $command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Batch test completed successfully" -ForegroundColor Green
        
        # Open the output directory
        if (Test-Path $OutputDir) {
            Write-Host "Opening results folder: $OutputDir"
            Start-Process explorer.exe -ArgumentList $OutputDir
        }
        
        exit 0
    } else {
        Write-Host "Batch test completed with issues (exit code: $LASTEXITCODE)" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
} catch {
    Write-Error "Error running batch test: $_"
    exit 1
} 