"""Command-line interface for Fiber."""

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
import random
import time
import requests
from typing import Tuple, Optional
from dataclasses import asdict
import os
import sys
import re
import json

from fiber.session import Session, prompt_history
from fiber.system_context import context
from prompts.weather.weather import get_weather, format_weather_response
from prompts.time.time_utils import get_current_time, format_time_response
from prompts.creator.creator import create_document, format_content, open_document
from prompts.summarizer.summarizer import format_summary

# Create console for terminal output
console = Console() if sys.stdout.isatty() else None

# Check if running in web mode (no terminal)
WEB_MODE = not sys.stdout.isatty()

def get_command_help() -> str:
    """Get help text for available commands."""
    return """
# Available Commands

- `ask [question]`: Ask a question or start interactive mode
- `weather [location]`: Get weather information
- `time [location]`: Get current time
- `create [type] [topic]`: Create a new document
- `summarize [url]`: Summarize a webpage
- `info`: Display system information
- `preferences`: Show user preferences
- `set_preference [key] [value]`: Set a user preference
- `help`: Show this help message
- `exit/quit`: Exit the program
- `search [query]`: Search the web and open the most relevant result in Chrome
- `compare [items]`: Compare different theories, ideas, or arguments side-by-side
- `define [word]`: Get the definition of a word
- `brainstorm [topic]`: Generate creative ideas based on a topic
- `chat [message]`: Chat with the AI assistant
"""

def save_session():
    """Save the current session state."""
    session.save()
    context.save_history()
    context.save_preferences()

def print_system_info():
    """Display system information and resource usage."""
    info = context.system_info
    usage = context.get_resource_usage()
    
    if console:
        console.print("\n[bold blue]System Information[/bold blue]")
        console.print(f"OS: {info.os_name} {info.os_version}")
        console.print(f"Python: {info.python_version}")
        console.print(f"CPU Cores: {info.cpu_count}")
        console.print(f"CPU Usage: {usage['cpu_percent']}%")
        console.print(f"Memory: {usage['memory_percent']}% used")
        console.print(f"Language: {info.language}")
        console.print(f"Timezone: {info.timezone}\n")

def print_session_info():
    """Display current session information."""
    summary = context.get_session_summary()
    if summary['start_time']:
        if console:
            console.print("\n[bold blue]Session Information[/bold blue]")
            console.print(f"Started: {summary['start_time']}")
            console.print(f"Commands Run: {summary['command_count']}")
            if summary['last_command']:
                console.print(f"Last Command: {summary['last_command']['command']}")

def type_text(text: str, min_delay: float = 0.02, max_delay: float = 0.08):
    """Type out text with a natural typing effect."""
    try:
        # Clean up the text
        text = ' '.join(text.replace('\n', ' ').split())
        displayed_text = ""
        
        # Create a Live display context
        with Live("", refresh_per_second=20) as live:
            # Print initial prompt
            if console:
                live.update(f"\n[bold blue]Fiber:[/bold blue] ")
            
            # Type out each character
            for char in text:
                displayed_text += char
                if console:
                    live.update(f"\n[bold blue]Fiber:[/bold blue] {displayed_text}")
                time.sleep(random.uniform(min_delay, max_delay))
            
            # Add final newline for spacing
            if console:
                live.update(f"\n[bold blue]Fiber:[/bold blue] {displayed_text}\n")
            
    except KeyboardInterrupt:
        if console:
            console.print("\n[yellow]Goodbye![/yellow]")
        save_session()
        raise

