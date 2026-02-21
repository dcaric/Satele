import requests
import json

def get_weather_in_split():
    """Fetches the current weather in Split, Croatia and prints a summary.
    """
    try:
        api_key = "YOUR_API_KEY" # Replace with a real API key or environment variable
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        city_name = "Split"
        country_code = "HR"
        units = "metric"  # For Celsius
        lang = "en"  # For English description

        url = f"{base_url}?q={city_name},{country_code}&appid={api_key}&units={units}&lang={lang}"

        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        if data['cod'] == 200:
            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']
            
            summary = f"The current weather in Split, Croatia is {weather_description} with a temperature of {temperature}°C, humidity of {humidity}%, and wind speed of {wind_speed} m/s."
            print(summary)
        else:
            print(f"Error: Could not retrieve weather data.  Response code: {data['cod']}")

    except requests.exceptions.RequestException as e:
        print(f"Error: Network issue or API error: {e}")
    except KeyError as e:
        print(f"Error: Malformed weather API response: Missing key {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    get_weather_in_split()
