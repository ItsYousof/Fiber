"""Brainstorming utilities for Fiber."""

import os
import requests
import json
from rich.console import Console
from typing import List, Dict
import time

console = Console()

def check_ollama_status():
    """Check if Ollama is running and responsive."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def generate_ideas(topic: str, category: str = "general") -> List[Dict[str, str]]:
    """Generate creative ideas based on a topic and category."""
    
    # Check if Ollama is running
    if not check_ollama_status():
        console.print("[red]Error: Ollama is not running. Please start Ollama first.[/red]")
        console.print("Run 'ollama serve' in a separate terminal to start the Ollama server.")
        return []
    
    try:
        model = os.getenv('OLLAMA_MODEL', 'qwen:7b')
        
        # Craft prompt based on category
        prompts = {
            "project": """Generate 3 unique project ideas related to: {topic}
            For each idea include:
            - A catchy title
            - A one-line description
            Focus on practical, engaging projects that can be completed in 1-4 weeks.""",
            
            "assignment": """Generate 3 interesting assignment ideas related to: {topic}
            For each idea include:
            - A clear title
            - A one-line description
            Focus on educational value and skill development.""",
            
            "writing": """Generate 3 creative writing prompts related to: {topic}
            For each idea include:
            - An engaging title
            - A one-line story hook
            Focus on unique angles and interesting scenarios.""",
            
            "general": """Generate 3 creative ideas related to: {topic}
            For each idea include:
            - A clear title
            - A one-line description
            Focus on variety and originality."""
        }
        
        prompt = prompts.get(category, prompts["general"]).format(topic=topic)
        
        # Use streaming response
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True
            },
            stream=True,
            timeout=10
        )
        
        if response.status_code == 200:
            # Collect the streamed response
            content = ""
            with console.status("[bold blue]Generating ideas...", spinner="dots") as status:
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line)
                            if "response" in json_response:
                                content += json_response["response"]
                                # Show progress
                                if json_response["response"].strip():
                                    status.update(f"[bold blue]Generating ideas... {content.count('.')}[/bold blue]")
                        except json.JSONDecodeError:
                            continue
            
            # Parse the response into structured ideas
            ideas = []
            current_idea = {}
            
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line starts with number (1-3)
                if line[0].isdigit() and line[1] in [')', '.', ':']:
                    # Save previous idea if exists
                    if current_idea:
                        ideas.append(current_idea)
                    current_idea = {"title": line[2:].strip()}
                elif current_idea and "title" in current_idea and "description" not in current_idea:
                    current_idea["description"] = line.strip()
            
            # Add last idea
            if current_idea:
                ideas.append(current_idea)
            
            return ideas[:3]  # Ensure we only return 3 ideas
            
    except requests.Timeout:
        console.print("[red]Error: Request timed out.[/red]")
        console.print("[yellow]Tips:[/yellow]")
        console.print("1. Check if Ollama is running properly")
        console.print("2. Try a different model (set OLLAMA_MODEL in .env)")
        console.print("3. Try a shorter prompt or simpler topic")
    except Exception as e:
        console.print(f"[red]Error generating ideas: {str(e)}[/red]")
    
    return []

def display_ideas(ideas: List[Dict[str, str]], topic: str, category: str):
    """Display generated ideas in a clean format."""
    if not ideas:
        return  # Error messages already handled in generate_ideas
        
    # Category-specific emoji
    emoji = {
        "project": "🚀",
        "assignment": "📚",
        "writing": "✍️",
        "general": "💡"
    }.get(category, "💡")
    
    # Display each idea
    console.print(f"\n{emoji} [bold]Ideas for:[/bold] {topic}\n")
    
    for i, idea in enumerate(ideas, 1):
        title = idea.get("title", "").strip()
        desc = idea.get("description", "").strip()
        
        console.print(f"[bold cyan]{i}. {title}[/bold cyan]")
        if desc:
            console.print(f"   {desc}\n")
