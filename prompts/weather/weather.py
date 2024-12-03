"""Weather functionality for Fiber."""
import os
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Load environment variables
load_dotenv()

def get_weather(city: str) -> Optional[Dict]:
    """Get weather information for a city using OpenWeatherMap API."""
    try:
        API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
        
        if not API_KEY or API_KEY == "your_api_key_here":
            console.print("\n[red]Error:[/red] OpenWeatherMap API key not found. "
                        "Please add your API key to the .env file.\n"
                        "You can get one at: https://openweathermap.org/api\n")
            return None
            
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"]
            }
        elif response.status_code == 401:
            console.print("\n[red]Error:[/red] Invalid OpenWeatherMap API key. "
                        "Please check your API key in the .env file.\n")
            return None
        else:
            console.print(f"\n[red]Error:[/red] Could not get weather for {city}. "
                        f"Status code: {response.status_code}\n")
            return None
    except Exception as e:
        console.print(f"\n[red]Error:[/red] Error getting weather: {str(e)}\n")
        return None

def format_weather_response(weather_data: Dict) -> str:
    """Format weather data into a human-readable response."""
    return (
        f"The current temperature is {weather_data['temperature']}°C with "
        f"{weather_data['description']}. The humidity is {weather_data['humidity']}% "
        f"and wind speed is {weather_data['wind_speed']} m/s."
    )
