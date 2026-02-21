import urllib.request
import urllib.parse
import ssl
import json
import re


def recipe_search(ingredients):
    """Searches online for a recipe using the given ingredients.

    Args:
        ingredients: A list of food ingredients.

    Returns:
        A JSON string containing the recipe title and ingredients list, or an error message if no recipe is found.
    """

    search_query = ' '.join(ingredients) + ' recipe'

    try:
        # Bypass SSL certificate verification (use with caution!)
        context = ssl._create_unverified_context()
        url = 'https://www.google.com/search?q=' + urllib.parse.quote_plus(search_query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})  # Spoof User-Agent
        with urllib.request.urlopen(req, context=context) as response:
            html_content = response.read().decode('utf-8')

        # Basic parsing using regular expressions.  This is fragile but avoids API key issues
        title_match = re.search(r'<title>(.*?)</title>', html_content)
        if title_match:
            title = title_match.group(1).split(" - Google Search")[0]
        else:
            title = "Recipe Title not found. This suggests the scraper failed."

        # Attempt to find ingredients on the same page, assuming they might be listed near the title
        ingredients_section_match = re.search(r'(Ingredients|You’ll need):(.*?)Instructions', html_content, re.DOTALL | re.IGNORECASE)

        if ingredients_section_match:
             ingredients_list = ingredients_section_match.group(2).strip()

             # Clean up extra HTML tags
             ingredients_list = re.sub('<.*?>', '', ingredients_list) # Remove any HTML tags within the ingredients
             ingredients_list = re.sub(r'\n+', '\n', ingredients_list).strip() # Remove excessive newlines

        else:
            ingredients_list = "Ingredients list not found on the page. Direct extraction failed."

        recipe_data = {"recipe_title": title, "recipe_ingredients": ingredients_list}
        return json.dumps(recipe_data)

    except Exception as e:
        return json.dumps({'error': f'An error occurred during the search: {str(e)}'})


if __name__ == '__main__':
    ingredients = ['chicken', 'rice', 'soy sauce', 'ginger']
    result = recipe_search(ingredients)
    print(result)
