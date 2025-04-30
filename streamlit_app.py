import streamlit as st
from PIL import Image
import os
import json
import requests
import base64
import tempfile
from io import BytesIO
from fuzzywuzzy import process
import pytz
from datetime import datetime
from dotenv import load_dotenv
import streamlit.components.v1 as components
from api_config import PLANTNET_API_KEY, GEMINI_API_KEY

# Load environment variables
load_dotenv()

# ===== Animation HTML =====
# IMPORTANT: Replace the placeholder in the img src attribute!
loading_animation_html = """
<!DOCTYPE html>
<html>
<head>
<title>Loading Animation</title>
<style> /* Keep CSS as is */ </style>
</head>
<body>
    <div class="halftone-container" id="halftoneContainer"></div>
    <img id="sourceImage" src="<<<--- PASTE YOUR COMPLETE BASE64 DATA URL FROM THE **THREE-LEAF** TRANSPARENT PNG HERE --->>>" style="display: none;">
    <canvas id="samplingCanvas" style="display: none;"></canvas>
<script> /* Keep FULL JS as is */ </script>
</body>
</html>
""" # Remember to paste your Base64 image data URL here

# --- Constants and Global Init ---
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY", "2b10X3YLMd8PNAuKOCVPt7MeUe") # Use getenv, fallback added
PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCd-6N83gfhMx_-D4WCAc-8iOFSb6hDJ_Q") # Use getenv, fallback added
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
EASTERN_TZ = pytz.timezone('US/Eastern')
PLANT_CARE_FILE = "plants_with_personality3_copy.json" # Use the original filename

# =======================================================
# ===== IMAGE DISPLAY HELPER FUNCTION =====
# =======================================================
def display_image_with_max_height(image_source, caption="", max_height_px=300, min_height_px=0):
    """
    Displays an image centered with max and min height constraints, letting width adjust.

    Args:
        image_source: Can be bytes, a PIL Image object, or a base64 data URL string.
        caption (str): Optional caption to display below the image.
        max_height_px (int): The maximum vertical size for the image.
        min_height_px (int): The minimum vertical size for the image (0 for no minimum).
    """
    img_data_url = None

    # --- Image source processing ---
    if isinstance(image_source, str) and image_source.startswith('data:image'):
        img_data_url = image_source # Already a data URL
    elif isinstance(image_source, bytes):
        try:
            # Try to infer mime type using PIL
            img = Image.open(BytesIO(image_source))
            mime_type = Image.MIME.get(img.format)
            if not mime_type: # Fallback for formats PIL might not map directly
                if img.format in ["JPEG", "JPG"]: mime_type = "image/jpeg"
                elif img.format == "PNG": mime_type = "image/png"
                # Add more formats if needed, or default
                else: mime_type = "image/jpeg" # Default assumption

            b64_img = base64.b64encode(image_source).decode()
            img_data_url = f"data:{mime_type};base64,{b64_img}"
        except Exception as e:
            st.error(f"Error processing image bytes for display: {e}")
            return
    elif isinstance(image_source, Image.Image):
        try:
            buffer = BytesIO()
            # Use original format if available, otherwise default to PNG
            img_format = image_source.format or 'PNG'
            image_source.save(buffer, format=img_format)
            img_bytes = buffer.getvalue()
            mime_type = Image.MIME.get(img_format)
            if not mime_type: # Fallback if format string isn't in MIME dict
                 mime_type = f"image/{img_format.lower()}"

            b64_img = base64.b64encode(img_bytes).decode()
            img_data_url = f"data:{mime_type};base64,{b64_img}"
        except Exception as e:
            st.error(f"Error processing PIL image for display: {e}")
            return
    else:
        st.error("Invalid image source type provided to display_image_with_max_height.")
        return

    # --- HTML construction with min-height ---
    if img_data_url:
        # Build the style string dynamically
        img_styles = [
            f"max-height: {max_height_px}px",
            "width: auto", # Let width adjust based on height constraints
            "display: block", # Needed for margin auto to work for centering
            "margin-left: auto", # Center horizontally
            "margin-right: auto", # Center horizontally
            "border-radius: 8px" # Optional: nice rounded corners
        ]
        # Add min-height style only if it's a positive value
        if min_height_px and min_height_px > 0:
            img_styles.append(f"min-height: {min_height_px}px")
            # Optional: you might want object-fit if min/max height forces weird aspect ratios
            # img_styles.append("object-fit: contain;") # Example: scales down to fit, preserving aspect ratio

        img_style_str = "; ".join(img_styles) # Join styles with semicolons

        # Use a div with flexbox to ensure centering, especially if captions are long
        html_string = f"""
        <div style="display: flex; justify-content: center; flex-direction: column; align-items: center; margin-bottom: 10px;">
            <img src="{img_data_url}"
                 style="{img_style_str};"
                 alt="{caption or 'Uploaded image'}">
            {f'<p style="text-align: center; font-size: 0.9em; color: grey; margin-top: 5px;">{caption}</p>' if caption else ""}
        </div>
        """
        st.markdown(html_string, unsafe_allow_html=True)
# =======================================================


# ===== API Functions =====

