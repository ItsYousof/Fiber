"""Definition utilities for Fiber."""

import requests
from typing import Optional
import os
import json

def get_word_definition(word: str) -> Optional[str]:
    """Get a simple, concise definition of a word."""
    word = word.strip().lower()
    
    try:
        # Try Free Dictionary API first
        response = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()[0]
            # Get the first definition from the first meaning
            if 'meanings' in data and len(data['meanings']) > 0:
                meaning = data['meanings'][0]
                part_of_speech = meaning.get('partOfSpeech', '')
                definitions = meaning.get('definitions', [])
                if definitions:
                    definition = definitions[0]['definition'].capitalize()
                    if part_of_speech:
                        return f"({part_of_speech}) {definition}"
                    return definition
    except (requests.RequestException, json.JSONDecodeError, IndexError, KeyError):
        pass

    # Fallback to Ollama for a simple definition
    try:
        model = os.getenv('OLLAMA_MODEL', 'qwen:7b')
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": (
                    f'Define the word "{word}" in one clear, concise sentence. '
                    'Include the part of speech in parentheses at the start. '
                    'Example format: "(noun) A clear definition here."'
                ),
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            definition = response.json().get("response", "").strip()
            if definition:
                # Clean up any extra quotes or periods at the end
                definition = definition.strip('"').rstrip('.')
                return definition + "."

    except (requests.RequestException, json.JSONDecodeError):
        pass
    
    return None

def display_definition(definition: str):
    """Display the word definition in a simple format."""
    print(f"{definition}")
