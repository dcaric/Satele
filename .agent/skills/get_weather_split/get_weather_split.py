import urllib.request
import json
import ssl

def get_weather():
    # Fetch current and daily forecast for 5 days
    url = "https://api.open-meteo.com/v1/forecast?latitude=43.5081&longitude=16.4402&current=temperature_2m,wind_speed_10m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=5"
    
    # Common interpretations for weather codes
    interpretations = {
        0: "☀️ Clear", 1: "🌤️ Mainly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
        45: "🌫️ Fog", 48: "🌫️ Rime fog", 51: "🌦️ Light drizzle", 53: "🌦️ Moderate drizzle",
        55: "🌧️ Dense drizzle", 61: "🌧️ Slight rain", 63: "🌧️ Moderate rain", 65: "🌧️ Heavy rain",
        71: "❄️ Slight snow", 73: "❄️ Moderate snow", 75: "❄️ Heavy snow", 95: "⛈️ Thunderstorm"
    }

    # Handle SSL issues common on Mac
    context = ssl._create_unverified_context()
    
    try:
        with urllib.request.urlopen(url, context=context) as response:
            data = json.loads(response.read().decode())
            
        # Current Weather
        temp = data['current']['temperature_2m']
        wind = data['current']['wind_speed_10m']
        code = data['current']['weather_code']
        desc = interpretations.get(code, "☁️ Cloudy")
        
        summary = f"📊 *Split Weather Summary* 📊\n"
        summary += f"--------------------------\n"
        summary += f"🌡️ *Temperature:* {temp}°C\n"
        summary += f"☁️ *Condition:* {desc}\n"
        summary += f"💨 *Wind Speed:* {wind} m/s\n"
        summary += f"--------------------------\n\n"
        
        # 5-Day Forecast
        summary += f"📅 *5-Day Forecast:* \n"
        daily = data['daily']
        for i in range(len(daily['time'])):
            date = daily['time'][i]
            max_t = daily['temperature_2m_max'][i]
            min_t = daily['temperature_2m_min'][i]
            d_code = daily['weather_code'][i]
            d_desc = interpretations.get(d_code, "☁️")
            
            # Format date to be shorter if possible (e.g. 2026-02-21)
            summary += f"• {date}: {d_desc} | {min_t}° / {max_t}°C\n"
            
        summary += f"--------------------------"
        print(summary)
    except Exception as e:
        print(f"❌ Error fetching weather: {e}")

if __name__ == "__main__":
    get_weather()
