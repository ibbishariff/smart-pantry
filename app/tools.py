import re
import os
import json
import uuid
import base64
import urllib.request
import urllib.parse
from google import genai
from google.genai import types
from google.cloud import firestore, storage
from google.adk.tools import ToolContext


# Hardcoded project ID and Cloud Storage bucket as required
PROJECT_ID = "qwiklabs-gcp-02-6f91fdc030de"
BUCKET_NAME = "smart-pantry-images-qwiklabs-gcp-02-6f91fdc030de"

def get_firestore_client():
    return firestore.Client(project=PROJECT_ID)

def search_recipes(cuisine: str = "", category: str = "", dietary_tag: str = "") -> list[dict]:
    """Search for recipes in the local Firestore database based on filters.

    Args:
        cuisine: Optional filter by cuisine (e.g. 'American', 'Mediterranean', 'Italian').
        category: Optional filter by meal category (e.g. 'Breakfast', 'Lunch', 'Dinner').
        dietary_tag: Optional filter by dietary tag (e.g. 'vegetarian', 'vegan', 'gluten-free').

    Returns:
        List of recipe dictionaries matching the criteria.
    """
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()
    
    results = []
    for doc in docs:
        data = doc.to_dict()
        if cuisine and data.get("cuisine", "").lower() != cuisine.lower():
            continue
        if category and data.get("category", "").lower() != category.lower():
            continue
        if dietary_tag:
            tags = [t.lower() for t in data.get("dietary_tags", [])]
            if dietary_tag.lower() not in tags:
                continue
        results.append(data)
    
    return results

