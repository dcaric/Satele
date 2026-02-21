import urllib.request
import json
import ssl

def get_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=43.5081&longitude=16.4402&current=temperature_2m,wind_speed_10m,weather_code"
    
    # Handle SSL issues common on Mac
    context = ssl._create_unverified_context()
    
    try:
        with urllib.request.urlopen(url, context=context) as response:
            data = json.loads(response.read().decode())
            
        temp = data['current']['temperature_2m']
        wind = data['current']['wind_speed_10m']
        code = data['current']['weather_code']
        
        interpretations = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 95: "Thunderstorm"
        }
        desc = interpretations.get(code, "Cloudy")
        
        summary = f"📊 *Split Weather Summary* 📊\n"
        summary += f"--------------------------\n"
        summary += f"🌡️ *Temperature:* {temp}°C\n"
        summary += f"☁️ *Condition:* {desc}\n"
        summary += f"💨 *Wind Speed:* {wind} m/s\n"
        summary += f"--------------------------"
        print(summary)
    except Exception as e:
        print(f"❌ Error fetching weather: {e}")

if __name__ == "__main__":
    get_weather()