def process_command(cmd: str) -> None:
    """Process a command in the interactive prompt."""
    try:
        # Add command to history
        context.add_to_history(cmd)
        
        # Handle document creation
        is_doc_request, file_path = handle_document_creation(cmd)
        if is_doc_request:
            session.last_file = file_path
            response = input().strip()
            if response.lower() == 'y':
                open_document(file_path)

        # Handle weather or time queries
        response_text = None
        if "weather" in cmd.lower():
            response_text = handle_weather_query(cmd)
        elif "time" in cmd.lower() or "date" in cmd.lower():
            response_text = handle_time_query(cmd)

        # Use Ollama for general queries
        if not response_text:
            try:
                model = os.getenv('OLLAMA_MODEL', 'mistral')
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": cmd,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    response_text = response.json().get("response", "")
                else:
                    response_text = f"Error: Ollama API returned status code {response.status_code}"
                    
            except requests.exceptions.ConnectionError:
                response_text = "Error: Could not connect to Ollama. Make sure it's running with 'ollama serve'"

        # Display the response with typing effect
        if response_text:
            type_text(response_text)

        # Update session context
        session.update_context('last_query', cmd)
        if response_text:
            session.update_context('last_response', response_text)
        save_session()
        
    except Exception as e:
        error = f"Error: {str(e)}"
        if WEB_MODE:
            print(error, file=sys.stderr)
        else:
            console.print(f"[red]{error}[/red]")

def handle_weather_query(query: str) -> str:
    """Handle weather-related queries."""
    # Extract city name from query using simple pattern matching
    city_match = re.search(r"weather (?:in|at|for)?\s+([a-zA-Z\s]+)", query.lower())
    if city_match:
        city = city_match.group(1).strip()
        weather_data = get_weather(city)
        if weather_data:
            return format_weather_response(weather_data)
    return None

def handle_time_query(query: str) -> str:
    """Handle time-related queries."""
    # Extract timezone from query using simple pattern matching
    tz_match = re.search(r"time (?:in|at|for)?\s+([a-zA-Z\s/]+)", query.lower())
    timezone = None
    if tz_match:
        timezone = tz_match.group(1).strip()

    time_data = get_current_time(timezone)
    if time_data:
        return format_time_response(time_data)
    return None

def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())

def format_time(seconds: int) -> str:
    """Format seconds into MM:SS."""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def handle_document_creation(prompt: str) -> Tuple[bool, Optional[str]]:
    """Handle requests to create documents."""
    write_patterns = [
        r"write (?:notes |a document )?(?:about |on )?(.+)",
        r"create (?:notes |a document )?(?:about |on )?(.+)",
        r"make (?:notes |a document )?(?:about |on )?(.+)"
    ]

    for pattern in write_patterns:
        match = re.search(pattern, prompt.lower())
        if match:
            topic = match.group(1).strip()
            if WEB_MODE:
                print(f"Planning document about {topic}...", file=sys.stderr)
            else:
                console.print(f"\n[bold blue]Fiber:[/bold blue] Planning document about {topic}...")
            
            # Get content from Ollama
            try:
                model = os.getenv('OLLAMA_MODEL', 'mistral')
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": f"""Write detailed, well-structured notes about {topic}.
Include relevant examples and explanations.
Make the content clear, concise, and well-organized.
Focus on the most important concepts and explain them well.""",
                        "stream": True
                    },
                    stream=True
                )
                
                if response.status_code == 200:
                    content = []
                    accumulated_text = ""
                    start_time = time.time()
                    last_update = 0
                    target_words = 500  # Target word count
                    
                    if WEB_MODE:
                        print("Writing content...", file=sys.stderr)
                    else:
                        console.print("[bold blue]Fiber:[/bold blue] Writing content...")
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                json_response = json.loads(line.decode())
                                if 'response' in json_response:
                                    chunk = json_response['response']
                                    content.append(chunk)
                                    accumulated_text += chunk
                                    
                                    # Update progress less frequently (every 0.5 seconds)
                                    current_time = time.time()
                                    if current_time - last_update >= 0.5:
                                        current_words = count_words(accumulated_text)
                                        progress = min(100, int((current_words / target_words) * 100))
                                        elapsed = format_time(int(current_time - start_time))
                                        
                                        # Clear previous line and write new progress
                                        if WEB_MODE:
                                            print("\033[K", end="\r", file=sys.stderr)  # Clear the current line
                                            print(f"Progress: {progress}% • {elapsed}", end="\r", file=sys.stderr)
                                        else:
                                            console.print(f"[bold blue]Progress:[/bold blue] {progress}% • {elapsed}", end="\r")
                                        last_update = current_time
                                        
                                    if json_response.get('done', False):
                                        break
                            except json.JSONDecodeError:
                                continue
                    
                    # Move to next line after progress is done
                    if WEB_MODE:
                        print("", file=sys.stderr)
                    else:
                        console.print()
                    
                    if content:
                        final_content = "".join(content)
                        formatted_content = format_content(topic, final_content)
                        file_path = create_document(topic, formatted_content)
                        
                        if file_path:
                            if WEB_MODE:
                                print(f"I have completed writing about: {topic} ({count_words(final_content)} words). Would you like me to open the document for you? (y/n)", file=sys.stderr)
                            else:
                                console.print(f"\n[bold blue]Fiber:[/bold blue] I have completed writing about: {topic} ({count_words(final_content)} words). Would you like me to open the document for you? (y/n)")
                            return True, file_path
                            
            except Exception as e:
                error = f"Error creating document: {str(e)}"
                if WEB_MODE:
                    print(error, file=sys.stderr)
                else:
                    console.print(f"[red]{error}[/red]")
                
    return False, None

def call_ollama(prompt, timeout=45):
    """Call Ollama API with better error handling and timeout."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": os.getenv('OLLAMA_MODEL', 'mistral'),
                "prompt": prompt,
                "stream": False
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            raise Exception(f"Ollama API returned status code {response.status_code}")
            
    except requests.exceptions.Timeout:
        raise Exception(
            "Ollama took too long to respond. Please ensure:\n"
            "1. Ollama is running (ollama serve)\n"
            "2. The model is already pulled (ollama pull qwen:7b)\n"
            "3. Your system has enough resources available"
        )
    except requests.exceptions.ConnectionError:
        raise Exception(
            "Could not connect to Ollama. Please ensure:\n"
            "1. Ollama is installed and running (ollama serve)\n"
            "2. It's accessible at localhost:11434"
        )
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")

