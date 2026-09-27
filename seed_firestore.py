from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-6f91fdc030de"

def seed():
    db = firestore.Client(project=PROJECT_ID)
    recipes_ref = db.collection("recipes")
    
    initial_recipes = [
        {
            "id": "recipe-001",
            "title": "Avocado & Tomato Toast",
            "category": "Breakfast",
            "cuisine": "American",
            "ingredients": ["2 slices sourdough bread", "1 ripe avocado", "1 ripe tomato", "olive oil", "salt", "black pepper"],
            "instructions": "Toast sourdough slices. Mash avocado with salt and pepper. Spread on toast and top with sliced tomatoes and a drizzle of olive oil.",
            "prep_time_mins": 10,
            "calories": 320,
            "dietary_tags": ["vegetarian", "vegan", "quick"]
        },
        {
            "id": "recipe-002",
            "title": "Mediterranean Chickpea Salad",
            "category": "Lunch",
            "cuisine": "Mediterranean",
            "ingredients": ["1 can chickpeas (drained)", "1 cucumber (diced)", "1 red bell pepper (diced)", "1/2 cup feta cheese", "lemon juice", "olive oil"],
            "instructions": "Combine chickpeas, cucumber, red bell pepper, and feta in a large bowl. Toss with lemon juice, olive oil, salt, and pepper.",
            "prep_time_mins": 15,
            "calories": 410,
            "dietary_tags": ["vegetarian", "gluten-free", "healthy"]
        },
        {
            "id": "recipe-003",
            "title": "Creamy Garlic Mushroom Pasta",
            "category": "Dinner",
            "cuisine": "Italian",
            "ingredients": ["200g fettuccine", "250g cremini mushrooms", "3 cloves garlic (minced)", "1/2 cup heavy cream", "1/4 cup parmesan cheese"],
            "instructions": "Boil pasta. Saute sliced mushrooms and garlic in butter. Add heavy cream and simmer until thickened. Stir in cooked pasta and parmesan.",
            "prep_time_mins": 25,
            "calories": 650,
            "dietary_tags": ["vegetarian"]
        }
    ]
    
    for r in initial_recipes:
        doc_id = r["id"]
        recipes_ref.document(doc_id).set(r)
        print(f"Seeded recipe: {r['title']} ({doc_id})")

if __name__ == "__main__":
    seed()
