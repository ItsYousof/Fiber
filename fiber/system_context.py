"""
System and user context management for Fiber.
Handles system awareness, user preferences, and session history.
"""

import os
import sys
import platform
import psutil
import locale
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import subprocess
from rich.console import Console
from dataclasses import dataclass, asdict
import shutil

console = Console()

@dataclass
class SystemInfo:
    os_name: str
    os_version: str
    python_version: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_usage: Dict[str, Dict[str, int]]
    terminal: str
    encoding: str
    language: str
    timezone: str

@dataclass
class UserPreferences:
    theme: str = "default"
    verbosity: str = "normal"
    max_history: int = 100
    default_path: str = "D:/Fiber_Notes"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
class SystemContext:
    def __init__(self):
        self._init_directories()  # Initialize directories first
        self.system_info = self._get_system_info()
        self.user_prefs = self._load_user_preferences()
        self.command_history: List[Dict] = []
        
    def _init_directories(self):
        """Initialize necessary directories for Fiber."""
        paths = {
            'config': Path.home() / '.fiber',
            'cache': Path.home() / '.fiber' / 'cache',
            'history': Path.home() / '.fiber' / 'history',
            'logs': Path.home() / '.fiber' / 'logs'
        }
        
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
        self.paths = paths

    def _get_system_info(self) -> SystemInfo:
        """Gather system information."""
        try:
            # Get disk usage for all mounted drives
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free
                    }
                except Exception:
                    continue

            return SystemInfo(
                os_name=platform.system(),
                os_version=platform.version(),
                python_version=sys.version.split()[0],
                cpu_count=psutil.cpu_count(),
                memory_total=psutil.virtual_memory().total,
                memory_available=psutil.virtual_memory().available,
                disk_usage=disk_usage,
                terminal=os.environ.get('TERM', 'unknown'),
                encoding=sys.getfilesystemencoding(),
                language=locale.getdefaultlocale()[0],
                timezone=datetime.now().astimezone().tzname()
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Error getting full system info: {e}[/yellow]")
            return SystemInfo(
                os_name=platform.system(),
                os_version="unknown",
                python_version=sys.version.split()[0],
                cpu_count=0,
                memory_total=0,
                memory_available=0,
                disk_usage={},
                terminal="unknown",
                encoding=sys.getfilesystemencoding(),
                language="unknown",
                timezone="unknown"
            )

    def _load_user_preferences(self) -> UserPreferences:
        """Load user preferences from config file."""
        config_file = self.paths['config'] / 'preferences.json'
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    prefs_dict = json.load(f)
                return UserPreferences(**prefs_dict)
            except Exception as e:
                console.print(f"[yellow]Warning: Error loading preferences: {e}[/yellow]")
                
        return UserPreferences()

    def save_preferences(self):
        """Save current preferences to config file."""
        config_file = self.paths['config'] / 'preferences.json'
        try:
            with open(config_file, 'w') as f:
                json.dump(asdict(self.user_prefs), f, indent=4)
        except Exception as e:
            console.print(f"[red]Error saving preferences: {e}[/red]")

    def add_to_history(self, command: str, args: Dict = None):
        """Add a command to the session history."""
        entry = {
            'timestamp': datetime.now().strftime(self.user_prefs.date_format),
            'command': command,
            'args': args or {}
        }
        self.command_history.append(entry)
        
        # Trim history if needed
        if len(self.command_history) > self.user_prefs.max_history:
            self.command_history = self.command_history[-self.user_prefs.max_history:]

    def save_history(self):
        """Save command history to file."""
        history_file = self.paths['history'] / f"history_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self.command_history, f, indent=4)
        except Exception as e:
            console.print(f"[red]Error saving history: {e}[/red]")

    def get_installed_tools(self) -> Dict[str, Optional[str]]:
        """Detect installed development tools and their versions."""
        tools = {}
        
        # Check for common development tools
        tool_commands = {
            'git': ['git', '--version'],
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
            'yarn': ['yarn', '--version'],
            'docker': ['docker', '--version'],
            'java': ['java', '-version'],
            'mvn': ['mvn', '--version'],
            'gcc': ['gcc', '--version'],
            'rustc': ['rustc', '--version'],
            'go': ['go', 'version']
        }
        
        for tool, command in tool_commands.items():
            try:
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0]
                    tools[tool] = version
                else:
                    tools[tool] = None
            except Exception:
                tools[tool] = None
                
        return tools

    def get_resource_usage(self) -> Dict:
        """Get current system resource usage."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': {
                path: psutil.disk_usage(path).percent
                for path in self.system_info.disk_usage.keys()
            }
        }

    def format_number(self, number: float) -> str:
        """Format number according to user's locale."""
        try:
            return locale.format_string("%.2f", number, grouping=True)
        except Exception:
            return str(number)

    def format_date(self, date: datetime) -> str:
        """Format date according to user's preferences."""
        return date.strftime(self.user_prefs.date_format)

    def get_session_summary(self) -> Dict:
        """Get summary of current session."""
        return {
            'start_time': self.command_history[0]['timestamp'] if self.command_history else None,
            'command_count': len(self.command_history),
            'last_command': self.command_history[-1] if self.command_history else None,
            'system_resources': self.get_resource_usage()
        }

# Global instance
context = SystemContext()
