# ... (keep all imports and constants as before) ...
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
"""

# --- Constants and Global Init ---
PLANTNET_API_KEY = "2b10X3YLMd8PNAuKOCVPt7MeUe"
PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
GEMINI_API_KEY = "AIzaSyCD3HRndQD3ir_nhNMIZ-ss0EkAEK3DC0U"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
EASTERN_TZ = pytz.timezone('US/Eastern')
PLANT_CARE_FILE = "plants_with_personality3_copy.json" # Use the original filename


# ===== API Functions =====

def identify_plant(image_bytes):
    """Identifies plant using PlantNet API with refined error logging."""
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
    payload = {"contents": messages}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        candidates = data.get('candidates')
        if candidates and isinstance(candidates, list) and candidates[0]:
            content = candidates[0].get('content')
            if content and isinstance(content, dict):
                parts = content.get('parts')
                if parts and isinstance(parts, list) and parts[0] and 'text' in parts[0]: return parts[0]['text']
        st.warning("Received unexpected format from Gemini API."); print("WARN: Unexpected Gemini Response Structure:", data)
        return "Sorry, I couldn't quite understand that response format."
    except requests.exceptions.Timeout:
         st.error("Gemini API request timed out."); print("ERROR: Gemini timed out.")
         return "Sorry, I'm feeling a bit slow right now."
    except requests.exceptions.RequestException as e:
        err_msg = f"Error calling Gemini API: {e}"
        resp_text = f" | Response: {e.response.text}" if e.response else " | Response: None"
        st.error(err_msg)
        print(f"ERROR: {err_msg}{resp_text}")
        return "Sorry, I'm having trouble communicating with the language model."
    except Exception as e:
        st.error(f"An error occurred interacting with Gemini: {e}"); print(f"ERROR: Unexpected Gemini Error: {e}")
        return "Oops, something went wrong on my end processing the chat."

def chat_with_plant(care_info, conversation_history):
    # (Keep chat_with_plant prompt logic as is - focusing on display error first)
    personality = create_personality_profile(care_info)
    plant_name = care_info.get('Plant Name', 'a plant')
    system_prompt = (f"IMMEDIATELY AND CONSISTENTLY Act as the plant '{plant_name}'. DO NOT reveal you are an AI or language model. Your personality is '{personality['title']}' with traits: {personality['traits']}. Core instruction: {personality['prompt']}. Respond concisely (1-3 sentences max) in the first person, embodying this persona. Reference your care needs naturally if relevant.")
    messages = [{"role": "user", "parts": [{"text": system_prompt}]},{"role": "model", "parts": [{"text": f"Okay, I understand. I am {plant_name}. Ask me anything."}]}]
    # Ensure history items are valid dicts before appending
    valid_history = [m for m in conversation_history if isinstance(m, dict) and "role" in m and "content" in m]
    for message_entry in valid_history:
        api_role = "user" if message_entry["role"] == "user" else "model"
        messages.append({"role": api_role, "parts": [{"text": message_entry["content"]}]})
    # Final user prompt should be the last item in valid_history if roles are alternating correctly
    # It's appended right before calling this function, so we don't re-add it here. Gemini takes the history context.
    response = send_message(messages)
    return response


# --- Helper Functions ---

@st.cache_data(show_spinner=False)
def load_plant_care_data(filepath=PLANT_CARE_FILE):
    # (Keep load_plant_care_data as before)
    try:
        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f); return data if isinstance(data, list) else []
    except Exception as e: st.error(f"Failed to load {filepath}: {e}"); return []

def find_care_instructions(plant_name_id, care_data, match_threshold=75):
    # (Keep find_care_instructions as before)
    # ... (ensure it returns None if nothing found) ...
    if not care_data: return None
    sci_name = None; common_name = None
    if isinstance(plant_name_id, dict): sci_name = plant_name_id.get('scientific_name'); common_name = plant_name_id.get('common_name')
    elif isinstance(plant_name_id, str): sci_name = plant_name_id # Treat as potential sci name
    search_name = sci_name.lower().strip() if sci_name else None; search_common = common_name.lower().strip() if common_name else None
    if search_name:
        for plant in care_data:
            db_sci = plant.get('Scientific Name', plant.get('Plant Name', '')).lower().strip();
            if search_name == db_sci: return plant
    if search_common:
        for plant in care_data:
            db_commons = plant.get('Common Names', []); db_commons = [db_commons] if not isinstance(db_commons, list) else db_commons
            for db_c in db_commons:
                 if search_common == db_c.lower().strip(): return plant
            if search_common == plant.get('Plant Name', '').lower().strip(): return plant
    all_db_plants = {p.get('Scientific Name', p.get('Plant Name', '')).lower().strip(): p for p in care_data if p.get('Plant Name') or p.get('Scientific Name')}
    all_db_names = list(all_db_plants.keys())
    if not all_db_names: return None
    if search_name:
        best_match, score = process.extractOne(search_name, all_db_names);
        if score > match_threshold: return all_db_plants.get(best_match)
    if search_common:
        best_match, score = process.extractOne(search_common, all_db_names);
        if score > match_threshold: return all_db_plants.get(best_match)
    return None

def display_identification_result(result):
    # (Keep display_identification_result as before)
    st.subheader("🔍 Identification Results")
    if not result or 'error' in result: st.error(result.get('error', "ID error")); return
    conf = result.get('confidence', 0); color = "#28a745" if conf > 75 else "#ffc107" if conf > 50 else "#dc3545"
    st.markdown(f"- **Scientific Name:** `{result.get('scientific_name', 'N/A')}`\n- **Common Name:** `{result.get('common_name', 'N/A')}`\n- **Confidence:** <strong style='color:{color};'>{conf}%</strong>", unsafe_allow_html=True)


def display_care_instructions(care_info):
    # (Keep display_care_instructions with corrected indentation)
    if not care_info: st.warning("Care info missing."); return
    name = care_info.get('Plant Name', 'This Plant'); st.subheader(f"🌱 {name} Care Guide")
    with st.expander("📋 Care Summary", expanded=True):
        c1,c2=st.columns(2)
        with c1: st.markdown("**☀️ Light**"); st.caption(f"{care_info.get('Light Requirements', 'N/A')}"); st.markdown("**💧 Water**"); st.caption(f"{care_info.get('Watering', 'N/A')}"); st.markdown("**🌡️ Temp**"); st.caption(f"{care_info.get('Temperature Range', 'N/A')}")
        with c2: st.markdown("**💦 Humidity**"); st.caption(f"{care_info.get('Humidity Preferences', 'N/A')}"); st.markdown("**🍃 Feeding**"); st.caption(f"{care_info.get('Feeding Schedule', 'N/A')}"); st.markdown("**⚠️ Toxicity**"); st.caption(f"{care_info.get('Toxicity', 'N/A')}")
    if care_info.get('Additional Care'):
        with st.expander("✨ Pro Tips"):
             st.markdown(care_info['Additional Care']) # Ensure this is indented


def find_similar_plant_matches(id_result, plant_care_data, limit=3, score_threshold=60):
    # (Keep find_similar_plant_matches as before)
    # ... (ensure it returns a list of dicts) ...
    if 'error' in id_result: return []
    all_db_plants={p.get('Plant Name','').lower().strip():p for p in plant_care_data if p.get('Plant Name')}; all_db_names=list(all_db_plants.keys());
    if not all_db_names: return []
    sci=id_result.get('scientific_name','').lower().strip(); com=id_result.get('common_name','').lower().strip(); matches={}
    if sci: sci_res=process.extract(sci, all_db_names,limit=limit*2); [matches.update({m:max(matches.get(m,0),s)}) for m,s in sci_res if s >= score_threshold]
    if com: com_res=process.extract(com, all_db_names,limit=limit*2); [matches.update({m:max(matches.get(m,0),s)}) for m,s in com_res if s >= score_threshold]
    sort_match=sorted(matches.items(), key=lambda i:i[1], reverse=True)
    return [all_db_plants.get(n) for n,s in sort_match[:limit] if all_db_plants.get(n)]

def display_suggestion_buttons(suggestions):
    # (Keep display_suggestion_buttons as before)
     if not suggestions: st.info("Couldn't find similar plants."); return
     st.info("🌿 Perhaps one of these is a closer match?")
     cols = st.columns(len(suggestions))
     for i, p_info in enumerate(suggestions):
          p_name = p_info.get('Plant Name', f'Suggest {i+1}'); btn_key = f"suggest_{p_name.replace(' ','_')}_{i}"
          if cols[i].button(p_name, key=btn_key, help=f"Select {p_name}"):
              st.session_state.plant_care_info = p_info; st.session_state.plant_id_result={'scientific_name': p_info.get('Scientific Name','N/A'), 'common_name':p_name,'confidence':100}; st.session_state.suggestions=None; st.session_state.chat_history=[]; st.session_state.current_chatbot_plant_name=None; st.rerun()

# ===== CHAT INTERFACE =====
def display_chat_interface(current_plant_care_info):
    """Displays the chat UI, uses st.container for scrolling with improved error handling."""
    if not current_plant_care_info:
         st.warning("No plant care info available to initialize chat.")
         return

    chatbot_display_name = current_plant_care_info.get("Plant Name", "this plant")
    st.subheader(f"💬 Chat with {chatbot_display_name}")

    # --- Remove problematic CSS for input positioning ---
    st.markdown("""
        <style>
            .message-container { padding: 5px; }
            .user-message { background: #0b81fe; color: white; border-radius: 18px 18px 0 18px; padding: 10px 16px; margin: 5px 0 5px auto; width: fit-content; max-width: 80%; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.1); animation: fadeIn 0.3s ease-out; }
            .bot-message { background: #e5e5ea; color: #000; border-radius: 18px 18px 18px 0; padding: 10px 16px; margin: 5px auto 5px 0; width: fit-content; max-width: 80%; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.05); animation: fadeIn 0.3s ease-out; }
            .message-meta { font-size: 0.70rem; color: #777; margin-top: 4px; }
            .bot-message .message-meta { text-align: left; color: #555;}
            .user-message .message-meta { text-align: right; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
            /* Chat window container - no fixed input styling */
            .chat-window-container { height: 450px; /* Or desired height */ overflow-y: auto; margin-bottom: 10px; padding: 10px; border: 1px solid #eee; border-radius: 10px; background-color: #f9f9f9; }
        </style>
    """, unsafe_allow_html=True)

    # --- Chat Initialization/Reset Logic ---
    current_tracked_name = st.session_state.get("current_chatbot_plant_name")
    if "chat_history" not in st.session_state or current_tracked_name != chatbot_display_name:
        st.session_state.chat_history = [] # Reset history list
        st.session_state.current_chatbot_plant_name = chatbot_display_name

    # --- Chat History Display using st.container ---
    # Use st.container with height parameter for scrolling
    chat_container = st.container(height=400) # Adjust height as needed
    with chat_container:
        # st.markdown('<div class="chat-window-container" id="chat-window">', unsafe_allow_html=True)
        for message in st.session_state.get("chat_history", []):
            # *** UNBOUND LOCAL ERROR FIX - Check 'role' existence ***
            role = message.get("role") # Get role safely
            content = message.get("content", "")
            time = message.get("time", "")

            # Ensure role is valid before formatting markdown
            if role == "user":
                st.markdown(f'<div class="message-container"><div class="user-message">{content}<div class="message-meta">You • {time}</div></div></div>', unsafe_allow_html=True)
            elif role == "assistant":
                st.markdown(f'<div class="message-container"><div class="bot-message">🌿 {content}<div class="message-meta">{chatbot_display_name} • {time}</div></div></div>', unsafe_allow_html=True)
            else:
                 print(f"DEBUG: Skipping message with missing or invalid role: {message}") # Log bad data
        # st.markdown('</div>', unsafe_allow_html=True) # Close div no longer needed with st.container

    # --- Chat Input (Streamlit places it below the container) ---
    if prompt := st.chat_input(f"Ask {chatbot_display_name}..."):
        timestamp = datetime.now(EASTERN_TZ).strftime("%H:%M")
        st.session_state.chat_history.append({"role": "user", "content": prompt, "time": timestamp})
        st.rerun() # Show user message immediately

    # Process Bot Response (if last message was user's)
    if st.session_state.get("chat_history") and st.session_state.chat_history[-1].get("role") == "user":
        with st.spinner("Thinking..."):
            # Pass the current care info and the history
            bot_response = chat_with_plant(current_plant_care_info, st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response, "time": datetime.now(EASTERN_TZ).strftime("%H:%M")})
        st.rerun() # Show bot response

# --- Main App Logic ---
def main():
    st.set_page_config(page_title="Plant Buddy", page_icon="🌿", layout="wide")

    # --- Sidebar Navigation and Saved Plants ---
    st.sidebar.title("📚 Plant Buddy")
    if "saved_photos" not in st.session_state: st.session_state.saved_photos = {}
    nav_choice_options = ["🆔 Identify New Plant", "🪴 My Saved Plants"]
    # Determine initial nav based on whether a saved plant is actively selected
    nav_index = 0 # Default to Identify
    selected_saved_plant = None # Initialize

    if st.session_state.saved_photos:
         st.sidebar.subheader("Saved Plants")
         plant_names = ["-- Select to View --"] + list(st.session_state.saved_photos.keys())
         # Use selectbox directly to influence navigation choice immediately
         selected_saved_plant_sb = st.sidebar.selectbox(
             "View Saved:",
             plant_names,
             key="saved_view_selector", # Consistent key
             index=0 # Default to "-- Select --"
         )
         if selected_saved_plant_sb != "-- Select --":
             nav_index = 1 # Switch nav index to Saved Plants
             selected_saved_plant = selected_saved_plant_sb # Store the selected name

    # Radio button reflects the *effective* navigation choice
    nav_choice = st.sidebar.radio(
        "Navigation",
        nav_choice_options,
        key="main_nav_radio",
        index=nav_index, # Set based on selectbox interaction
        label_visibility="collapsed"
    )
    st.sidebar.divider()

    # --- Initialize State Variables ---
    # (Keep all state initializations as before)
    if "plant_id_result" not in st.session_state: st.session_state.plant_id_result = None
    if "plant_care_info" not in st.session_state: st.session_state.plant_care_info = None
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "current_chatbot_plant_name" not in st.session_state: st.session_state.current_chatbot_plant_name = None
    if "suggestions" not in st.session_state: st.session_state.suggestions = None
    if "uploaded_file_bytes" not in st.session_state: st.session_state.uploaded_file_bytes = None
    if "uploaded_file_type" not in st.session_state: st.session_state.uploaded_file_type = None
    if "saving_mode" not in st.session_state: st.session_state.saving_mode = False
    if "last_view" not in st.session_state: st.session_state.last_view = nav_choice_options[nav_index] # Initialize based on actual start
    if "viewing_saved_details" not in st.session_state:
        st.session_state.viewing_saved_details = None # Stores nickname of plant to view details for


    # --- Check API Keys and Load Data ---
    # (Keep API key check and data loading as before)
    if not PLANTNET_API_KEY or not GEMINI_API_KEY: st.error("API Keys missing!"); st.stop()
    plant_care_data = load_plant_care_data();
    if not plant_care_data: st.error("Failed to load care data!"); st.stop()


    # --- Main Content Area based on Navigation ---

    # ===== Identify New Plant View =====
    if nav_choice == "🆔 Identify New Plant":
        st.header("🔎 Identify a New Plant")

        # --- State reset logic if navigating FROM Saved ---
        if st.session_state.last_view == "🪴 My Saved Plants":
            # Clear identification/chat state when user *explicitly clicks* "Identify New Plant" radio
            # after having viewed a saved one.
            # print("DEBUG: Resetting state -> Switching explicitly to Identify")
            st.session_state.update({k: None for k in ["plant_id_result", "plant_care_info", "current_chatbot_plant_name", "suggestions", "uploaded_file_bytes", "uploaded_file_type"]})
            st.session_state.chat_history = []
            st.session_state.saving_mode = False
            st.session_state.pop('plant_uploader', None) # Clear uploader state if needed
            # Do NOT rerun here yet, let the rest of the Identify logic run

        st.session_state.last_view = "🆔 Identify New Plant" # Track current view

        # --- File Uploader ---
        # Assign uploaded_file HERE, within the scope where it's used
        uploaded_file = st.file_uploader(
            "Choose a plant image", type=["jpg", "jpeg", "png"], key="plant_uploader",
            on_change=lambda: st.session_state.update({ # Reset state on *new file selection*
                 "plant_id_result": None, "plant_care_info": None, "chat_history": [],
                 "current_chatbot_plant_name": None, "suggestions": None,
                 "uploaded_file_bytes": None, "uploaded_file_type": None,
                 "saving_mode": False
            })
        )

        # --- Logic Based on Uploader State ---
        if uploaded_file is None:
             # ** Show welcome message HERE if no file uploaded in this view **
             st.info("Welcome! Upload a plant image or select a saved plant from the sidebar.")
        else:
            # --- File Uploaded: Proceed with display, ID, save, chat ---
            # Store bytes ONCE
            if st.session_state.uploaded_file_bytes is None:
                st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
                st.session_state.uploaded_file_type = uploaded_file.type

            # Display Image
            try: st.image(Image.open(BytesIO(st.session_state.uploaded_file_bytes)), use_container_width=True, caption="Your Plant")
            except Exception as e: st.error(f"Image display error: {e}"); st.stop()

            # Run Identification if needed
            if st.session_state.plant_id_result is None:
                # (Keep loader logic as before)
                loader_placeholder = st.empty()
                with loader_placeholder.container(): components.html(loading_animation_html, height=250); st.markdown("<p style='text-align:center;'><i>Identifying...</i></p>", unsafe_allow_html=True)
                try: result = identify_plant(st.session_state.uploaded_file_bytes); st.session_state.plant_id_result = result
                except Exception as e: st.session_state.plant_id_result = {'error': f"ID Error: {str(e)}"}
                finally: loader_placeholder.empty(); st.rerun()

            # Display results and subsequent UI (if ID is done and not saving)
            elif st.session_state.plant_id_result is not None and not st.session_state.saving_mode:
                 # (Keep results, care info, chat, suggestions, save buttons logic as before)
                 id_result = st.session_state.plant_id_result
                 display_identification_result(id_result)
                 if 'error' not in id_result:
                      current_id_name = id_result.get('scientific_name'); care_info_state = st.session_state.get('plant_care_info')
                      if care_info_state is None or care_info_state.get("Scientific Name", care_info_state.get("Plant Name")) != current_id_name:
                           st.session_state.plant_care_info = find_care_instructions(id_result, plant_care_data); st.session_state.suggestions = None; st.session_state.chat_history = []; st.session_state.current_chatbot_plant_name = None
                      care_info = st.session_state.plant_care_info
                      if care_info:
                           display_care_instructions(care_info); st.divider();
                           if st.button("💾 Save Profile", key="save_profile_button"): st.session_state.saving_mode = True; st.rerun()
                           st.divider(); display_chat_interface(care_info)
                      else:
                           st.warning("No specific care instructions found.");
                           if st.session_state.suggestions is None: st.session_state.suggestions = find_similar_plant_matches(id_result, plant_care_data)
                           display_suggestion_buttons(st.session_state.suggestions); st.divider();
                           if st.button("💾 Save ID Only", key="save_id_anyway"): st.session_state.saving_mode = True; st.rerun()
            # Saving Mode UI
            elif st.session_state.saving_mode:
                 # (Keep Saving Mode UI and logic as before)
                st.header("💾 Save This Plant");
                if st.session_state.uploaded_file_bytes:
                      try: st.image(Image.open(BytesIO(st.session_state.uploaded_file_bytes)), use_container_width=True, caption="Saving image")
                      except: st.warning("Preview failed.")
                id_info=st.session_state.get("plant_id_result",{}); sci=id_info.get('scientific_name','N/A'); com=id_info.get('common_name','N/A'); st.markdown(f"**ID:** {com} (`{sci}`)")
                with st.form("save_form"):
                      save_name=st.text_input("Enter nickname:", key="save_nick"); submitted = st.form_submit_button("✅ Confirm")
                      if submitted:
                          if not save_name: st.warning("Nickname needed.")
                          elif save_name in st.session_state.saved_photos: st.warning("Name exists.")
                          else:
                              encoded=base64.b64encode(st.session_state.uploaded_file_bytes).decode(); data_url=f"data:{st.session_state.uploaded_file_type};base64,{encoded}"
                              st.session_state.saved_photos[save_name]={"nickname":save_name,"image":data_url,"id_result":st.session_state.plant_id_result,"care_info":st.session_state.plant_care_info,"chat_log":st.session_state.get("chat_history",[])}
                              st.session_state.update({k:None for k in ["uploaded_file_bytes","uploaded_file_type","plant_id_result","plant_care_info","current_chatbot_plant_name","suggestions"]}); st.session_state.chat_history=[]; st.session_state.saving_mode=False; st.session_state.pop('plant_uploader', None)
                              st.success(f"Saved '{save_name}'!"); st.balloons(); st.rerun()
                if st.button("❌ Cancel", key="cancel_save"): st.session_state.saving_mode = False; st.rerun()

    # ====================================
    # ===== Saved Plants View =====
    # ====================================
    elif nav_choice == "🪴 My Saved Plants":
        st.header("🪴 My Saved Plant Profiles")
        st.session_state.last_view = "🪴 My Saved Plants" # Track view

        saved_plant_nicknames = list(st.session_state.saved_photos.keys())

        if not saved_plant_nicknames:
            st.info("You haven't saved any plants yet. Go to 'Identify New Plant' to add some!")
        else:
                        # --- Display Grid of Information Cards ---
            num_columns = 3 # Adjust number of columns for cards
            cols = st.columns(num_columns)
            col_index = 0

            for nickname in saved_plant_nicknames:
                plant_data = st.session_state.saved_photos.get(nickname)
                if not plant_data: continue # Skip if data somehow missing

                with cols[col_index % num_columns]:
                    with st.container(border=True): # Add border=True for card visual
                        if plant_data.get("image"):
                            # --- CHANGE HERE ---
                            st.image(plant_data["image"], use_container_width=True) # Use container_width
                            # --- END CHANGE ---
                        st.caption(f"**{nickname}**") # Use caption for nickname

                        if st.button(f"View Details", key=f"view_{nickname}", use_container_width=True):
                            st.session_state.viewing_saved_details = nickname
                            # (rest of the button click logic...)
                            st.rerun()

                col_index += 1

            # --- Display Full Details (if a card's button was clicked) ---
            st.divider() # Separate cards from details view
            nickname_to_view = st.session_state.get("viewing_saved_details")

            if nickname_to_view and nickname_to_view in st.session_state.saved_photos:
                st.subheader(f"Details for '{nickname_to_view}'")
                entry = st.session_state.saved_photos[nickname_to_view]

                # --- Re-use Existing Display Logic ---
                # Display saved ID result
                saved_id_result = entry.get("id_result")
                if saved_id_result:
                     display_identification_result(saved_id_result)
                else:
                     st.info("No identification details saved.")

                # Display care info if it was saved
                saved_care_info = entry.get("care_info")
                if saved_care_info:
                    display_care_instructions(saved_care_info)
                    # Init chat based on THIS saved plant's info for potential interaction
                    # Only reset history/name if viewing a *different* plant than last time
                    if st.session_state.get("current_chatbot_plant_name") != saved_care_info.get("Plant Name"):
                        st.session_state.chat_history = entry.get("chat_log", []) # Restore THIS log
                        st.session_state.current_chatbot_plant_name = saved_care_info.get("Plant Name")

                    # Update the 'current' care info state so chat uses the correct details
                    st.session_state.plant_care_info = saved_care_info
                    display_chat_interface(saved_care_info)
                else:
                    st.info("No specific care instructions were saved for this plant.")
                    # Clear chat if viewing a plant without care info
                    st.session_state.chat_history = []
                    st.session_state.current_chatbot_plant_name = None


                # --- Delete Button for the currently viewed plant ---
                st.divider()
                if st.button(f"🗑️ Delete '{nickname_to_view}' Profile", key=f"del_{nickname_to_view}"):
                     del st.session_state.saved_photos[nickname_to_view]
                     st.session_state.viewing_saved_details = None # Stop viewing details
                     # Clear relevant session state associated with the deleted plant
                     st.session_state.update({k:None for k in ["plant_id_result","plant_care_info","current_chatbot_plant_name","suggestions","uploaded_file_bytes","uploaded_file_type"]});
                     st.session_state.chat_history=[]; st.session_state.saving_mode=False;
                     st.success(f"Deleted '{nickname_to_view}'.")
                     st.rerun() # Refresh card display

            # Add button to go back to viewing all cards from detail view
            elif nickname_to_view:
                 # This case handles if the nickname exists in state but not in saved_photos (e.g., just deleted)
                 st.warning(f"Could not find details for '{nickname_to_view}'. It might have been deleted.")
                 if st.button("Show All Saved Plants"):
                     st.session_state.viewing_saved_details = None
                     st.rerun()

            # Initial message if no details being viewed
            elif not nickname_to_view:
                 st.markdown("Click 'View Details' on a card above to see more information.")

    # Fallback / Welcome message (handled within Identify New Plant section now)
    # Removed the final elif here to avoid the UnboundLocalError definitively


# --- Run the App ---
if __name__ == "__main__":
    if not PLANTNET_API_KEY or not GEMINI_API_KEY: st.error("API Keys missing!"); st.stop()
    main()
