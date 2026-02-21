import os
import sys
import json
import requests
from urllib.parse import quote_plus


def search_the_web(query, num_results=5):
    """Searches the web using DuckDuckGo and returns a JSON list of results."""
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&pretty=1&num_results={num_results}"
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        results = []
        for result in data['RelatedTopics']:
            if 'FirstURL' in result and 'Text' in result:
                results.append({'title': result['Text'], 'url': result['FirstURL']})
        return json.dumps(results, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({'error': f'Request failed: {str(e)}'}, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Failed to decode JSON response: {str(e)}'}, indent=2)
    except Exception as e:
        return json.dumps({'error': f'An unexpected error occurred: {str(e)}'}, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Missing search query.  Please provide a query as a command line argument.'}, indent=2))
        sys.exit(1)

    query = sys.argv[1]
    num_results = 5 # You can potentially add number of results as an argument if needed.

    search_results = search_the_web(query, num_results)
    print(search_results)
