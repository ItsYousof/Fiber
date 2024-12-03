import requests
from bs4 import BeautifulSoup
import trafilatura
import re
from typing import Tuple, Optional
from rich.console import Console
from rich.markdown import Markdown
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

# Load environment variables
load_dotenv()

console = Console()

def get_ollama_model() -> str:
    """Get the Ollama model name from environment variables."""
    return os.getenv('OLLAMA_MODEL', 'llama2')  # Default to llama2 if not set

def get_default_notes_path() -> str:
    """Get the default path for saving notes."""
    default_path = os.getenv('DEFAULT_PATH', 'D:/Fiber_Notes')
    if not os.path.exists(default_path):
        os.makedirs(default_path)
    return default_path

def extract_article_content(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract the main content and title from a webpage.
    
    Args:
        url: The URL of the webpage to extract content from
        
    Returns:
        Tuple of (title, content) or (None, None) if extraction fails
    """
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format. URL must start with http:// or https://")

        # Download webpage content
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            console.print("[yellow]Warning:[/yellow] Initial download failed, trying alternative method...")
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response.raise_for_status()  # Raise error for bad status codes
            downloaded = response.text

        # Try trafilatura first
        result = trafilatura.extract(
            downloaded,
            include_links=False,
            include_images=False,
            include_tables=False,
            no_fallback=False,
            output_format='txt'  
        )
        
        if result:
            # Try to extract title separately
            metadata = trafilatura.extract_metadata(downloaded)
            title = metadata.title if metadata and hasattr(metadata, 'title') else None
            
            if not result.strip():
                raise ValueError("No content extracted from the webpage")
                
            # Clean up content
            content = re.sub(r'\s+', ' ', result).strip()
            return title, content
            
        # Fallback to BeautifulSoup
        console.print("[yellow]Warning:[/yellow] Primary extraction failed, trying fallback method...")
        soup = BeautifulSoup(downloaded, 'html.parser')
        
        # Try to get title
        title = soup.title.string if soup.title else None
        
        # Try to get main content
        # Remove script, style, and nav elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
            element.decompose()
            
        # Get text from article or main content area
        content = ''
        main_content = (
            soup.find('article') or 
            soup.find('main') or 
            soup.find('div', {'id': re.compile(r'(content|article|post)', re.I)}) or
            soup.find('div', {'class': re.compile(r'(content|article|post)', re.I)})
        )
        
        if main_content:
            # Remove unwanted elements from main content
            for element in main_content(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            content = main_content.get_text()
        else:
            content = soup.get_text()
        
        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()
        content = re.sub(r'Share this article Share this article on.*?$', '', content, flags=re.DOTALL)
        
        if not content:
            raise ValueError("No content could be extracted from the webpage")
            
        return title, content
        
    except requests.exceptions.RequestException as e:
        if '404' in str(e):
            console.print("[red]Error:[/red] Page not found (404)")
        elif '403' in str(e):
            console.print("[red]Error:[/red] Access forbidden (403). This site may be blocking automated access")
        elif '401' in str(e):
            console.print("[red]Error:[/red] Authentication required (401). This may be a paywall")
        else:
            console.print(f"[red]Error accessing the webpage:[/red] {str(e)}")
        return None, None
    except Exception as e:
        console.print(f"[red]Error extracting content:[/red] {str(e)}")
        return None, None

def create_summary(url: str) -> Optional[str]:
    """
    Create a summary of the webpage content.
    
    Args:
        url: The URL of the webpage to summarize
        
    Returns:
        A formatted summary or None if summarization fails
    """
    try:
        # Extract content
        title, content = extract_article_content(url)
        
        if not content:
            return None
            
        # Read prompt template
        with open('prompts/summarizer/prompt.txt', 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        # Prepare content for summarization
        if title:
            article_content = f"Title: {title}\n\nContent: {content}"
        else:
            article_content = f"Content: {content}"
            
        # Get the model name
        model = get_ollama_model()
        console.print(f"[blue]Using model:[/blue] {model}")
            
        # Get summary from Ollama
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": f"{prompt_template}\n\nPlease summarize this article:\n{article_content}",
                    "stream": False  # Disable streaming for now
                }
            )
            
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    if isinstance(response_json, dict):
                        summary = response_json.get("response", "")
                        if summary:
                            return summary
                        else:
                            raise ValueError("No summary in response")
                    else:
                        raise ValueError("Invalid response format from Ollama")
                except json.JSONDecodeError as e:
                    # Try to handle streaming response
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if isinstance(chunk, dict) and "response" in chunk:
                                    full_response += chunk["response"]
                            except json.JSONDecodeError:
                                continue
                    if full_response:
                        return full_response
                    else:
                        raise ValueError("Could not parse Ollama response")
            elif response.status_code == 404:
                raise ValueError(f"Model '{model}' not found. Please run: ollama pull {model}")
            else:
                raise ValueError(f"Ollama API returned status code {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            raise ValueError("Could not connect to Ollama. Make sure it's running with 'ollama serve'")
            
    except Exception as e:
        console.print(f"[red]Error creating summary:[/red] {str(e)}")
        if "Model" in str(e) and "not found" in str(e):
            model = get_ollama_model()
            console.print(f"[yellow]Tip:[/yellow] Run this command to download the model:")
            console.print(f"[blue]ollama pull {model}[/blue]")
        return None

def save_summary_as_note(url: str, title: Optional[str], summary: str) -> bool:
    """
    Save the summary as a markdown note.
    
    Args:
        url: The URL of the summarized article
        title: The title of the article (if available)
        summary: The generated summary
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Create filename from title or timestamp
        if title:
            # Clean title for filename
            filename = re.sub(r'[<>:"/\\|?*]', '', title)
            filename = re.sub(r'\s+', '_', filename)
        else:
            filename = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        filename = f"{filename}.md"
        notes_path = get_default_notes_path()
        filepath = os.path.join(notes_path, filename)
        
        # Create markdown content
        markdown_content = f"""# {title or 'Article Summary'}

## Source
{url}

## Summary
{summary}

---
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        # Save the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        console.print(f"\n[green]Summary saved to:[/green] {filepath}")
        return True
        
    except Exception as e:
        console.print(f"[red]Error saving summary:[/red] {str(e)}")
        return False

def format_summary(url: str) -> str:
    """Format and optionally save a summary of the webpage."""
    summary = create_summary(url)
    if summary:
        console.print("\n[green]Summary generated successfully![/green]\n")
        console.print(Markdown(summary))
        
        # Ask if user wants to save the summary
        save_prompt = prompt("\nWould you like to save this summary as a note? (y/n): ").lower().strip()
        if save_prompt.startswith('y'):
            # Get the title if we can
            _, content = extract_article_content(url)
            title = None
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else None
            except:
                pass
                
            save_summary_as_note(url, title, summary)
            
        return summary
    else:
        return "Failed to generate summary. Please check the URL and try again."