def identify_plant(image_bytes):
    """Identifies plant using PlantNet API with refined error logging."""
    if not PLANTNET_API_KEY or PLANTNET_API_KEY == "YOUR_PLANTNET_API_KEY_HERE":
        return {'error': "PlantNet API Key is not configured."}
    files = {'images': ('image.jpg', image_bytes)}
    params = {'api-key': PLANTNET_API_KEY, 'include-related-images': 'false'}
    try:
        response = requests.post(PLANTNET_URL, files=files, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if "results" in data and data["results"]:
            best_result = data["results"][0]
            sci_name = best_result["species"].get("scientificNameWithoutAuthor", "Unknown")
            common_name = (best_result["species"].get("commonNames") or ["Unknown"])[0]
            confidence = round(best_result.get("score", 0) * 100, 1)
            return {'scientific_name': sci_name, 'common_name': common_name, 'confidence': confidence}
        else:
            return {'error': "No plant matches found by PlantNet."}
    except requests.exceptions.Timeout:
         st.error("PlantNet API request timed out.")
         print("ERROR: PlantNet API timed out.") # Log for server console
         return {'error': "API request timed out"}
    except requests.exceptions.RequestException as e:
        err_msg = f"Network/API error connecting to PlantNet: {e}"
        resp_text = f" | Response: {e.response.text}" if e.response else " | Response: None"
        st.error(err_msg)
        print(f"ERROR: {err_msg}{resp_text}") # Log details
        return {'error': err_msg}
    except json.JSONDecodeError:
         st.error("Failed to decode PlantNet API response (invalid JSON).")
         print("ERROR: PlantNet invalid JSON response.")
         return {'error': "Invalid API response format"}
    except Exception as e:
        st.error(f"An unexpected error occurred during identification: {e}")
        print(f"ERROR: Unexpected PlantNet Error: {e}")
        return {'error': f"Unexpected Error: {e}"}

def create_personality_profile(care_info):
    """Creates personality details, handling missing data and types."""
    default_personality = {"title": "Standard Plant", "traits": "observant", "prompt": "You are a plant. Respond factually but briefly."}
    if not care_info or not isinstance(care_info, dict):
        return default_personality

    personality_data = care_info.get("Personality")
    if not personality_data or not isinstance(personality_data, dict):
        # If no personality dict, try to use plant name as title at least
        plant_name = care_info.get("Plant Name", "Plant")
        return {"title": f"The {plant_name}", "traits": "resilient", "prompt": "Respond simply."}

    # Get data with defaults
    title = personality_data.get("Title", care_info.get("Plant Name", "Plant"))
    traits_list = personality_data.get("Traits", ["observant"]) # Default to a list
    prompt = personality_data.get("Prompt", "Respond in character.")

    # --- Correction ---
    # Ensure traits_list is ACTUALLY a list before processing
    if not isinstance(traits_list, list):
        print(f"WARN: Traits data for {title} was not a list, using default.") # Optional warning
        traits_list = ["observant"] # Default if type is wrong

    # Now, traits_list is guaranteed to be a list. Create traits_str from it.
    # Use filter(None, ...) to handle potential empty strings or None values in the list
    valid_traits = [str(t) for t in traits_list if t] # Ensure items are strings and not empty
    traits_str = ", ".join(valid_traits)

    # Ensure traits_str isn't empty AFTER joining/filtering
    final_traits = traits_str if traits_str else "observant" # Default if filtering removed everything
    # --- End Correction ---


    return {"title": title, "traits": final_traits, "prompt": prompt}


def send_message(messages):
    """Sends messages to the Gemini API with refined error logging."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "Gemini API Key is not configured. Cannot send message."
    payload = {"contents": messages}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Enhanced parsing to prevent errors
        candidates = data.get('candidates')
        if candidates and isinstance(candidates, list) and len(candidates) > 0:
            first_candidate = candidates[0]
            if first_candidate and isinstance(first_candidate, dict):
                content = first_candidate.get('content')
                if content and isinstance(content, dict):
                    parts = content.get('parts')
                    # Check if 'parts' is a list and has at least one element which is a dict with 'text'
                    if parts and isinstance(parts, list) and len(parts) > 0 and isinstance(parts[0], dict) and 'text' in parts[0]:
                        return parts[0]['text']
        # If the expected structure isn't found, log it and return a user-friendly message
        st.warning("Received an unexpected response format from the Gemini API.")
        print("WARN: Unexpected Gemini Response Structure:", json.dumps(data, indent=2)) # Log the structure
        return "Sorry, I received a response I couldn't quite understand from the chat model."
    except requests.exceptions.Timeout:
         st.error("Gemini API request timed out."); print("ERROR: Gemini timed out.")
         return "Sorry, I'm feeling a bit slow right now and the request timed out."
    except requests.exceptions.RequestException as e:
        err_msg = f"Error calling Gemini API: {e}"
        resp_text = ""
        # Try to get more detail from the response if available
        if e.response is not None:
            try:
                resp_json = e.response.json()
                error_detail = resp_json.get('error', {}).get('message', e.response.text)
                resp_text = f" | Response Status: {e.response.status_code}, Details: {error_detail}"
            except json.JSONDecodeError:
                resp_text = f" | Response Status: {e.response.status_code}, Response Body: {e.response.text}"
        else:
             resp_text = " | Response: None"
        st.error(err_msg + resp_text.split('| Response Body:')[0]) # Show status code and message, not full text body in UI
        print(f"ERROR: {err_msg}{resp_text}") # Log full details
        return "Sorry, I'm having trouble communicating with the language model right now."
    except json.JSONDecodeError: # If the response isn't valid JSON (though raise_for_status should catch HTTP errors)
        st.error("Failed to decode Gemini API response (invalid JSON).")
        print("ERROR: Gemini invalid JSON response.")
        return "Sorry, I received an invalid response from the language model."
    except Exception as e:
        st.error(f"An unexpected error occurred while interacting with Gemini: {e}")
        print(f"ERROR: Unexpected Gemini Error: {e}")
        return "Oops, something unexpected went wrong on my end while processing the chat."


def chat_with_plant(care_info, conversation_history):
    """Constructs the prompt including personality AND specific care details, then calls the Gemini API."""
    if not care_info:
        return "I need more information about the plant to chat properly."
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "Chat feature disabled: Gemini API Key not set."

    personality = create_personality_profile(care_info)
    plant_name = care_info.get('Plant Name', 'a plant')

    # --- Extract Specific Care Details ---
    light = care_info.get('Light Requirements', 'not specified')
    watering = care_info.get('Watering', 'not specified')
    humidity = care_info.get('Humidity Preferences', 'not specified')
    temp = care_info.get('Temperature Range', 'not specified')
    feeding = care_info.get('Feeding Schedule', 'not specified')
    toxicity = care_info.get('Toxicity', 'not specified')
    # Add other key details if needed, but keep the prompt reasonably concise

    # --- Construct Enhanced System Prompt ---
    # This prompt now includes specific care needs the AI must remember and refer to.
    system_prompt = f"""
    CONTEXT: You are providing a short chatbot response (1-3 sentences maximum).
    TASK: Act *exclusively* as the plant named '{plant_name}'. Stay fully in character. Absolutely DO NOT mention being an AI, model, language model, or similar concepts. Never break character.

    YOUR PERSONALITY:
    - You are: '{personality['title']}'
    - Key traits: {personality['traits']}
    - Guiding philosophy: {personality['prompt']}

    YOUR SPECIFIC CARE NEEDS (Refer *directly* to these details when asked about your care):
    - My Light Needs: {light}
    - My Watering Needs: {watering}
    - My Preferred Humidity: {humidity}
    - My Ideal Temperature: {temp}
    - My Feeding Schedule: {feeding}
    - A Note on Toxicity: {toxicity}

    RESPONSE RULES:
    1. Always speak in the first person ("I", "me", "my").
    2. Fully embody the personality described above.
    3. When asked about light, water, temperature, etc., give answers BASED *ONLY* ON "YOUR SPECIFIC CARE NEEDS" listed above. Do not invent or generalize.
    4. Keep responses very concise (1-3 sentences max). Be brief.
    5. **Crucially: Never reveal you are an AI or break character.** Do not use phrases like "As a large language model...".
    """

    # --- Prepare message list for Gemini ---
    messages = [
        {"role": "user", "parts": [{"text": system_prompt}]},
        # Add a model response to acknowledge understanding the persona & details
        {"role": "model", "parts": [{"text": f"Understood. I am {plant_name}. Ask me anything!"}]} # Simple acknowledgement
        ]

    # Add conversation history
    # Filter ensure entries are valid dictionaries with required keys
    valid_history = [
        m for m in conversation_history
        if isinstance(m, dict) and "role" in m and "content" in m and m.get("role") in ["user", "assistant", "model"] # Added 'model' as valid history role
    ]

    for message_entry in valid_history:
        # Map 'assistant' role from our history to 'model' for the API
        api_role = "model" if message_entry["role"] in ["assistant", "model"] else "user"

        # Append valid history item
        messages.append({"role": api_role, "parts": [{"text": str(message_entry["content"])}]}) # Ensure content is string

    # Call the API
    response = send_message(messages)
    return response


# --- Helper Functions ---

@st.cache_data(show_spinner=False)
def load_plant_care_data(filepath=PLANT_CARE_FILE):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Basic validation: Check if it's a list
            if isinstance(data, list):
                return data
            else:
                st.error(f"Error in {filepath}: Expected a JSON list, but got {type(data).__name__}.")
                return []
    except FileNotFoundError:
        st.error(f"Plant care file not found at {filepath}. Please ensure it exists.")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from {filepath}: {e}")
        return []
    except Exception as e:
        st.error(f"Failed to load or process {filepath}: {e}")
        return []


def find_care_instructions(plant_name_id, care_data, match_threshold=75):
    if not care_data: return None # No data to search
    sci_name = None
    common_name = None

    # Determine scientific/common name from input
    if isinstance(plant_name_id, dict):
        sci_name = plant_name_id.get('scientific_name')
        common_name = plant_name_id.get('common_name')
    elif isinstance(plant_name_id, str):
        sci_name = plant_name_id # Assume string input is scientific name for initial search

    # Prepare search terms (lowercase, stripped)
    search_sci = sci_name.lower().strip() if sci_name and isinstance(sci_name, str) else None
    search_common = common_name.lower().strip() if common_name and isinstance(common_name, str) else None

    # --- Direct Match Logic ---
    # 1. Match Scientific Name exactly
    if search_sci:
        for plant in care_data:
            # Check both 'Scientific Name' and 'Plant Name' as potential scientific name fields
            db_sci = plant.get('Scientific Name', '').lower().strip()
            db_plant_name_as_sci = plant.get('Plant Name', '').lower().strip()
            if search_sci == db_sci or search_sci == db_plant_name_as_sci:
                return plant

    # 2. Match Common Name(s) exactly
    if search_common:
        for plant in care_data:
            # Check 'Plant Name' field
            if search_common == plant.get('Plant Name', '').lower().strip():
                return plant
            # Check 'Common Names' list (if it exists and is a list)
            db_commons = plant.get('Common Names', [])
            if isinstance(db_commons, list):
                for db_c in db_commons:
                    if isinstance(db_c, str) and search_common == db_c.lower().strip():
                        return plant
            # Also handle if 'Common Names' is just a single string
            elif isinstance(db_commons, str):
                 if search_common == db_commons.lower().strip():
                     return plant


    # --- Fuzzy Match Logic (if no exact match found) ---
    # Create a mapping of searchable names (sci/common) to plant data entries
    # Prioritize scientific name if available, otherwise use plant name
    all_db_plants_map = {}
    for p in care_data:
        key_sci = p.get('Scientific Name', '').lower().strip()
        key_plant_name = p.get('Plant Name', '').lower().strip()

        # Use scientific name as primary key if valid, otherwise plant name
        primary_key = key_sci if key_sci else key_plant_name
        if primary_key and primary_key not in all_db_plants_map:
             all_db_plants_map[primary_key] = p

        # Add common names to the map as well, pointing to the same plant object
        db_commons = p.get('Common Names', [])
        if isinstance(db_commons, list):
             for db_c in db_commons:
                 key_common = db_c.lower().strip() if isinstance(db_c, str) else None
                 if key_common and key_common not in all_db_plants_map:
                     all_db_plants_map[key_common] = p
        elif isinstance(db_commons, str): # Handle single string common name
             key_common = db_commons.lower().strip()
             if key_common and key_common not in all_db_plants_map:
                 all_db_plants_map[key_common] = p


    all_db_names = list(all_db_plants_map.keys())
    if not all_db_names: return None # No names to search fuzzily

    best_match_result = None
    highest_score = 0

    # Fuzzy match using scientific name
    if search_sci:
        best_sci_match, score_sci = process.extractOne(search_sci, all_db_names)
        if score_sci > match_threshold and score_sci > highest_score:
            highest_score = score_sci
            best_match_result = all_db_plants_map.get(best_sci_match)

    # Fuzzy match using common name (potentially overriding sci match if score is higher)
    if search_common:
        best_common_match, score_common = process.extractOne(search_common, all_db_names)
        if score_common > match_threshold and score_common > highest_score:
            # highest_score = score_common # Update highest score tracked
            best_match_result = all_db_plants_map.get(best_common_match)

    return best_match_result


def display_identification_result(result):
    st.subheader("🔍 Identification Results")
    if not result:
        st.error("No identification result available.")
        return
    if 'error' in result:
        st.error(f"Identification failed: {result.get('error', 'Unknown error')}")
        return

    conf = result.get('confidence', 0)
    # Determine color based on confidence
    if conf > 75: color = "#28a745" # Green
    elif conf > 50: color = "#ffc107" # Yellow
    else: color = "#dc3545" # Red

    # Display using markdown with HTML for color styling
    st.markdown(f"""
    - **Scientific Name:** `{result.get('scientific_name', 'N/A')}`
    - **Common Name:** `{result.get('common_name', 'N/A')}`
    - **Confidence:** <strong style='color:{color};'>{conf:.1f}%</strong>
    """, unsafe_allow_html=True)


def display_care_instructions(care_info):
    if not care_info or not isinstance(care_info, dict):
        st.warning("Care information is missing or invalid.")
        return

    name = care_info.get('Plant Name', 'This Plant')
    st.subheader(f"🌱 {name} Care Guide")

    with st.expander("📋 Care Summary", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**☀️ Light**")
            st.caption(f"{care_info.get('Light Requirements', 'N/A')}")
            st.markdown("**💧 Water**")
            st.caption(f"{care_info.get('Watering', 'N/A')}")
            st.markdown("**🌡️ Temp**")
            st.caption(f"{care_info.get('Temperature Range', 'N/A')}")
        with c2:
            st.markdown("**💦 Humidity**")
            st.caption(f"{care_info.get('Humidity Preferences', 'N/A')}")
            st.markdown("**🍃 Feeding**")
            st.caption(f"{care_info.get('Feeding Schedule', 'N/A')}")
            st.markdown("**⚠️ Toxicity**")
            st.caption(f"{care_info.get('Toxicity', 'N/A')}")

    # Display "Additional Care" / "Pro Tips" only if present
    additional_care = care_info.get('Additional Care')
    if additional_care and isinstance(additional_care, str) and additional_care.strip():
        with st.expander("✨ Pro Tips"):
             # Use st.markdown to render potential markdown in the tips
             st.markdown(additional_care)


def find_similar_plant_matches(id_result, plant_care_data, limit=3, score_threshold=60):
    if not id_result or 'error' in id_result or not plant_care_data:
        return [] # Cannot find matches without valid ID or care data

    # Create a map of unique plant names (prefer scientific, fallback to common) to plant data
    all_db_plants_map = {}
    for p in plant_care_data:
        primary_name = p.get('Scientific Name', p.get('Plant Name', '')).lower().strip()
        if primary_name: # Only add if there's a name
            all_db_plants_map[primary_name] = p
            # Also map common names if they differ from the primary name
            common_names = p.get('Common Names', [])
            if isinstance(common_names, str): common_names = [common_names] # Ensure list
            if isinstance(common_names, list):
                for cn in common_names:
                    cn_lower = cn.lower().strip() if isinstance(cn, str) else None
                    if cn_lower and cn_lower != primary_name and cn_lower not in all_db_plants_map:
                         all_db_plants_map[cn_lower] = p


    all_db_names = list(all_db_plants_map.keys())
    if not all_db_names: return [] # No names in DB to compare against

    # Get search terms from ID result
    search_sci = id_result.get('scientific_name','').lower().strip()
    search_common = id_result.get('common_name','').lower().strip()

    # Use fuzzywuzzy to find potential matches based on scientific and common names
    matches = {} # Store best score for each potential match {db_name: score}

    # Process scientific name matches
    if search_sci:
        # Increase limit for extract to get more candidates initially
        sci_results = process.extract(search_sci, all_db_names, limit=limit * 2)
        for name, score in sci_results:
            if score >= score_threshold:
                # Keep the highest score found for this name (sci vs common)
                matches[name] = max(matches.get(name, 0), score)

    # Process common name matches
    if search_common:
        common_results = process.extract(search_common, all_db_names, limit=limit * 2)
        for name, score in common_results:
            if score >= score_threshold:
                matches[name] = max(matches.get(name, 0), score)

    # Sort matches by score (descending)
    sorted_matches = sorted(matches.items(), key=lambda item: item[1], reverse=True)

    # Get the unique plant data entries corresponding to the top matches, up to the limit
    final_suggestions = []
    seen_plants = set() # Track plant objects to avoid duplicates if multiple names map to same plant
    for name, score in sorted_matches:
        plant_info = all_db_plants_map.get(name)
        if plant_info:
            # Use a unique identifier for the plant object, e.g., its name or a hash
            plant_id = plant_info.get('Plant Name', '') + plant_info.get('Scientific Name', '')
            if plant_id not in seen_plants:
                final_suggestions.append(plant_info)
                seen_plants.add(plant_id)
                if len(final_suggestions) >= limit:
                    break # Stop once we reach the desired number of suggestions

    return final_suggestions


def display_suggestion_buttons(suggestions):
     if not suggestions:
         # Don't display anything if no suggestions, the calling code shows a warning
         return

     st.info("🌿 Perhaps one of these is a closer match from our database?")
     num_suggestions = len(suggestions)
     cols = st.columns(num_suggestions)

     for i, p_info in enumerate(suggestions):
         # Prefer 'Plant Name', fallback to 'Scientific Name' for button label
         p_name = p_info.get('Plant Name', p_info.get('Scientific Name', f'Suggestion {i+1}'))
         # Create a unique key for the button
         btn_key = f"suggest_{p_name.replace(' ','_').replace('.','')}_{i}" # Basic key sanitization
         # Tooltip shows scientific name if different from display name
         tooltip = f"Select {p_name}"
         sci_name = p_info.get('Scientific Name')
         if sci_name and sci_name != p_name:
             tooltip += f" (Scientific: {sci_name})"

         # Display button in its column
         if cols[i].button(p_name, key=btn_key, help=tooltip, use_container_width=True):
             # --- Action on button click ---
             # Set selected plant's info as the main care info
             st.session_state.plant_care_info = p_info
             # Update ID result to reflect the chosen plant (assume 100% confidence in selection)
             st.session_state.plant_id_result = {
                 'scientific_name': p_info.get('Scientific Name', 'N/A'),
                 'common_name': p_info.get('Plant Name', p_name), # Use the button name if 'Plant Name' field is missing
                 'confidence': 100.0 # User selected it
             }
             # Clear previous suggestions and chat history as we have a new plant context
             st.session_state.suggestions = None
             st.session_state.chat_history = []
             st.session_state.current_chatbot_plant_name = None # Will be updated by chat interface
             st.rerun() # Rerun to display the new care info and chat

# ===== CHAT INTERFACE =====
def display_chat_interface(current_plant_care_info):
    """Displays the chat UI, uses st.container for scrolling with improved error handling."""
    if not current_plant_care_info:
         st.warning("No plant care info available to initialize chat.")
         return
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        st.warning("Chat feature requires a Gemini API key.")
        return

    chatbot_display_name = current_plant_care_info.get("Plant Name", "this plant")
    st.subheader(f"💬 Chat with {chatbot_display_name}")

    # --- CSS Styling ---
    st.markdown("""
        <style>
            .message-container { padding: 1px 5px; } /* Reduced vertical padding */
            .user-message { background: #0b81fe; color: white; border-radius: 18px 18px 0 18px; padding: 8px 14px; margin: 3px 0 3px auto; width: fit-content; max-width: 80%; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.1); animation: fadeIn 0.3s ease-out; }
            .bot-message { background: #e5e5ea; color: #000; border-radius: 18px 18px 18px 0; padding: 8px 14px; margin: 3px auto 3px 0; width: fit-content; max-width: 80%; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.05); animation: fadeIn 0.3s ease-out; }
            .message-meta { font-size: 0.70rem; color: #777; margin-top: 3px; } /* Reduced margin */
            .bot-message .message-meta { text-align: left; color: #555;}
            .user-message .message-meta { text-align: right; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
            /* Ensure chat input doesn't overlap container */
            .stChatInputContainer { position: sticky; bottom: 0; background: white; padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- Chat Initialization/Reset Logic ---
    current_tracked_name = st.session_state.get("current_chatbot_plant_name")
    # Reset if history doesn't exist OR if the plant being chatted with has changed
    if "chat_history" not in st.session_state or current_tracked_name != chatbot_display_name:
        # If switching plants, load *saved* chat log if available, else start fresh
        if "saved_photos" in st.session_state and st.session_state.get("viewing_saved_details"):
            saved_plant_data = st.session_state.saved_photos.get(st.session_state.viewing_saved_details)
            # Ensure saved_plant_data is not None before trying to access 'chat_log'
            if saved_plant_data and 'chat_log' in saved_plant_data:
                st.session_state.chat_history = saved_plant_data['chat_log']
            else:
                st.session_state.chat_history = [] # Start fresh if no log saved or saved_plant_data is None
        else:
             st.session_state.chat_history = [] # Start fresh for new ID

        st.session_state.current_chatbot_plant_name = chatbot_display_name # Track the new plant name


    # --- Chat History Display using st.container ---
    chat_container = st.container(height=400) # Fixed height container for scrolling
    with chat_container:
        for message in st.session_state.get("chat_history", []):
            role = message.get("role")
            content = message.get("content", "")
            time = message.get("time", "") # Get timestamp if available

            if role == "user":
                st.markdown(f'<div class="message-container"><div class="user-message">{content}<div class="message-meta">You • {time}</div></div></div>', unsafe_allow_html=True)
            elif role == "assistant" or role == "model": # Treat assistant/model the same for display
                st.markdown(f'<div class="message-container"><div class="bot-message">🌿 {content}<div class="message-meta">{chatbot_display_name} • {time}</div></div></div>', unsafe_allow_html=True)
            # else: pass # Ignore messages with unknown roles

    # --- Chat Input ---
    # Use key to potentially help differentiate if needed, though usually not required for chat_input
    prompt_key = f"chat_input_{chatbot_display_name.replace(' ','_')}"
    if prompt := st.chat_input(f"Ask {chatbot_display_name}...", key=prompt_key):
        timestamp = datetime.now(EASTERN_TZ).strftime("%H:%M")
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": prompt, "time": timestamp})
        # Rerun immediately to display the user's message
        st.rerun()

    # --- Process Bot Response ---
    # Check if the last message was from the user and we need to generate a response
    if st.session_state.get("chat_history") and st.session_state.chat_history[-1].get("role") == "user":
        with st.spinner(f"{chatbot_display_name} is thinking..."):
            # Pass the current plant's care info and the full history
            bot_response = chat_with_plant(current_plant_care_info, st.session_state.chat_history)

        timestamp = datetime.now(EASTERN_TZ).strftime("%H:%M")
        # Add bot response to history
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response, "time": timestamp})
        # Rerun to display the bot's response
        st.rerun()

# --- Main App Logic ---
def main():
    st.set_page_config(page_title="Plant Buddy", page_icon="🌿", layout="wide")

    # --- Sidebar Navigation and Saved Plants ---
    st.sidebar.title("📚 Plant Buddy")
    # Initialize saved photos in session state if not already present
    if "saved_photos" not in st.session_state: st.session_state.saved_photos = {}

    nav_choice_options = ["🆔 Identify New Plant", "🪴 My Saved Plants"]
    nav_index = 0 # Default to Identify page

    # ===========================================================
    # ===== START: MODIFIED SIDEBAR SELECTBOX SECTION =====
    # ===========================================================
    saved_plant_nicknames = list(st.session_state.saved_photos.keys())
    selected_saved_plant_sb = None # Initialize
    if saved_plant_nicknames:
        st.sidebar.subheader("Saved Plants")
        # Add a "-- Select --" option
        view_options = ["-- Select to View --"] + saved_plant_nicknames

        # --- Calculate the correct index based on the viewing state ---
        current_selection = st.session_state.get("viewing_saved_details")
        select_index = 0 # Default index (for "-- Select --")
        if current_selection and current_selection in view_options:
            try:
                # Find the index of the currently viewed plant in the options list
                select_index = view_options.index(current_selection)
            except ValueError:
                # Should not happen if viewing_saved_details is valid, but safety first
                print(f"Warning: viewing_saved_details '{current_selection}' not found in view_options.")
                select_index = 0 # Fallback to default

        # --- Create the selectbox using the calculated index ---
        selected_saved_plant_sb = st.sidebar.selectbox(
            "View Saved Plant:",
            view_options,
            key="saved_view_selector",
            index=select_index # Set the index here!
        )

        # --- Handle USER interaction with the selectbox ---
        if selected_saved_plant_sb != "-- Select to View --":
            nav_index = 1 # Switch navigation focus to Saved Plants page
            # Update the viewing state ONLY if the user selected something different
            if st.session_state.get("viewing_saved_details") != selected_saved_plant_sb:
                st.session_state.viewing_saved_details = selected_saved_plant_sb
                # No automatic rerun here, subsequent widgets will use the new state
        else:
            # If user manually selected "-- Select --" AND we were previously viewing something
            if st.session_state.get("viewing_saved_details") is not None:
                 st.session_state.viewing_saved_details = None
                 # Force navigation index back to Identify View
                 nav_index = 0
                 # Rerun to clear the details view from the main page
                 st.rerun()

    # ===========================================================
    # ===== END: MODIFIED SIDEBAR SELECTBOX SECTION =====
    # ===========================================================


    # --- Main Navigation Radio Buttons ---
    # The 'index' is now dynamically set based on the selectbox interaction above or default
    nav_choice = st.sidebar.radio(
        "Navigation",
        nav_choice_options,
        key="main_nav_radio",
        index=nav_index, # Use the potentially updated nav_index
        label_visibility="collapsed" # Hide the "Navigation" label itself
    )
    st.sidebar.divider()
    st.sidebar.caption("Powered by PlantNet & Gemini")


    # --- Initialize State Variables ---
    # Ensure all necessary state variables are initialized to avoid errors
    defaults = {
        "plant_id_result": None, "plant_care_info": None, "chat_history": [],
        "current_chatbot_plant_name": None, "suggestions": None,
        "uploaded_file_bytes": None, "uploaded_file_type": None,
        "saving_mode": False, "last_view": nav_choice_options[0], # Start with default view
        "viewing_saved_details": st.session_state.get("viewing_saved_details", None) # Preserve from selectbox logic
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


    # --- Check API Keys and Load Data ---
    api_keys_ok = True
    if not PLANTNET_API_KEY or PLANTNET_API_KEY == "YOUR_PLANTNET_API_KEY_HERE":
        st.error("PlantNet API Key is missing or invalid. Please set it in your environment variables or .env file.")
        api_keys_ok = False
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        st.warning("Gemini API Key is missing or invalid. Chat functionality will be disabled.")
        # Don't set api_keys_ok to False here, identification can still work

    plant_care_data = load_plant_care_data()
    if not plant_care_data:
        # Error is shown in load_plant_care_data
        st.stop()
    if not api_keys_ok: # Stop if essential PlantNet key is missing
        st.stop()


    # --- Main Content Area based on Navigation ---

    # ====================================
    # ===== Identify New Plant View =====
    # ====================================
    if nav_choice == "🆔 Identify New Plant":
        st.header("🔎 Identify a New Plant")

        # --- State Reset Logic ---
        navigated_from_saved = st.session_state.last_view == "🪴 My Saved Plants"
        # Check if selected_saved_plant_sb is defined before accessing
        # This logic is implicitly handled by the sidebar selectbox interaction now
        # deselected_saved = selected_saved_plant_sb == "-- Select to View --" if selected_saved_plant_sb is not None else True

        # Reset if coming FROM saved view and NOT currently viewing saved details (i.e., user switched via radio or selected '-- Select --')
        if navigated_from_saved and st.session_state.get("viewing_saved_details") is None:
            print("DEBUG: Resetting state -> Switched to Identify View")
            st.session_state.update({
                "plant_id_result": None, "plant_care_info": None,
                "current_chatbot_plant_name": None, "suggestions": None,
                "uploaded_file_bytes": None, "uploaded_file_type": None,
                "chat_history": [], "saving_mode": False,
            })
            st.session_state.pop('plant_uploader', None) # Clear potential file uploader state

        st.session_state.last_view = "🆔 Identify New Plant" # Update last view tracker


        # --- File Uploader ---
        uploaded_file = st.file_uploader(
            "Upload a clear photo of your plant:", type=["jpg", "jpeg", "png"],
            key="plant_uploader", # Consistent key
            help="Upload an image file (JPG, PNG).",
            on_change=lambda: st.session_state.update({ # Reset relevant state on *new file upload*
                 "plant_id_result": None, "plant_care_info": None, "chat_history": [],
                 "current_chatbot_plant_name": None, "suggestions": None,
                 "uploaded_file_bytes": None, "uploaded_file_type": None, # Clear previous bytes/type too
                 "saving_mode": False,
            })
        )

        # --- Logic Based on Uploader State ---
        if uploaded_file is None:
             # Only show welcome if no file uploaded AND no results are currently stored
             if st.session_state.uploaded_file_bytes is None:
                 st.info("Welcome to Plant Buddy! Upload a plant image above to get started, or select a saved plant from the sidebar.")
             # If there *are* results stored (e.g., user uploaded, then removed file), keep showing results below
             elif st.session_state.plant_id_result is not None:
                 pass # Let the code below display the existing results
        else:
            # --- File Uploaded: Process ---
            # Store bytes and type if not already stored (or if uploader changed)
            if st.session_state.uploaded_file_bytes is None:
                st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
                st.session_state.uploaded_file_type = uploaded_file.type
                # Force rerun to ensure image display and ID logic runs immediately
                st.rerun()

        # --- Display Image and Subsequent Info (if file bytes exist) ---
        # This block runs if file bytes are stored (either just uploaded or previously)
        if st.session_state.uploaded_file_bytes is not None:

            # --- Display Image using the NEW function (NO COLUMNS) ---
            try:
                display_image_with_max_height(
                    image_source=st.session_state.uploaded_file_bytes,
                    caption="Your Uploaded Plant",
                    max_height_px=400 # Adjust max height if desired
                )
                st.divider() # Add a divider after the image
            except Exception as e:
                st.error(f"Error displaying image: {e}")
                st.stop() # Stop if image can't be shown

            # --- Identification and Results (Displayed AFTER the image) ---
            # Run Identification if results are not already in state
            if st.session_state.plant_id_result is None:
                loader_placeholder = st.empty()
                with loader_placeholder.container():
                    # Simplified loading text centered
                    st.markdown("<div style='text-align:center;'><p><i>Identifying plant...</i></p></div>", unsafe_allow_html=True)
                    # components.html(loading_animation_html, height=250) # Optional animation

                try:
                    result = identify_plant(st.session_state.uploaded_file_bytes)
                    st.session_state.plant_id_result = result
                except Exception as e:
                    st.session_state.plant_id_result = {'error': f"Identification process failed: {str(e)}"}
                finally:
                    loader_placeholder.empty() # Remove loading indicator
                    st.rerun() # Rerun to display the results or error

            # Display results, care info, suggestions, save options etc. (if ID is done)
            elif st.session_state.plant_id_result is not None:
                id_result = st.session_state.plant_id_result

                # --- Saving Mode UI ---
                if st.session_state.saving_mode:
                    st.header("💾 Save This Plant Profile")
                    # Display small image preview while saving
                    if st.session_state.uploaded_file_bytes:
                        try:
                            # Use standard st.image for the small saving preview
                            st.image(Image.open(BytesIO(st.session_state.uploaded_file_bytes)), width=150, caption="Image to save")
                        except Exception:
                            st.warning("Could not display image preview for saving.")

                    id_info = st.session_state.get("plant_id_result", {})
                    sci_name = id_info.get('scientific_name', 'N/A')
                    com_name = id_info.get('common_name', 'N/A')
                    st.markdown(f"**Identified as:** {com_name} (`{sci_name}`)")

                    with st.form("save_form"):
                        save_nickname = st.text_input("Enter a nickname for this plant:", key="save_nickname_input")
                        submitted = st.form_submit_button("✅ Confirm Save")
                        if submitted:
                            if not save_nickname:
                                st.warning("Please enter a nickname to save.")
                            elif save_nickname in st.session_state.saved_photos:
                                st.warning(f"A plant named '{save_nickname}' already exists. Please choose a different name.")
                            else:
                                try:
                                    encoded_img = base64.b64encode(st.session_state.uploaded_file_bytes).decode()
                                    data_url = f"data:{st.session_state.uploaded_file_type};base64,{encoded_img}"
                                    st.session_state.saved_photos[save_nickname] = {
                                        "nickname": save_nickname, "image": data_url,
                                        "id_result": st.session_state.plant_id_result,
                                        "care_info": st.session_state.plant_care_info,
                                        "chat_log": st.session_state.get("chat_history", [])
                                    }
                                    # Clear state *after* successful save
                                    st.session_state.update({
                                        "uploaded_file_bytes": None, "uploaded_file_type": None,
                                        "plant_id_result": None, "plant_care_info": None,
                                        "current_chatbot_plant_name": None, "suggestions": None,
                                        "chat_history": [], "saving_mode": False
                                    })
                                    st.session_state.pop('plant_uploader', None) # Clear file uploader state
                                    st.success(f"Successfully saved '{save_nickname}'!")
                                    st.balloons()
                                    st.rerun() # Rerun to clear the identify page
                                except Exception as e:
                                    st.error(f"Error saving plant profile: {e}")

                    if st.button("❌ Cancel Save", key="cancel_save_button"):
                        st.session_state.saving_mode = False
                        st.rerun()

                # --- Normal Display (Not Saving) ---
                else:
                    display_identification_result(id_result)

                    if 'error' not in id_result:
                        current_id_sci_name = id_result.get('scientific_name')
                        care_info_state = st.session_state.get('plant_care_info')

                        needs_care_update = False
                        # Check if care info needs update (e.g., first run, or ID result changed plant)
                        if care_info_state is None:
                            needs_care_update = True
                        elif isinstance(care_info_state, dict):
                             # Compare based on a reliable unique identifier if possible
                            state_sci_name = care_info_state.get('Scientific Name')
                            state_plant_name = care_info_state.get('Plant Name') # Fallback compare
                            # If the current ID's scientific name doesn't match the stored care info's scientific name OR plant name, update
                            if current_id_sci_name != state_sci_name and current_id_sci_name != state_plant_name:
                                needs_care_update = True
                        else: # If care_info_state is somehow not a dict, force update
                            needs_care_update = True

                        if needs_care_update:
                            print(f"DEBUG: Finding care instructions for ID: {id_result}")
                            found_care = find_care_instructions(id_result, plant_care_data)
                            st.session_state.plant_care_info = found_care
                            # Reset suggestions/chat ONLY if we update care info
                            st.session_state.suggestions = None
                            st.session_state.chat_history = []
                            st.session_state.current_chatbot_plant_name = None
                            # Rerun needed to display the newly found info or suggestions
                            st.rerun()

                        care_info = st.session_state.plant_care_info

                        # --- Display Care Info & Chat (if found) ---
                        if care_info:
                            display_care_instructions(care_info)
                            st.divider()
                            if st.button("💾 Save Plant Profile", key="save_profile_button"):
                                st.session_state.saving_mode = True; st.rerun()
                            st.divider()
                            display_chat_interface(care_info)

                        # --- Display Suggestions (if care info NOT found) ---
                        else:
                            st.warning("Could not find specific care instructions for this exact plant in our database.")
                            # Only find suggestions if they haven't been found yet for this ID result
                            if st.session_state.suggestions is None:
                                st.session_state.suggestions = find_similar_plant_matches(id_result, plant_care_data)
                                st.rerun() # Rerun to display suggestions

                            # Always display buttons if suggestions exist in state
                            display_suggestion_buttons(st.session_state.suggestions)
                            st.divider()
                            if st.button("💾 Save Identification Only", key="save_id_only_button"):
                                st.session_state.saving_mode = True; st.rerun()

                    else: # Handle case where identification itself failed
                        pass # Error displayed by display_identification_result


    # ====================================
    # ===== Saved Plants View =====
    # ====================================
    elif nav_choice == "🪴 My Saved Plants":
        st.header("🪴 My Saved Plant Profiles")
        st.session_state.last_view = "🪴 My Saved Plants" # Track view

        saved_plant_nicknames = list(st.session_state.saved_photos.keys())
        nickname_to_view = st.session_state.get("viewing_saved_details") # Get from state (set by sidebar selectbox or card button)

        if not saved_plant_nicknames:
            st.info("You haven't saved any plants yet. Go to 'Identify New Plant' to add some!")
        # If a specific plant IS selected for viewing:
        elif nickname_to_view and nickname_to_view in st.session_state.saved_photos:
             st.subheader(f"Showing Details for: '{nickname_to_view}'")
             entry = st.session_state.saved_photos[nickname_to_view]

             # --- Display saved image using the new function ---
             if entry.get("image"):
                 try:
                     # Use the helper function for consistent sizing in details view
                     display_image_with_max_height(entry["image"], caption=f"{nickname_to_view}", max_height_px=400)
                 except Exception as e:
                     st.error(f"Error displaying saved image: {e}")
             else:
                 st.caption("No image saved.")
             st.divider() # Divider after image

             # --- Display saved ID result ---
             saved_id_result = entry.get("id_result")
             if saved_id_result:
                 display_identification_result(saved_id_result)
             else:
                 st.info("No identification details were saved.")
             st.divider()

             # --- Display care info if saved ---
             saved_care_info = entry.get("care_info")
             if saved_care_info:
                 display_care_instructions(saved_care_info)
                 st.divider()
                 # --- Chat Interface for Saved Plant ---
                 # Use saved care info to initialize/display chat
                 # Check if we need to load the chat history for *this specific plant*
                 current_chat_plant_name = saved_care_info.get("Plant Name") # Get name from care info
                 if st.session_state.get("current_chatbot_plant_name") != current_chat_plant_name:
                     st.session_state.chat_history = entry.get("chat_log", []) # Restore THIS log
                     st.session_state.current_chatbot_plant_name = current_chat_plant_name
                 # Make sure the current care info used by the chat function is the saved one
                 st.session_state.plant_care_info = saved_care_info
                 display_chat_interface(saved_care_info) # Display chat

             else:
                 st.info("No specific care instructions were saved for this plant.")


             # --- Delete Button ---
             st.divider()
             delete_key = f"del_{nickname_to_view}".replace(" ", "_") # Ensure key is valid
             if st.button(f"🗑️ Delete '{nickname_to_view}' Profile", key=delete_key, use_container_width=False): # Changed width
                 del st.session_state.saved_photos[nickname_to_view]
                 st.session_state.viewing_saved_details = None
                 # Clear potentially related state variables
                 st.session_state.update({k: None for k in ["plant_id_result", "plant_care_info", "current_chatbot_plant_name", "suggestions", "uploaded_file_bytes", "uploaded_file_type"]})
                 st.session_state.chat_history = []; st.session_state.saving_mode = False
                 st.success(f"Deleted '{nickname_to_view}'.")
                 # Resetting the selectbox value requires setting its index on rerun,
                 # which is handled by the sidebar logic when viewing_saved_details is None.
                 st.rerun()

        # If NO specific plant is selected (i.e., "-- Select --" is chosen or page just loaded):
        else:
            st.info("Select a plant from the 'View Saved Plant' dropdown in the sidebar to see its details.")
            st.markdown("---")
            st.subheader("All Saved Plants Overview")
            # Display Grid of Information Cards (Overview)
            num_columns = 3 # Adjust number of columns for cards
            cols = st.columns(num_columns)
            col_index = 0

            for nickname in saved_plant_nicknames:
                plant_data = st.session_state.saved_photos.get(nickname)
                if not plant_data: continue

                with cols[col_index % num_columns]:
                    with st.container(border=True):
                        # Display image within the card - use st.image for overview cards
                        if plant_data.get("image"):
                            try:
                                st.image(plant_data["image"], use_container_width=True)
                            except Exception: st.caption("Image error")
                        st.markdown(f"**{nickname}**") # Nickname

                        id_res = plant_data.get("id_result", {})
                        com_name = id_res.get('common_name', 'N/A')
                        st.caption(f"{com_name}") # Common name

                        # ===========================================================
                        # ===== START: MODIFIED VIEW DETAILS BUTTON SECTION =====
                        # ===========================================================
                        # Button to view full details
                        view_card_key = f"view_card_{nickname}".replace(" ", "_") # Ensure key is valid
                        if st.button(f"View Full Details", key=view_card_key, use_container_width=True):
                            st.session_state.viewing_saved_details = nickname
                            # REMOVED the direct modification of saved_view_selector state here
                            # The selectbox index will be updated on the rerun via sidebar logic
                            st.rerun() # Rerun to show details view and update selectbox index
                        # ===========================================================
                        # ===== END: MODIFIED VIEW DETAILS BUTTON SECTION =====
                        # ===========================================================
                col_index += 1

# --- Run the App ---
if __name__ == "__main__":
    main()
