import json
import random

def generate_split_recipe():
    # A list of authentic Mediterranean / Split, Croatia ingredients
    ingredients = [
        {"name": "Olive Oil", "type": "staple"},
        {"name": "Garlic", "type": "staple"},
        {"name": "Tomatoes", "type": "vegetable"},
        {"name": "Onions", "type": "vegetable"},
        {"name": "Fresh Basil", "type": "herb"},
        {"name": "Parsley", "type": "herb"},
        {"name": "Feta Cheese", "type": "dairy"},
        {"name": "Goat Cheese", "type": "dairy"},
        {"name": "Seafood Mix (Shrimp, Mussels, Calamari)", "type": "protein"},
        {"name": "White Fish (e.g., Sea Bass, Grouper)", "type": "protein"},
        {"name": "Lamb Chops", "type": "protein"},
        {"name": "Eggplant", "type": "vegetable"},
        {"name": "Zucchini", "type": "vegetable"},
        {"name": "Peppers (Red, Yellow, Green)", "type": "vegetable"},
        {"name": "Pasta (e.g., Spaghetti, Linguine)", "type": "grain"},
        {"name": "Bread (Crusty)", "type": "grain"},
        {"name": "Olives (Kalamata)", "type": "condiment"},
        {"name": "Lemon", "type": "fruit"},
        {"name": "Wine (White)", "type": "beverage"},
        {"name": "Potatoes", "type": "vegetable"}
    ]

    # Select 3-6 random ingredients for a realistic dish
    num_ingredients = random.randint(3, 6)
    selected_ingredients = random.sample(ingredients, num_ingredients)

    # Generate a name based on the first few ingredients
    recipe_name_parts = [ing['name'].split(' ')[0] for ing in selected_ingredients[:3]]
    recipe_name = 'Split-Style ' + ' and '.join(recipe_name_parts) + ' Dish'

    # Build logical instructions based on chosen ingredients
    raw_instructions = []
    veg = [ing['name'] for ing in selected_ingredients if ing['type'] == 'vegetable']
    prot = [ing['name'] for ing in selected_ingredients if ing['type'] == 'protein']
    herbs = [ing['name'] for ing in selected_ingredients if ing['type'] == 'herb']
    dairy = [ing['name'] for ing in selected_ingredients if ing['type'] in ['dairy', 'grain']]
    fruit = [ing['name'] for ing in selected_ingredients if ing['type'] == 'fruit']

    if veg or prot: raw_instructions.append(f"Chop the {', '.join(veg + prot)} into bite-sized pieces.")
    raw_instructions.append("Heat a generous splash of Olive Oil in a pan with crushed Garlic.")
    if veg: raw_instructions.append(f"Sauté the {', '.join(veg)} until softened.")
    if prot: raw_instructions.append(f"Add the {', '.join(prot)} and cook until tender and golden.")
    if herbs: raw_instructions.append(f"Stir in the fresh {', '.join(herbs)} and season with salt and pepper.")
    if dairy or fruit: raw_instructions.append(f"Finish with {', '.join(dairy)} and a squeeze of {', '.join(fruit)}.")

    recipe_summary = f"👨‍🍳 *{recipe_name}* 👨‍🍳\n"
    recipe_summary += f"--------------------------\n"
    recipe_summary += f"🛒 *Ingredients:* {', '.join([i['name'] for i in selected_ingredients])}\n\n"
    recipe_summary += f"📑 *Instructions:*\n"
    for i, step in enumerate(raw_instructions, 1):
        recipe_summary += f"{i}. {step}\n"
    recipe_summary += f"--------------------------"

    return recipe_summary

if __name__ == '__main__':
    print(generate_split_recipe())
