"""Session management for Fiber CLI."""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from prompt_toolkit.history import InMemoryHistory

# Initialize history
prompt_history = InMemoryHistory()

class Session:
    def __init__(self):
        """Initialize a new session."""
        self.commands: List[str] = []
        self.context: Dict = {}
        self.last_file: Optional[str] = None
        self._load()
        
    def _get_session_file(self) -> Path:
        """Get the session file path."""
        session_dir = Path.home() / '.fiber'
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / 'session.json'
        
    def _load(self):
        """Load session from file."""
        session_file = self._get_session_file()
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    self.commands = data.get('commands', [])
                    self.context = data.get('context', {})
                    self.last_file = data.get('last_file')
                    
                    # Add commands to prompt history
                    for cmd in self.commands:
                        prompt_history.append_string(cmd)
            except Exception:
                # Start fresh if there's an error
                pass
                
    def save(self):
        """Save session to file."""
        session_file = self._get_session_file()
        try:
            with open(session_file, 'w') as f:
                json.dump({
                    'commands': self.commands,
                    'context': self.context,
                    'last_file': self.last_file
                }, f, indent=4)
        except Exception:
            pass
            
    def add_command(self, command: str):
        """Add a command to the session history."""
        self.commands.append(command)
        prompt_history.append_string(command)
        
    def update_context(self, key: str, value: str):
        """Update session context."""
        self.context[key] = value
        
    def get_suggestions(self, current_input: str) -> List[str]:
        """Get command suggestions based on history."""
        suggestions = []
        current_input = current_input.lower()
        
        # Add recent commands that match
        for cmd in reversed(self.commands):
            if current_input in cmd.lower() and cmd not in suggestions:
                suggestions.append(cmd)
                
        # Add common commands if input is empty
        if not current_input:
            common_commands = [
                "help",
                "weather in London",
                "time in New York",
                "create notes about Python",
                "summarize https://example.com",
                "info",
                "preferences"
            ]
            suggestions.extend(cmd for cmd in common_commands if cmd not in suggestions)
                
        return suggestions[:5]  # Limit to 5 suggestions
