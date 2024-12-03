"""Comparison utilities for Fiber."""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
from pathlib import Path

console = Console()

# Constants for image generation
COLORS = {
    'background': (255, 255, 255),
    'title': (47, 84, 150),
    'header': (0, 0, 0),
    'text': (60, 60, 60),
    'border': (200, 200, 200),
    'highlight': (70, 130, 180)
}

class ImageGenerator:
    def __init__(self, width=1200, padding=20, line_height=30):
        self.width = width
        self.padding = padding
        self.line_height = line_height
        self.current_y = padding
        
        # Try to load Arial font, fall back to default if not available
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 36)
            self.header_font = ImageFont.truetype("arial.ttf", 24)
            self.text_font = ImageFont.truetype("arial.ttf", 20)
        except OSError:
            # Fallback to default font
            self.title_font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()
            self.text_font = ImageFont.load_default()
    
    def calculate_text_width(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        """Calculate width of text using the newer getbbox method."""
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0] if bbox else 0
    
    def calculate_text_height(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> int:
        """Calculate the height needed for wrapped text."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            line = ' '.join(current_line)
            w = self.calculate_text_width(line, font)
            if w > max_width:
                if len(current_line) == 1:
                    lines.append(line)
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return len(lines) * self.line_height
    
    def wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wrap text to fit within a given width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            line = ' '.join(current_line)
            w = self.calculate_text_width(line, font)
            if w > max_width:
                if len(current_line) == 1:
                    lines.append(line)
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines
    
    def generate_comparison_image(self, result: 'ComparisonResult') -> Image.Image:
        """Generate an image for the comparison result."""
        # Calculate total height needed
        height = self.padding  # Start with top padding
        
        # Title space
        height += self.line_height * 2
        
        # Space for each comparison point
        content_width = self.width - (2 * self.padding)
        for point in result.points:
            height += self.line_height  # Aspect header
            max_desc_height = 0
            for desc in point.descriptions:
                desc_height = self.calculate_text_height(desc, self.text_font, content_width // len(result.items))
                max_desc_height = max(max_desc_height, desc_height)
            height += max_desc_height + self.padding
            
            if point.similarities:
                height += self.calculate_text_height(f"Similarities: {point.similarities}", 
                                                   self.text_font, content_width) + self.padding
            if point.differences:
                height += self.calculate_text_height(f"Differences: {point.differences}", 
                                                   self.text_font, content_width) + self.padding
        
        # Space for summary and recommendation
        if result.summary != 'No summary available':
            height += self.line_height
            height += self.calculate_text_height(result.summary, self.text_font, content_width) + self.padding
        
        if result.recommendation != 'No recommendation available':
            height += self.line_height
            height += self.calculate_text_height(result.recommendation, self.text_font, content_width)
        
        height += self.padding  # Bottom padding
        
        # Create the image
        img = Image.new('RGB', (self.width, height), COLORS['background'])
        draw = ImageDraw.Draw(img)
        
        # Reset current_y
        self.current_y = self.padding
        
        # Draw title
        title = f"Comparison of {' vs '.join(result.items)}"
        draw.text((self.padding, self.current_y), title, 
                 font=self.title_font, fill=COLORS['title'])
        self.current_y += self.line_height * 2
        
        # Draw comparison points
        for point in result.points:
            # Draw aspect header
            draw.text((self.padding, self.current_y), point.aspect, 
                     font=self.header_font, fill=COLORS['header'])
            self.current_y += self.line_height
            
            # Draw descriptions
            start_y = self.current_y
            max_height = 0
            col_width = (content_width - self.padding) // len(result.items)
            
            for i, desc in enumerate(point.descriptions):
                x = self.padding + (i * col_width)
                wrapped_lines = self.wrap_text(desc, self.text_font, col_width - self.padding)
                
                for line in wrapped_lines:
                    draw.text((x, self.current_y), line, 
                             font=self.text_font, fill=COLORS['text'])
                    self.current_y += self.line_height
                
                max_height = max(max_height, len(wrapped_lines) * self.line_height)
                self.current_y = start_y  # Reset for next column
            
            self.current_y = start_y + max_height + self.padding
            
            # Draw similarities and differences
            if point.similarities:
                wrapped_lines = self.wrap_text(f"Similarities: {point.similarities}", 
                                             self.text_font, content_width)
                for line in wrapped_lines:
                    draw.text((self.padding, self.current_y), line, 
                             font=self.text_font, fill=COLORS['highlight'])
                    self.current_y += self.line_height
                self.current_y += self.padding
            
            if point.differences:
                wrapped_lines = self.wrap_text(f"Differences: {point.differences}", 
                                             self.text_font, content_width)
                for line in wrapped_lines:
                    draw.text((self.padding, self.current_y), line, 
                             font=self.text_font, fill=COLORS['highlight'])
                    self.current_y += self.line_height
                self.current_y += self.padding
        
        # Draw summary and recommendation
        if result.summary != 'No summary available':
            draw.text((self.padding, self.current_y), "Summary:", 
                     font=self.header_font, fill=COLORS['header'])
            self.current_y += self.line_height
            
            wrapped_lines = self.wrap_text(result.summary, self.text_font, content_width)
            for line in wrapped_lines:
                draw.text((self.padding, self.current_y), line, 
                         font=self.text_font, fill=COLORS['text'])
                self.current_y += self.line_height
            self.current_y += self.padding
        
        if result.recommendation != 'No recommendation available':
            draw.text((self.padding, self.current_y), "Recommendation:", 
                     font=self.header_font, fill=COLORS['header'])
            self.current_y += self.line_height
            
            wrapped_lines = self.wrap_text(result.recommendation, self.text_font, content_width)
            for line in wrapped_lines:
                draw.text((self.padding, self.current_y), line, 
                         font=self.text_font, fill=COLORS['text'])
                self.current_y += self.line_height
        
        return img

def save_comparison_image(result: 'ComparisonResult', base_path: str = None) -> str:
    """Generate and save an image of the comparison."""
    if base_path is None:
        base_path = os.getenv('DEFAULT_PATH', 'D:/Fiber_Notes')
    
    # Create comparison directory if it doesn't exist
    comparison_dir = Path(base_path) / 'comparisons'
    comparison_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    items_text = '_vs_'.join(item.replace(' ', '_') for item in result.items)
    filename = f"comparison_{items_text}_{timestamp}.png"
    filepath = comparison_dir / filename
    
    # Generate and save image
    generator = ImageGenerator()
    img = generator.generate_comparison_image(result)
    img.save(filepath)
    
    return str(filepath)

@dataclass
class ComparisonPoint:
    aspect: str
    descriptions: List[str]
    similarities: str
    differences: str

@dataclass
class ComparisonResult:
    items: List[str]
    points: List[ComparisonPoint]
    summary: str
    recommendation: str

def create_comparison_prompt(items: List[str]) -> str:
    """Create a detailed prompt for comparison."""
    return f"""Compare the following items in detail: {', '.join(items)}

For each important aspect, provide:
1. A clear description for each item
2. Key similarities
3. Notable differences

Also include:
- A balanced analysis of strengths and weaknesses
- Common misconceptions or important nuances
- Practical implications or real-world applications
- A final summary and recommendation

Format your response as a structured comparison with clear sections."""

def get_comparison(items: List[str]) -> ComparisonResult:
    """Get a detailed comparison using Ollama."""
    try:
        # Get model from environment or use default
        model = os.getenv('OLLAMA_MODEL', 'qwen:7b')
        
        # Create the request
        with console.status("[bold blue]Connecting to Ollama...") as status:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": create_comparison_prompt(items),
                    "stream": True
                },
                stream=True,
                timeout=60  # Increased timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status code {response.status_code}")
            
            # Process streaming response
            content = []
            status.update("[bold blue]Generating comparison...")
            
            try:
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line.decode())
                            if 'response' in json_response:
                                chunk = json_response['response']
                                content.append(chunk)
                                # Show some progress
                                if len(chunk.strip()) > 0:
                                    status.update(f"[bold blue]Analyzing: {chunk.strip()[:50]}...")
                        except json.JSONDecodeError:
                            continue
            except requests.exceptions.ChunkedEncodingError:
                # Handle streaming errors gracefully
                if not content:
                    raise Exception("Stream interrupted before receiving content")
                # If we have some content, continue processing
                console.print("[yellow]Note: Stream ended early but continuing with received content[/yellow]")
            
            if not content:
                raise Exception("No response received from AI model")
            
            # Combine all content
            full_content = "".join(content)
            
            # Process the content to extract structured information
            status.update("[bold blue]Structuring comparison data...")
            sections = parse_comparison_content(full_content)
            
            # Validate the parsed sections
            if not sections['points']:
                # If parsing failed, return raw format
                console.print("[yellow]Note: Structured parsing failed, displaying raw comparison[/yellow]")
                return ComparisonResult(
                    items=items,
                    points=[ComparisonPoint(
                        aspect="Comparison",
                        descriptions=[full_content],
                        similarities="",
                        differences=""
                    )],
                    summary="Raw comparison data",
                    recommendation="Please see the main comparison text above"
                )
            
            return ComparisonResult(
                items=items,
                points=sections['points'],
                summary=sections.get('summary', 'No summary available'),
                recommendation=sections.get('recommendation', 'No recommendation available')
            )
        
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to Ollama. Make sure Ollama is running (https://ollama.ai)")
    except requests.exceptions.Timeout:
        raise Exception("Request to Ollama timed out. Try using a simpler comparison or check Ollama's status")
    except Exception as e:
        console.print(f"[yellow]Debug - Full error:[/yellow] {str(e)}")
        raise

def parse_comparison_content(content: str) -> Dict:
    """Parse the AI response into structured sections."""
    # Split content into sections
    lines = content.split('\n')
    current_section = None
    sections = {
        'points': [],
        'summary': '',
        'recommendation': ''
    }
    
    current_point = None
    collecting_descriptions = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect section headers
        lower_line = line.lower()
        if 'summary' in lower_line and 'summary:' in lower_line:
            current_section = 'summary'
            sections['summary'] = line.split(':', 1)[1].strip()
            continue
        elif 'recommend' in lower_line and ':' in line:
            current_section = 'recommendation'
            sections['recommendation'] = line.split(':', 1)[1].strip()
            continue
        
        # Process comparison points
        if ':' in line and not collecting_descriptions:
            if current_point:
                sections['points'].append(current_point)
            aspect = line.split(':', 1)[0].strip()
            current_point = ComparisonPoint(
                aspect=aspect,
                descriptions=[],
                similarities="",
                differences=""
            )
            collecting_descriptions = True
            continue
            
        if collecting_descriptions:
            if 'similarities:' in lower_line:
                current_point.similarities = line.split(':', 1)[1].strip()
                continue
            elif 'differences:' in lower_line:
                current_point.differences = line.split(':', 1)[1].strip()
                collecting_descriptions = False
                continue
            else:
                current_point.descriptions.append(line)
    
    # Add the last point if exists
    if current_point:
        sections['points'].append(current_point)
    
    return sections

def display_comparison(result: ComparisonResult):
    """Display the comparison in a rich formatted table."""
    # Handle raw format
    if len(result.points) == 1 and result.points[0].aspect == "Comparison":
        console.print(Panel(Markdown(result.points[0].descriptions[0])))
        return
        
    # Create main comparison table
    table = Table(title=f"Comparison of {' vs '.join(result.items)}")
    
    # Add columns
    table.add_column("Aspect", style="bold blue")
    for item in result.items:
        table.add_column(item, style="green")
    table.add_column("Similarities", style="yellow")
    table.add_column("Differences", style="red")
    
    # Add rows
    for point in result.points:
        row = [point.aspect]
        for desc in point.descriptions:
            row.append(desc)
        row.append(point.similarities)
        row.append(point.differences)
        table.add_row(*row)
    
    # Display the table
    console.print(table)
    
    # Display summary and recommendation
    if result.summary != 'No summary available':
        console.print("\n[bold blue]Summary:[/bold blue]")
        console.print(Panel(Markdown(result.summary)))
    
    if result.recommendation != 'No recommendation available':
        console.print("\n[bold blue]Recommendation:[/bold blue]")
        console.print(Panel(Markdown(result.recommendation)))

def save_comparison_image(result: ComparisonResult, base_path: str = None) -> str:
    """Generate and save an image of the comparison."""
    if base_path is None:
        base_path = os.getenv('DEFAULT_PATH', 'D:/Fiber_Notes')
    
    # Create comparison directory if it doesn't exist
    comparison_dir = Path(base_path) / 'comparisons'
    comparison_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    items_text = '_vs_'.join(item.replace(' ', '_') for item in result.items)
    filename = f"comparison_{items_text}_{timestamp}.png"
    filepath = comparison_dir / filename
    
    # Generate and save image
    generator = ImageGenerator()
    img = generator.generate_comparison_image(result)
    img.save(filepath)
    
    return str(filepath)