def get_recipe_details(recipe_id: str) -> dict:
    """Get complete details for a specific recipe by ID.

    Args:
        recipe_id: The unique ID of the recipe (e.g. 'recipe-001').

    Returns:
        A dictionary containing recipe details or an error message.
    """
    db = get_firestore_client()
    doc = db.collection("recipes").document(recipe_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Recipe with ID '{recipe_id}' not found."}

def add_recipe(
    title: str,
    category: str,
    cuisine: str,
    ingredients: list[str],
    instructions: str,
    prep_time_mins: int = 15,
    calories: int = 400,
    dietary_tags: list[str] = None
) -> dict:
    """Add a new recipe to the Firestore database.

    Args:
        title: Title of the recipe.
        category: Meal category (e.g. 'Breakfast', 'Lunch', 'Dinner').
        cuisine: Cuisine type (e.g. 'American', 'Italian').
        ingredients: List of ingredient strings with amounts.
        instructions: Preparation instructions.
        prep_time_mins: Preparation time in minutes.
        calories: Calorie count per serving.
        dietary_tags: Optional list of dietary tags (e.g. ['vegetarian', 'gluten-free']).

    Returns:
        A status dictionary confirming recipe creation with the assigned recipe_id.
    """
    if dietary_tags is None:
        dietary_tags = []
        
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    
    docs = list(recipes_ref.stream())
    new_id = f"recipe-{len(docs) + 1:03d}"
    
    recipe_data = {
        "id": new_id,
        "title": title,
        "category": category,
        "cuisine": cuisine,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time_mins": prep_time_mins,
        "calories": calories,
        "dietary_tags": dietary_tags,
    }
    
    recipes_ref.document(new_id).set(recipe_data)
    return {"status": "success", "message": f"Recipe '{title}' added successfully.", "recipe": recipe_data}

def manage_pantry_inventory(action: str, item_name: str = "", quantity: str = "") -> dict:
    """Manage the pantry inventory stored in Firestore.

    Args:
        action: The inventory action to perform: 'list', 'add', or 'remove'.
        item_name: Name of the pantry item (e.g., 'Flour', 'Olive Oil', 'Spinach').
        quantity: Quantity or amount description (e.g., '2 lbs', '1 bottle').

    Returns:
        A dictionary containing action status, message, and current pantry inventory items.
    """
    db = get_firestore_client()
    pantry_ref = db.collection("pantry_items")
    action_clean = action.lower().strip()

    if action_clean == "add":
        if not item_name:
            return {"status": "error", "message": "item_name is required when adding an item."}
        doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', item_name.lower())
        pantry_ref.document(doc_id).set({
            "item_name": item_name,
            "quantity": quantity or "1 unit"
        })
        msg = f"Added '{item_name}' ({quantity or '1 unit'}) to pantry."
    elif action_clean == "remove":
        if not item_name:
            return {"status": "error", "message": "item_name is required when removing an item."}
        doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', item_name.lower())
        pantry_ref.document(doc_id).delete()
        msg = f"Removed '{item_name}' from pantry."
    else:
        msg = "Retrieved current pantry inventory."

    docs = pantry_ref.stream()
    pantry_list = [doc.to_dict() for doc in docs]
    return {
        "status": "success",
        "message": msg,
        "pantry_items": pantry_list
    }

async def generate_dish_photo(
    recipe_title: str,
    dish_description: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a photo of a recipe dish using gemini-3.1-flash-lite-image in global location, save as an artifact, and upload to public Cloud Storage.

    Args:
        recipe_title: Title or name of the dish (e.g. 'Berry Smoothie Bowl', 'Mushroom Risotto').
        dish_description: Optional description of visual presentation or ingredients.
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        A dictionary containing status, recipe_title, and public image_url.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global"
        )
        prompt = f"A appetizing, professional culinary food photograph of {recipe_title}."
        if dish_description:
            prompt += f" {dish_description}"

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_part = response.candidates[0].content.parts[0]
        image_bytes = image_part.inline_data.data
        mime_type = image_part.inline_data.mime_type or "image/jpeg"
        ext = "png" if "png" in mime_type.lower() else "jpg"

        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', recipe_title.lower())
        filename = f"{slug}.{ext}"

        # 1. Save artifact with tool_context.save_artifact if tool_context is provided
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload same image bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_path = f"dishes/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"
        return {
            "status": "success",
            "recipe_title": recipe_title,
            "image_url": public_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate dish photo: {str(e)}"
        }

def generate_dish_image(recipe_title: str, dish_description: str = "") -> dict:
    """Generate a photo of a recipe dish using Imagen/Gemini and store it in Cloud Storage.

    Args:
        recipe_title: Title of the dish (e.g., 'Avocado Toast', 'Chickpea Salad').
        dish_description: Optional extra details to describe visual styling or presentation.

    Returns:
        A dictionary containing status, recipe_title, and public image_url.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="us-central1"
        )
        prompt = f"A appetizing, professional culinary food photograph of {recipe_title}."
        if dish_description:
            prompt += f" {dish_description}"

        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_part = response.candidates[0].content.parts[0]
        image_bytes = image_part.inline_data.data

        # Save to GCS
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', recipe_title.lower())
        blob_path = f"dishes/{slug}.png"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type="image/png")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"
        return {
            "status": "success",
            "recipe_title": recipe_title,
            "image_url": public_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate dish image: {str(e)}"
        }

def search_external_recipes(query: str) -> list[dict]:
    """Search for global meal recipes and preparation instructions from the free public TheMealDB API.

    Args:
        query: Search term for recipe name or main ingredient (e.g. 'pasta', 'tacos', 'curry').

    Returns:
        A list of matching recipe dictionaries with title, category, cuisine_area, instructions, ingredients, and thumbnail.
    """
    if not query:
        return []

    api_key = os.getenv("THEMEALDB_API_KEY", "1")
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={encoded_query}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            meals = data.get("meals")
            if not meals:
                return []

            results = []
            for meal in meals[:5]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    measure = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"{measure.strip() if measure else ''} {ing.strip()}".strip())

                results.append({
                    "id": meal.get("idMeal"),
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "cuisine_area": meal.get("strArea"),
                    "instructions": meal.get("strInstructions", "")[:300] + "...",
                    "ingredients": ingredients,
                    "image_url": meal.get("strMealThumb"),
                    "source": "TheMealDB API"
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to fetch external recipes from TheMealDB: {str(e)}"}]

def geocode_address(address: str) -> dict:
    """Turn a physical address or city name into geographic latitude and longitude coordinates using Google Geocoding API.

    Args:
        address: The address, city, or landmark string to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing formatted_address, latitude, and longitude.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}
    if not address:
        return {"error": "address parameter is required."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                loc = result["geometry"]["location"]
                return {
                    "formatted_address": result.get("formatted_address"),
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng"),
                }
            return {"error": f"Geocoding failed: {data.get('status', 'No results found')}"}
    except Exception as e:
        return {"error": f"Failed to call Geocoding API: {str(e)}"}

def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "grocery_store",
    radius_meters: float = 2000.0
) -> list[dict]:
    """Find nearby places (such as grocery stores or supermarkets) around coordinates using Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'grocery_store', 'supermarket', 'bakery').
        radius_meters: Search radius in meters (default 2000.0).

    Returns:
        A list of nearby places with name, address, and location coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }
    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                },
                "radius": float(radius_meters)
            }
        }
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            places = data.get("places", [])
            results = []
            for place in places:
                display_name = place.get("displayName", {}).get("text", "")
                formatted_address = place.get("formattedAddress", "")
                loc = place.get("location", {})
                results.append({
                    "name": display_name,
                    "address": formatted_address,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude")
                    }
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to call Places API: {str(e)} me"}]

async def generate_dish_video(
    recipe_title: str,
    video_prompt: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a short video for a dish or pantry item using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video with tool_context.save_artifact so it shows up in the Playground's Artifacts panel,
    and uploads the video bytes to the public Cloud Storage bucket, returning its public https URL.

    Args:
        recipe_title: Title or item name in the pantry/recipe domain (e.g. 'Sizzling Pasta', 'Vegetable Soup').
        video_prompt: Optional extra details describing the motion, video styling, or cooking action.
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        A dictionary containing status, recipe_title, and public video_url.
    """
    try:
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global"
        )
        prompt = f"A short video showing {recipe_title}."
        if video_prompt:
            prompt += f" {video_prompt}"

        response = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_modalities=["video"]
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(response, "output_video") and response.output_video:
            out_v = response.output_video
            if hasattr(out_v, "mime_type") and out_v.mime_type:
                mime_type = out_v.mime_type
            if hasattr(out_v, "data") and out_v.data:
                if isinstance(out_v.data, str):
                    video_bytes = base64.b64decode(out_v.data)
                else:
                    video_bytes = out_v.data
            elif hasattr(out_v, "uri") and out_v.uri:
                gcs_uri = out_v.uri
                if gcs_uri.startswith("gs://"):
                    parts = gcs_uri[5:].split("/", 1)
                    if len(parts) == 2:
                        src_bucket_name, src_blob_name = parts
                        st_client = storage.Client(project=PROJECT_ID)
                        src_bucket = st_client.bucket(src_bucket_name)
                        blob = src_bucket.blob(src_blob_name)
                        video_bytes = blob.download_as_bytes()

        if not video_bytes:
            return {
                "status": "error",
                "message": "gemini-omni-flash-preview did not return video bytes or data."
            }

        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', recipe_title.lower())
        filename = f"{slug}_{uuid.uuid4().hex[:6]}.mp4"

        # (1) Save video as artifact with tool_context.save_artifact if tool_context is provided
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload same video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_path = f"videos/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"
        return {
            "status": "success",
            "recipe_title": recipe_title,
            "video_url": public_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate dish video: {str(e)}"
        }

