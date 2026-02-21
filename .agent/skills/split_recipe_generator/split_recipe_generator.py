import json
import random

def generate_split_recipe():
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

    num_ingredients = random.randint(3, 6) #3-6 ingredients
    selected_ingredients = random.sample(ingredients, num_ingredients)

    recipe_name_parts = [ing['name'].split(' ')[0] for ing in selected_ingredients[:3]]  # First 3 ingredients
    recipe_name = 'Split-Style ' + ' and '.join(recipe_name_parts) + ' Dish'

    instructions = [
        f"Prepare the {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] in ['vegetable', 'protein']])}.",
        f"Sauté the {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] == 'vegetable'])} with garlic and olive oil.",
        f"Add the {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] == 'protein'])} and cook until done.",
        f"Deglaze with a splash of {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] == 'beverage'])} (if included).",
        f"Season with salt, pepper, and {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] == 'herb'])}.",
        f"Serve with {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] in ['grain', 'dairy']])} and a squeeze of {', '.join([ing['name'] for ing in selected_ingredients if ing['type'] == 'fruit'])}."
    ]

    random.shuffle(instructions)
    instructions = [s for s in instructions if not s.startswith('Serve with Serve with')]

    recipe = {
        "name": recipe_name,
        "ingredients": [ing['name'] for ing in selected_ingredients],
        "instructions": instructions
    }

    recipe_summary = f"## {recipe['name']}\n\n**Ingredients:**\n{chr(10).join([f'- {ing}' for ing in recipe['ingredients']])}\n\n**Instructions:**\n{chr(10).join([f'{i+1}. {step}' for i, step in enumerate(recipe['instructions'])])}"

    return recipe_summary


if __name__ == '__main__':
    recipe = generate_split_recipe()
    print(recipe)
