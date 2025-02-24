import requests
import json
import time
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Initialize Rich console
console = Console()

def generate_article(payload: dict) -> Optional[dict]:
    """Generate an article with progress indication."""
    url = "http://localhost:8000/api/v1/articles/generate"
    headers = {"Content-Type": "application/json"}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        try:
            # Start the generation task
            task = progress.add_task("Generating educational article...", total=None)
            
            # Make the POST request
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Mark task as complete
            progress.update(task, completed=True)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            progress.update(task, description="[red]Error generating article!")
            console.print(f"\n[red]Error making request: {e}")
            if hasattr(e.response, 'text'):
                console.print(f"[red]Error details: {e.response.text}")
            return None
        except Exception as e:
            progress.update(task, description="[red]Unexpected error!")
            console.print(f"\n[red]Unexpected error: {e}")
            return None

def print_article(article: dict) -> None:
    """Print the article in a formatted way."""
    console.print("\n[bold green]Generated Article:[/bold green]")
    console.rule(style="green")
    
    # Article metadata
    console.print(f"[bold blue]ID:[/bold blue] {article['id']}")
    console.print(f"[bold blue]Title:[/bold blue] {article['title']}")
    
    # Content
    console.rule(style="blue")
    console.print("[bold]Content:[/bold]")
    console.print(article['content'])
    
    # Key Concepts
    console.rule(style="blue")
    console.print("[bold]Key Concepts:[/bold]")
    for concept in article['key_concepts']:
        console.print(f"• {concept}")
    
    # Examples
    console.rule(style="blue")
    console.print("[bold]Examples:[/bold]")
    for example in article['examples']:
        console.print(f"• {example}")
    
    # Metadata
    console.rule(style="blue")
    console.print("[bold]Metadata:[/bold]")
    console.print(f"[dim]Grade Level:[/dim] {article['grade_level']}")
    console.print(f"[dim]Subject:[/dim] {article['subject']}")
    console.print(f"[dim]Difficulty:[/dim] {article['difficulty_level']}")
    console.print(f"[dim]Created At:[/dim] {article['created_at']}")
    console.print(f"[dim]Tags:[/dim] {', '.join(article['tags'])}")
    
    console.rule(style="green")

def main():
    # Request payload
    payload = {
        "topic": "Creative Writing: Building Strong Characters",
        "grade_level": 4,
        "subject": "Language Arts",
        "difficulty": "intermediate",
        "keywords": ["character development", "personality traits", "dialogue", "description"],
        "style": "creative"
    }

    # Generate the article
    console.print("[bold]Starting Article Generation[/bold]")
    article = generate_article(payload)
    
    if article:
        print_article(article)
        console.print("\n[bold green]✓[/bold green] Article generation completed successfully!")
    else:
        console.print("\n[bold red]✗[/bold red] Article generation failed!")

if __name__ == "__main__":
    main() 