def interactive_prompt():
    """Start an interactive prompt session."""
    try:
        prompt_session = PromptSession(history=prompt_history)

        while True:
            try:
                # Get suggestions based on session history
                suggestions = session.get_suggestions("")
                completer = WordCompleter(suggestions, ignore_case=True)
                
                # Get user input with plain text prompt
                user_input = prompt_session.prompt(
                    "Fiber> ",
                    completer=completer
                ).strip()
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit']:
                    save_session()
                    break
                elif user_input.lower() == 'help':
                    if WEB_MODE:
                        print(get_command_help(), file=sys.stderr)
                    else:
                        console.print(Markdown(get_command_help()))
                    continue
                elif not user_input:  # Skip empty input
                    continue
                
                # Process the command
                session.add_command(user_input)
                process_command(user_input)
                
            except KeyboardInterrupt:
                if WEB_MODE:
                    print("\nSession terminated by user", file=sys.stderr)
                else:
                    console.print("\n[yellow]Session terminated by user[/yellow]")
                context.save_history()
                break
            except Exception as e:
                error = f"Error: {str(e)}"
                if WEB_MODE:
                    print(error, file=sys.stderr)
                else:
                    console.print(f"[red]{error}[/red]")
                continue
    except Exception as e:
        error = f"Fatal error: {str(e)}"
        if WEB_MODE:
            print(error, file=sys.stderr)
        else:
            console.print(f"[red]{error}[/red]")
        sys.exit(1)

# CLI Commands
@click.group()
def cli():
    """Fiber CLI - Your AI-powered assistant"""
    pass

@cli.command()
def info():
    """Display system and session information."""
    print_system_info()
    print_session_info()
    
    # Show installed development tools
    tools = context.get_installed_tools()
    if tools:
        if console:
            console.print("\n[bold blue]Installed Development Tools[/bold blue]")
            for tool, version in tools.items():
                if version:
                    console.print(f"{tool}: {version}")

@cli.command()
@click.argument('key')
@click.argument('value')
def set_preference(key: str, value: str):
    """Set a user preference."""
    if hasattr(context.user_prefs, key):
        setattr(context.user_prefs, key, value)
        context.save_preferences()
        if console:
            console.print(f"[green]Preference {key} set to: {value}[/green]")
    else:
        error = f"Unknown preference: {key}"
        if console:
            console.print(f"[red]{error}[/red]")
        else:
            print(error, file=sys.stderr)

