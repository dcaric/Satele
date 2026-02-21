import requests
import json

def get_weather_split():
    try:
        url = 'https://api.open-meteo.com/v1/forecast?latitude=43.51&longitude=16.44&current=temperature_2m,weather_code&timezone=Europe%2FBerlin'
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        temperature = data['current']['temperature_2m']
        weather_code = data['current']['weather_code']

        weather_interpretations = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Drizzle: Light intensity",
            53: "Drizzle: Moderate intensity",
            55: "Drizzle: Dense intensity",
            56: "Freezing Drizzle: Light intensity",
            57: "Freezing Drizzle: Dense intensity",
            61: "Rain: Slight intensity",
            63: "Rain: Moderate intensity",
            65: "Rain: Heavy intensity",
            66: "Freezing Rain: Light intensity",
            67: "Freezing Rain: Heavy intensity",
            71: "Snow fall: Slight intensity",
            73: "Snow fall: Moderate intensity",
            75: "Snow fall: Heavy intensity",
            77: "Snow grains",
            80: "Rain showers: Slight intensity",
            81: "Rain showers: Moderate intensity",
            82: "Rain showers: Violent intensity",
            85: "Snow showers: Slight intensity",
            86: "Snow showers: Heavy intensity",
            95: "Thunderstorm: Slight or moderate",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }

        weather_description = weather_interpretations.get(weather_code, "Unknown weather code")

        summary = f"The current weather in Split, Croatia is: {temperature}°C and {weather_description}."
        print(summary)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
    except (KeyError, TypeError) as e:
        print(f"Error parsing weather data: {e}")

if __name__ == '__main__':
    get_weather_split()
