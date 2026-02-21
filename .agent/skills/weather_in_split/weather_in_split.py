import urllib.request
import json
import datetime


def get_weather_in_split():
    try:
        api_url = "https://api.open-meteo.com/v1/forecast?latitude=43.5081&longitude=16.4402&current=temperature_2m,wind_speed_10m&hourly=temperature_2m"
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read().decode())

        current_temperature = data['current']['temperature_2m']
        current_wind_speed = data['current']['wind_speed_10m']

        now = datetime.datetime.now()
        current_hour = now.hour

        hourly_temperatures = data['hourly']['temperature_2m']
        hourly_times = data['hourly']['time']

        # Find the index of the current hour
        current_hour_index = next((i for i, time in enumerate(hourly_times) if datetime.datetime.fromisoformat(time).hour == current_hour), None)

        if current_hour_index is not None:
            current_hour_temperature = hourly_temperatures[current_hour_index]
        else:
            current_hour_temperature = "Temperature not found for the current hour."

        summary = f"Current weather in Split, Croatia:\n"
        summary += f"Temperature: {current_temperature}°C\n"
        summary += f"Wind Speed: {current_wind_speed} m/s\n"
        # summary += f"Temperature at {current_hour}:00: {current_hour_temperature}°C\n"

        return summary

    except Exception as e:
        return f"Error fetching weather data: {e}"


if __name__ == '__main__':
    weather_summary = get_weather_in_split()
    print(weather_summary)