@cli.command()
def preferences():
    """Show current user preferences."""
    if console:
        console.print("\n[bold blue]Current Preferences[/bold blue]")
        for key, value in asdict(context.user_prefs).items():
            console.print(f"{key}: {value}")

@cli.command()
@click.argument('prompt', required=False)
def ask(prompt):
    """Ask Fiber a question or start interactive mode."""
    if not prompt:
        interactive_prompt()
        return
    
    # If prompt is provided, process it directly
    process_command(prompt)

@cli.command()
@click.argument('url', required=True)
def summarize(url: str):
    """Summarize a webpage article."""
    result = format_summary(url)
    if result:
        if console:
            console.print(Markdown(result))

@cli.command()
@click.argument('query')
def search(query):
    """Search for information and open results in browser.
    
    Examples:
    - search "python web development"
    - search "history of the silk road"
    - search "machine learning basics"
    """
    try:
        # Remove quotes from query
        query = query.strip('"\'')
        
        if console:
            console.print("\n[bold]🔍 Searching...[/bold]\n")
        
        # Get search results
        results = search_web(query)
        
        if not results:
            if console:
                console.print("[red]No results found[/red]")
            return
            
        # Display results
        if console:
            console.print("\n[bold]Search Results:[/bold]\n")
            for i, result in enumerate(results, 1):
                console.print(f"[bold blue]{i}. {result['title']}[/bold blue]")
                if result.get('description'):
                    console.print(f"   {result['description']}")
                console.print(f"   [link={result['url']}]{result['url']}[/link]")
                console.print(f"   Source: {result['source']}\n")
            
            # Open best result in browser
            import webbrowser
            best_result = results[0]['url']
            webbrowser.open(best_result)
            console.print(f"\n[green]✓ Opened top result in your browser[/green]")
            
    except Exception as e:
        error = f"Search error: {str(e)}"
        if console:
            console.print(f"[red]{error}[/red]")
        else:
            print(error, file=sys.stderr)

def search_web(query):
    """Search the web using DuckDuckGo."""
    try:
        # Use DuckDuckGo API
        url = f'https://api.duckduckgo.com/?q={query}&format=json'
        response = requests.get(url)
        data = response.json()
        
        results = []
        
        # Add instant answer if available
        if data.get('AbstractText'):
            results.append({
                'title': data['Heading'],
                'description': data['AbstractText'],
                'url': data['AbstractURL'],
                'source': 'DuckDuckGo Abstract'
            })
        
        # Add related topics
        for topic in data.get('RelatedTopics', [])[:5]:
            if isinstance(topic, dict) and 'Text' in topic:
                url = topic.get('FirstURL', '')
                if url:
                    title = topic['Text'].split(' - ')[0] if ' - ' in topic['Text'] else topic['Text']
                    description = topic['Text'].split(' - ')[1] if ' - ' in topic['Text'] else ''
                    results.append({
                        'title': title,
                        'description': description,
                        'url': url,
                        'source': 'DuckDuckGo'
                    })
        
        return results
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

@cli.command()
@click.argument('items', nargs=-1, required=True)
def compare(items):
    """Compare different theories, ideas, or arguments side-by-side.
    
    Example: compare "Python" "JavaScript" "Ruby"
    """
    if len(items) < 2:
        error = "Error: Please provide at least two items to compare"
        if console:
            console.print(f"[red]{error}[/red]")
        else:
            print(error, file=sys.stderr)
        return
        
    try:
        if console:
            with console.status("[bold blue]Working on comparison...") as status:
                # Get comparison
                status.update("[bold blue]Analyzing and comparing items...")
                from fiber.prompts.compare.compare_utils import get_comparison, display_comparison, save_comparison_image
                result = get_comparison(list(items))
                
                # Generate and save image
                status.update("[bold blue]Generating comparison image...")
                image_path = save_comparison_image(result)
                
                # Display results
                console.print("\n")  # Add some spacing
                display_comparison(result)
                console.print(f"\n[bold green]Comparison image saved:[/bold green] {image_path}")
                
    except Exception as e:
        error = f"Error: {str(e)}"
        if console:
            console.print(f"[red]{error}[/red]")
        else:
            print(error, file=sys.stderr)

