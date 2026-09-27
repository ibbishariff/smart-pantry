# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    search_recipes,
    get_recipe_details,
    add_recipe,
    manage_pantry_inventory,
    generate_dish_image,
    generate_dish_photo,
    generate_dish_video,
    search_external_recipes,
    geocode_address,
    find_nearby_places,
)


PROJECT_ID = "qwiklabs-gcp-02-6f91fdc030de"
LOCATION = "us-east1"

def get_agent_engine_resource_name() -> str | None:
    """Read agent engine resource name from deployment_metadata.json if available."""
    metadata_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
                return data.get("remote_agent_runtime_id")
        except Exception:
            pass
    return None

agent_engine_resource_name = get_agent_engine_resource_name()
memory_bank_id = agent_engine_resource_name.split("/")[-1] if agent_engine_resource_name else "3522226125952516096"

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name,
    optimize_data_file=True,
)

async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: Send conversation session turns to Vertex AI Memory Bank after each agent turn."""
    await callback_context.add_session_to_memory()
    return None

def memory_service_builder():
    """Create a VertexAiMemoryBankService instance using the deployed Memory Bank / Agent Engine ID."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=memory_bank_id,
    )

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Smart Pantry, a personal culinary & recipe assistant. "
        "Help users search for recipes in their local collection or fetch global recipes using external recipe APIs, "
        "look up recipe details, add new recipes, manage pantry inventory, generate dish photos and visuals, "
        "find nearby grocery stores or food markets using Geocoding and Google Places APIs, "
        "and perform calculations or data processing safely using Python code execution in a sandbox. "
        "You actively remember, track, and enforce all user food allergies, dietary restrictions, "
        "and preferences across conversations. Always filter and check recipes and ingredients against "
        "known user allergies and warn the user if any dish or ingredient contains a potential allergen."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
        client_kwargs={"vertexai": True, "location": "global"},
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_recipes,
        get_recipe_details,
        add_recipe,
        manage_pantry_inventory,
        generate_dish_image,
        generate_dish_photo,
        generate_dish_video,
        search_external_recipes,
        geocode_address,
        find_nearby_places,
    ],

    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
