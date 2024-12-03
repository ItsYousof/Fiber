"""Chat utilities for Fiber."""

import os
import json
import time
import sys
import requests
from rich.console import Console
from typing import Optional
from requests.exceptions import Timeout, RequestException

console = Console()

# Configuration
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
RETRY_DELAY = 2

def get_ollama_model() -> str:
    """Get the Ollama model from environment or use default."""
    return os.getenv('OLLAMA_MODEL', 'qwen:7b')

def chat_with_ai(message: str) -> Optional[str]:
    """
    Chat with the AI using Ollama API with retry logic.
    
    Args:
        message: The message to send to the AI
        
    Returns:
        The AI's response or None if failed
    """
    model = get_ollama_model()
    print(f"Debug: Starting chat with message: '{message}'", file=sys.stderr)
    print(f"Debug: Using model: {model}", file=sys.stderr)
    
    # Ensure message is a string
    if not isinstance(message, str):
        print(f"Debug: Converting message from {type(message)} to str", file=sys.stderr)
        message = str(message)
        
    # Prepare request data
    data = {
        'model': model,
        'prompt': f'You are a helpful AI assistant. Respond to: {message}',
        'stream': True
    }
    print(f"Debug: Request data: {data}", file=sys.stderr)
    
    # Initialize retry counter
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            # Make request to Ollama API
            response = requests.post(
                'http://localhost:11434/api/generate',
                json=data,
                timeout=TIMEOUT_SECONDS,
                stream=True
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Process streamed response
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line)
                        if 'response' in json_response:
                            full_response += json_response['response']
                            # Immediately flush for web interface
                            sys.stdout.flush()
                        elif "error" in json_response:
                            error_msg = json_response["error"]
                            print(f"Debug: Ollama API error: {error_msg}", file=sys.stderr)
                            if "rate limit exceeded" in error_msg.lower():
                                return "I'm currently rate limited. Please try again in a few minutes."
                            return f"Error: {error_msg}"
                    except json.JSONDecodeError as e:
                        print(f"Debug: Error decoding JSON: {e}", file=sys.stderr)
                        continue
            
            if not full_response:
                print("Debug: No content received from Ollama", file=sys.stderr)
                return "I couldn't generate a response. Please try again."
                
            print(f"Debug: Successfully generated response of length: {len(full_response)}", file=sys.stderr)
            return full_response.strip()
            
        except Timeout:
            retries += 1
            print(f"Debug: Request timed out (attempt {retries}/{MAX_RETRIES})", file=sys.stderr)
            if retries < MAX_RETRIES:
                print(f"Debug: Retrying in {RETRY_DELAY} seconds...", file=sys.stderr)
                time.sleep(RETRY_DELAY)
            continue
            
        except RequestException as e:
            print(f"Debug: Request failed: {str(e)}", file=sys.stderr)
            if "Connection refused" in str(e):
                return "Error: Unable to connect to Ollama. Please make sure Ollama is running."
            return f"Error: Failed to communicate with AI service: {str(e)}"
            
        except Exception as e:
            print(f"Debug: Unexpected error: {str(e)}", file=sys.stderr)
            return f"Error: An unexpected error occurred: {str(e)}"
    
    # If we've exhausted all retries
    if retries == MAX_RETRIES:
        return "Error: Request timed out after multiple attempts. Please try again later."
    
    return None
