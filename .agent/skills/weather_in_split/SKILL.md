---
name: Weather in Split
description: Fetches the current weather conditions in Split, Croatia, including temperature and wind speed, using the open-meteo API.
author: Satele Shan's Brain
version: 0.1.0

input_parameters:
  None

output_parameters:
  weather_summary: A string containing the current weather summary for Split.

instructions:
  1.  The skill uses the open-meteo API to fetch weather data for Split, Croatia.
  2.  It extracts the current temperature and wind speed.
  3.  The skill returns a summary string with the weather information.

example:
  ```text
  Current weather in Split, Croatia:
  Temperature: 25.5°C
  Wind Speed: 3.2 m/s
  ```
---
