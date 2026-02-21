import json
import random
import ssl
import urllib.request

def generate_split_recipe():
    """Generates a random Mediterranean recipe based on Split local ingredients."""

    # Hardcoded list of Split/Dalmatian recipes and ingredients. Using AI's knowledge for this.
    recipes = {
        "Pašticada (Dalmatian Beef Stew)": {
            "ingredients": ["Beef (usually chuck or round)", "Red Wine", "Dried Plums", "Tomato Paste", "Onions", "Carrots", "Celery", "Garlic", "Olive Oil", "Bay Leaves", "Cloves", "Nutmeg", "Prosciutto (optional)"],
            "instructions": "A slow-cooked beef stew marinated in vinegar and spices, then braised with red wine and dried plums."
        },
        "Crni Rižot (Black Risotto)": {
            "ingredients": ["Squid or Cuttlefish", "Arborio Rice", "Squid Ink", "Onion", "Garlic", "Olive Oil", "White Wine", "Fish Stock", "Parsley"],
            "instructions": "Risotto colored black with squid ink, made with squid or cuttlefish."
        },
        "Gregada (Fish Stew)": {
            "ingredients": ["White Fish (like sea bass or grouper)", "Potatoes", "Onion", "Garlic", "Olive Oil", "White Wine", "Parsley", "Bay Leaf"],
            "instructions": "Simple fish stew with potatoes, onions, garlic, and white wine."
        },
        "Soparnik (Swiss Chard Pie)": {
            "ingredients": ["Swiss Chard", "Onion", "Garlic", "Olive Oil", "Thin Dough (flour, water, salt)"],
            "instructions": "Thin, savory pie filled with Swiss chard, onion, and garlic."
        },
         "Fritule (Fried Doughnuts)": {
            "ingredients": ["Flour", "Yogurt", "Eggs", "Rum or Brandy", "Lemon Zest", "Raisins (optional)", "Powdered Sugar"],
            "instructions": "Small, sweet fried doughnuts flavored with citrus zest and rum."
        }

    }

    recipe_name = random.choice(list(recipes.keys()))
    recipe = recipes[recipe_name]

    return {
        "recipe_name": recipe_name,
        "ingredients": recipe["ingredients"],
        "instructions": recipe["instructions"]
    }




def main():
    recipe = generate_split_recipe()
    print(json.dumps(recipe, indent=4))

if __name__ == "__main__":
    main()
