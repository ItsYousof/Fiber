# Fiber AI Assistant

A powerful, modular AI assistant that runs locally on your machine.

## Features

### Core Features
- 🤖 Local AI Model Integration (via Ollama)
- 💻 System Context Awareness
- 🌐 Web Search Integration
- 📝 Document Creation and Management
- ⚡ Interactive Command Line Interface
- 🎨 Rich Console Formatting
- 🔄 Session Management
- ⚙️ Customizable User Preferences

### Web Interface
Access Fiber through a modern web interface:
- Clean, responsive design
- Real-time streaming responses
- Syntax highlighting for code
- Markdown rendering
- Easy command input

### Commands

#### General Commands
- `ask [question]`: Ask Fiber anything and get AI-powered responses
- `info`: Display system and session information
- `preferences`: Show current user preferences
- `set_preference [key] [value]`: Modify user settings
- `help`: Show help message
- `exit/quit`: Exit the program

#### Document Management
- `write [topic]`: Create a detailed document about any topic
  - Shows real-time progress with word count
  - Displays elapsed time while writing
  - Option to automatically open created documents

#### Web Integration
- `search [query]`: Intelligent web search across multiple engines
  - Searches Google, Bing, and DuckDuckGo simultaneously
  - Ranks results by relevance
  - Automatically opens best result in Chrome
  - Shows detailed result information

#### Language Tools
- `define [word]`: Get comprehensive word definitions
  - Multiple dictionary sources
  - Pronunciation and phonetics
  - All meanings and parts of speech
  - Usage examples
  - Etymology when available
  - Example: `define "ephemeral"`

#### Analysis Tools
- `compare [items...]`: Compare different theories, ideas, or arguments
  - Side-by-side comparison with key aspects
  - Similarities and differences analysis
  - Summary and recommendations
  - Rich table formatting
  - Example: `compare "Python" "JavaScript" "Ruby"`

#### Creativity Tools
- `brainstorm [topic] --type [category]`: Generate creative ideas for any topic
  - Categories: project, assignment, writing, general
  - Generates 3 unique ideas with titles and descriptions
  - Examples:
    ```bash
    # Generate project ideas
    fiber brainstorm "artificial intelligence" --type project

    # Get writing prompts
    fiber brainstorm "space exploration" --type writing

    # Create assignment ideas
    fiber brainstorm "environmental science" --type assignment
    ```

#### Weather and Time
- `weather [city]`: Get current weather information for any city
- `time [timezone]`: Check current time in different timezones

## Setup

### Prerequisites
- Node.js (Latest LTS version)
- npm (comes with Node.js)
- Ollama for local AI model inference
- Python 3.8+
- Windows/Linux/MacOS
- Chrome (for web search feature)

### Installation

1. Install Python from [Python.org](https://python.org)
   - **IMPORTANT:** During installation, check "Add Python to PATH"
   - If you forgot to check it, you can add it manually:
     1. Open System Properties (Win + Pause/Break)
     2. Click "Advanced system settings"
     3. Click "Environment Variables"
     4. Under "System Variables", find and select "Path"
     5. Click "Edit"
     6. Add these two paths (replace X.X with your Python version, e.g., 3.11):
        ```
        C:\Users\YourUsername\AppData\Local\Programs\Python\PythonX.X\
        C:\Users\YourUsername\AppData\Local\Programs\Python\PythonX.X\Scripts\
        ```
     7. Click "OK" on all windows
     8. Restart your terminal

2. Install Ollama from [Ollama.ai](https://ollama.ai)
   - After installation, open a terminal and run:
   ```bash
   ollama pull llama3.2:1b
   ```

3. Install Fiber:
   ```bash
   pip install fiber
   ```

4. Create a `.env` file in your home directory with:
   ```env
   # Ollama Configuration
   OLLAMA_MODEL=llama3.2:1b

   # Where to save generated files
   DEFAULT_PATH=D:/Fiber_Notes   # Change this to your preferred path
   ```

That's it! Now you can use Fiber:

```bash
# Ask anything
fiber ask "What do you think of AI?"

# Get definitions
fiber define "serendipity"

# Search the web
fiber search "best pizza in NYC"

# Compare things
fiber compare "Python vs JavaScript"

# Generate ideas
fiber brainstorm "weekend project ideas"
```

## Having Issues?

### Command Not Found
If you get "fiber command not found", your PATH might not be set up correctly:

1. **Check your Python installation**:
   ```bash
   python --version
   ```
   If this fails, Python is not in PATH

2. **Check pip installation**:
   ```bash
   pip --version
   ```
   If this fails, pip is not in PATH

3. **Fix PATH issues**:
   - Open System Properties (Win + Pause/Break)
   - Click "Environment Variables"
   - Under "System Variables", edit "Path"
   - Make sure these paths exist:
     ```
     C:\Users\YourUsername\AppData\Local\Programs\Python\PythonX.X\
     C:\Users\YourUsername\AppData\Local\Programs\Python\PythonX.X\Scripts\
     ```
   - Restart your terminal

4. **Alternative Installation**:
   ```bash
   python -m pip install --user fiber
   ```

### Other Issues

- If you get rate limit errors, wait a few minutes and try again
- Make sure Ollama is running in the background

## Optional Features

To use weather commands, get an API key from [OpenWeatherMap](https://openweathermap.org/api) and add to your `.env`:
```env
OPENWEATHERMAP_API_KEY=your_api_key_here
```

## Usage

### Starting Fiber
```bash
python -m fiber
```

### Direct Commands
```bash
# Ask a question
python -m fiber ask "What is Python?"

# Search the web
python -m fiber search "best python practices"

# Check weather
python -m fiber ask "weather in London"

# Create a document
python -m fiber ask "write about machine learning"
```

### Interactive Mode
```bash
> ask What is Python?
> search best python practices
> write about machine learning
```

### Web Interface
1. Start the server using `npm start` in the `web` directory
2. Open your browser to `http://localhost:3000`
3. Enter commands in the input box at the bottom
4. View AI responses with proper formatting and syntax highlighting

### Available Commands
- `ask [question]`: Ask Fiber anything and get AI-powered responses
- `info`: Display system and session information
- `preferences`: Show current user preferences
- `set_preference [key] [value]`: Modify user settings
- `help`: Show help message
- `exit/quit`: Exit the program

## System Requirements
- Python 3.8+
- Windows/Linux/MacOS
- Chrome (for web search feature)
- Ollama (for AI features)

## Configuration

### User Preferences
Customize your experience with the following preferences:
- `default_path`: Default path for documents

### Environment Variables
- `OPENWEATHERMAP_API_KEY`: For weather information
- `OLLAMA_MODEL`: Preferred AI model
- `DEFAULT_PATH`: Default document storage path

## Development

### Project Structure
```
fiber/
├── fiber/
│   ├── __init__.py
│   ├── cli.py              # Main CLI interface
│   ├── system_context.py   # System awareness module
│   ├── session.py          # Session management
│   └── prompts/
│       ├── weather/        # Weather functionality
│       ├── time/           # Time utilities
│       ├── creator/        # Document creation
│       ├── search/         # Web search features
│       └── summarizer/     # Content summarization
└── web/
    ├── index.html
    ├── main.js
    └── styles.css
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
[MIT License](LICENSE)
