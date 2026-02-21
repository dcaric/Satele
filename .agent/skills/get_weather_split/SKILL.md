---
name: Get Weather in Split
description: Fetches the current weather conditions in Split, Croatia, and provides a summary including temperature and a description of the weather.
author: Satele's Brain
version: 1.0

input_parameters:
  None

output_parameters:
  weather_summary: The summary of the weather in Split, Croatia.

dependencies:
  - requests

installation_instructions: |
  1. Save the `get_weather_split.py` file to your agent's skills directory:
     `.agent/skills/get_weather_split/get_weather_split.py`
  2. Ensure the `requests` library is installed: `pip install requests`

example_usage: |
  ```python
  from .agent.skills.get_weather_split.get_weather_split import get_weather_split # Assuming you've saved the skill as suggested
  get_weather_split()
  # Expected output: A string describing the current weather in Split, Croatia.
  ```

file_structure:
  - .agent/skills/get_weather_split/get_weather_split.py
---