@cli.command()
@click.argument('word', required=True)
def define(word):
    """Get a simple definition of a word.
    
    Example: define "ephemeral"
    """
    try:
        from fiber.prompts.define.define_utils import get_word_definition
        
        # Get definition
        definition = get_word_definition(word)
        
        if definition:
            if console:
                console.print(f"\n[bold]{word}:[/bold] {definition}")
            else:
                # Web mode - just print the definition
                print(definition)
        else:
            error = f"Could not find definition for '{word}'"
            if console:
                console.print(f"\n[red]{error}[/red]")
            else:
                print(error, file=sys.stderr)
            
    except Exception as e:
        error = f"Error: {str(e)}"
        if console:
            console.print(f"[red]{error}[/red]")
        else:
            print(error, file=sys.stderr)

@cli.command()
@click.argument('topic')
def brainstorm(topic):
    """Generate creative ideas based on a topic.
    
    Examples:
    - brainstorm "artificial intelligence"
    - brainstorm "climate change"
    - brainstorm "medieval history"
    """
    try:
        # Remove any extra quotes from the topic
        topic = topic.strip('"\'')
        prompt = f'Brainstorm 5 creative and unique ideas related to "{topic}". Format as a numbered list.'
        
        if console:
            with console.status("[bold blue]Brainstorming ideas..."):
                ideas = call_ollama(prompt)
                if ideas:
                    console.print(f"\n[bold]Ideas for {topic}:[/bold]\n")
                    console.print(Markdown(ideas))
                else:
                    console.print("\n[red]No ideas generated[/red]")
        else:
            # Web mode - direct output
            ideas = call_ollama(prompt)
            if ideas:
                print(ideas)
            else:
                print("No ideas generated", file=sys.stderr)
                
    except Exception as e:
        error = f"Error: {str(e)}"
        if console:
            console.print(f"[red]{error}[/red]")
        else:
            print(error, file=sys.stderr)

@cli.command()
@click.argument('message', type=str)
def chat(message):
    """Have a conversation with the AI."""
    try:
        if WEB_MODE:
            print(f"Debug: Received message type: {type(message)}", file=sys.stderr)
            print(f"Debug: Message content: {message}", file=sys.stderr)
        
        from fiber.prompts.chat.chat_utils import chat_with_ai
        
        # Ensure message is a string
        if not isinstance(message, str):
            error = f"Error: Expected string message, got {type(message)}"
            if WEB_MODE:
                print(error, file=sys.stderr)
            else:
                console.print(f"[red]{error}[/red]")
            sys.exit(1)
            
        # Get AI response
        response = chat_with_ai(str(message))
        
        if response:
            # Print raw response for web interface
            if WEB_MODE:
                print(response, flush=True)
            else:
                console.print(response)
        else:
            error = "Failed to get a response from the AI."
            if WEB_MODE:
                print(error, flush=True)
            else:
                console.print(f"[red]{error}[/red]")
            
    except ImportError as e:
        error = f"Error: Failed to import required modules: {str(e)}"
        if WEB_MODE:
            print(error, file=sys.stderr)
        else:
            console.print(f"[red]{error}[/red]")
        sys.exit(1)
    except Exception as e:
        error = f"Error in chat command: {str(e)}"
        if WEB_MODE:
            print(error, file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            console.print(f"[red]{error}[/red]")
        sys.exit(1)

cli.add_command(chat)

def main():
    """Main entry point for the CLI."""
    try:
        # Initialize session
        global session
        session = Session()
        
        cli()
    except Exception as e:
        if console:
            console.print(f"[red]Error: {str(e)}[/red]")
        else:
            print(f"Error: {str(e)}", file=sys.stderr)
        
if __name__ == '__main__':
    main()
