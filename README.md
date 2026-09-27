# Smart Pantry Agent

Smart Pantry is an AI-powered personal culinary and recipe assistant built with Google's Agent Development Kit (ADK) and deployed on Google Cloud Platform. It manages pantry inventory, searches and stores recipes, tracks user dietary preferences and allergies across sessions, generates dish photography and cooking videos, and locates nearby grocery markets.

---

## Capabilities & Implemented Tools

### 1. Recipe Management & Local Database
- **Recipe Search & Retrieval**: Search local recipes in Firestore by cuisine, meal category, or dietary tag (`search_recipes`, `get_recipe_details`).
- **Recipe Creation**: Add new custom recipes with ingredients, preparation instructions, time, and calorie counts (`add_recipe`).
- **External Recipe Discovery**: Search global recipes from TheMealDB API (`search_external_recipes`).

### 2. Pantry Inventory Tracking
- **Inventory Control**: Add, remove, and list pantry items and quantities stored in Google Cloud Firestore (`manage_pantry_inventory`).

### 3. AI Media Generation & Artifacts
- **Dish Photography**: Generate culinary food photography using `gemini-3.1-flash-lite-image` and `gemini-2.5-flash-image`. Photos are saved as Agent Playground artifacts and uploaded to a public Google Cloud Storage bucket (`generate_dish_photo`, `generate_dish_image`).
- **Cooking Video Generation**: Generate short cooking videos for dishes using Google's Omni model (`gemini-omni-flash-preview`) in the `global` region via the Interactions API. Videos are saved as Agent Playground artifacts via `tool_context.save_artifact` and uploaded to public Cloud Storage (`generate_dish_video`).

### 4. Location & Grocery Services
- **Address Geocoding**: Convert physical addresses into latitude/longitude coordinates using the Google Maps Geocoding API (`geocode_address`).
- **Nearby Market Search**: Find nearby grocery stores and supermarkets based on location coordinates using the Google Places API (`find_nearby_places`).

### 5. Memory & Preference Enforcement
- **Vertex AI Memory Bank**: Persistent session memory tracking user food allergies, dietary restrictions, and cooking preferences across turns (`VertexAiMemoryBankService`, `PreloadMemoryTool`).

### 6. Interactive UI & Frontend
- **A2UI Schema Manager (v0.8)**: Generates structured, client-rendered A2UI cards for recipes and inventory listings.
- **FastAPI Web Proxy & Chat UI**: A lightweight web interface built with FastAPI and `a2a-sdk` providing a responsive chat experience with example prompts and inline A2UI rendering.

---

## Google Cloud Services Integrated

- **Agent Engine / Reasoning Engine**: Hosting runtime for the ADK agent.
- **Vertex AI Memory Bank**: Multi-turn conversation and preference persistence.
- **Google Cloud Firestore**: NoSQL document storage for recipes and pantry inventory.
- **Google Cloud Storage**: Public bucket hosting for AI-generated dish images and cooking videos.
- **Vertex AI Gemini Models**:
  - `gemini-flash-latest` (Core agent reasoning)
  - `gemini-3.1-flash-lite-image` & `gemini-2.5-flash-image` (Dish photo generation)
  - `gemini-omni-flash-preview` (Short video generation)
- **Google Maps & Places APIs**: Address geocoding and nearby store discovery.

---

## Project Structure

```
.
├── app/
│   ├── agent.py          # Core ADK Agent, A2UI setup, and Memory Bank callbacks
│   ├── tools.py          # Firestore, Cloud Storage, Gemini Media, Maps, and MealDB tools
│   ├── a2ui_utils.py     # A2UI callback and JSON parsing utilities
│   └── fast_api_app.py   # ADK FastAPI application entrypoint
├── frontend/
│   ├── main.py           # FastAPI web proxy using a2a-sdk
│   ├── static/index.html # Chat UI interface with A2UI renderer
│   ├── Dockerfile        # Container specification for Cloud Run
│   └── requirements.txt  # Frontend proxy dependencies
└── agents-cli-manifest.yaml # Agent deployment manifest
```

---

## Local Setup & Development

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`)
- Configured GCP Project with Firestore, Cloud Storage, Vertex AI, Maps, and Places APIs enabled

### Installation

1. **Clone the repository and navigate to the project directory:**
   ```bash
   cd smart-pantry
   ```

2. **Set up a virtual environment and install backend dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/venv/activate
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies:**
   ```bash
   pip install -r frontend/requirements.txt
   ```

### Running Locally

1. **Set Environment Variables:**
   ```bash
   export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
   export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<RESOURCE_ID>"
   export AGENT_DIRECTORY="app"
   export GOOGLE_MAPS_API_KEY="<YOUR_MAPS_API_KEY>"
   ```

2. **Start the Frontend Web Proxy:**
   ```bash
   cd frontend
   python3 main.py
   ```

3. **Access the Application:**
   Open a web browser and navigate to the port output by the application server (default port `8080`).
