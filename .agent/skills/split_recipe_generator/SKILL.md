# Generate Split Recipe

## Description

This skill generates a random Mediterranean recipe based on locally sourced ingredients from Split, Croatia. The recipes are based on typical Dalmatian cuisine.

## Usage

Simply invoke the skill. It will return a JSON object containing the recipe name, a list of ingredients, and brief instructions.

## Output Example

```json
{
    "recipe_name": "Pašticada (Dalmatian Beef Stew)",
    "ingredients": [
        "Beef (usually chuck or round)",
        "Red Wine",
        "Dried Plums",
        "Tomato Paste",
        "Onions",
        "Carrots",
        "Celery",
        "Garlic",
        "Olive Oil",
        "Bay Leaves",
        "Cloves",
        "Nutmeg",
        "Prosciutto (optional)"
    ],
    "instructions": "A slow-cooked beef stew marinated in vinegar and spices, then braised with red wine and dried plums."
}
```

## Tools

*   `random`: For selecting a random recipe.
*   `json`: For formatting the output as JSON.
*   `ssl` and `urllib`: Not used for external requests, but included as placeholders in case future versions require data from public, keyless URLs.
