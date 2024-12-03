"""Time utilities for Fiber."""
from datetime import datetime
import pytz

def get_current_time(timezone: str = None) -> dict:
    """Get current time, optionally for a specific timezone."""
    try:
        if timezone:
            tz = pytz.timezone(timezone)
            current = datetime.now(tz)
        else:
            current = datetime.now()
            
        return {
            "time": current.strftime("%I:%M %p"),
            "date": current.strftime("%B %d, %Y"),
            "day": current.strftime("%A"),
            "timezone": timezone or "local"
        }
    except Exception as e:
        print(f"Error getting time: {str(e)}")
        return None

def format_time_response(time_data: dict) -> str:
    """Format time data into a human-readable response."""
    return (
        f"It's currently {time_data['time']} on {time_data['day']}, "
        f"{time_data['date']} ({time_data['timezone']} time)."
    )
