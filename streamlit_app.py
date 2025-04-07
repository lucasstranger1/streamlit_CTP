import streamlit as st
from PIL import Image
import os
import json
import tempfile
from fuzzywuzzy import process
from plant_net import PlantNetAPI
from plant_chatbot import PlantChatbot
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from datetime import timezone
import pytz
# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="Plant Identifier",
        page_icon="🌿",
        layout="centered"
    )
    
    st.title("🌿 Smart Plant Identifier")
    st.markdown("Upload a plant photo to get care instructions and chat with your plant!")

    # Initialize services
    plant_care_data = load_plant_care_data()
    plantnet = PlantNetAPI(os.getenv("PLANTNET_API_KEY"))

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a plant image (leaves, flowers, or fruits work best)",
        type=["jpg", "jpeg", "png"],
        key="plant_uploader" # Add a key to help Streamlit track the widget state
    )

    # --- State Management for Selected Plant ---
    # Check if a plant was selected from suggestions in the *previous* run
    if "selected_plant_care_info" in st.session_state:
        selected_care_info = st.session_state.pop("selected_plant_care_info") # Get and remove
        # Display info and initialize chat for the selected plant
        display_care_instructions(selected_care_info)
        initialize_chatbot(selected_care_info) # This will now correctly initialize/reset
        st.stop() # Stop further processing for this run (don't re-process uploaded file)
    # --- End State Management ---


    if uploaded_file is not None:
        # Clear previous selection state if a new file is uploaded
        if "selected_plant_care_info" in st.session_state:
            del st.session_state.selected_plant_care_info

        process_uploaded_image(uploaded_file, plantnet, plant_care_data)


def load_plant_care_data():
    """Load plant care instructions from JSON file."""
    try:
        with open('plant_care_instructions.json') as f:
            data = json.load(f)
            if not isinstance(data, list):
                st.error("Invalid data format in care instructions")
                return []
            return data
    except Exception as e:
        st.error(f"Failed to load care instructions: {str(e)}")
        return []

def process_uploaded_image(uploaded_file, plantnet, plant_care_data):
    """Handle the image upload and processing pipeline."""
    # Display the image first
    try:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True, caption="Your Plant")
    except Exception as e:
        st.error(f"Error opening image: {e}")
        return # Don't proceed if image can't be opened

    # Process the image
    try:
        with st.spinner("Analyzing your plant..."):
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_path = tmp.name

            # Identify plant
            result = plantnet.identify_plant(temp_path)

            # Display results & handle care/chat
            if 'error' in result:
                st.error(f"PlantNet API Error: {result['error']}")
                return

            display_identification_result(result)
            handle_care_instructions(result, plant_care_data) # This function now calls initialize_chatbot

    except Exception as e:
        st.error(f"An error occurred during processing: {str(e)}")
    finally:
        # Ensure temp file is removed
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                st.warning(f"Could not remove temp file {temp_path}: {e}")
def display_identification_result(result):
    """Display the plant identification results."""
    st.subheader("🔍 Identification Results")
    
    confidence = result.get('confidence', 0)
    confidence_color = "green" if confidence > 75 else "orange" if confidence > 50 else "red"
    
    st.markdown(f"""
    - 🧪 **Scientific Name**: `{result.get('scientific_name', 'Unknown')}`
    - 🌎 **Common Name**: `{result.get('common_name', 'Unknown')}`
    - 🎯 **Confidence**: <span style='color:{confidence_color}'>{confidence}%</span>
    """, unsafe_allow_html=True)

def handle_care_instructions(result, plant_care_data):
    """Find care instructions, display them, and initialize chat OR suggest alternatives."""
    plant_name_sci = result.get('scientific_name')
    plant_name_common = result.get('common_name')

    care_info = find_care_instructions(plant_name_sci, plant_care_data)
    if not care_info and plant_name_common:
        care_info = find_care_instructions(plant_name_common, plant_care_data)

    if care_info:
        # Found direct match - display and initialize/reset chat
        display_care_instructions(care_info)
        initialize_chatbot(care_info) # Call the modified function
    else:
        # No direct match found
        st.warning("No complete care instructions found matching the identification.")
        # --- IMPORTANT: Clear any *existing* chat state from a *previous* plant ---
        if "current_chatbot_plant_name" in st.session_state:
            # st.write("DEBUG: Clearing chat state due to no match found.") # Optional debug
            del st.session_state.current_chatbot_plant_name
        if "plant_chatbot" in st.session_state:
            del st.session_state.plant_chatbot
        if "chat_history" in st.session_state:
            del st.session_state.chat_history
        # --- End clearing logic ---

        suggest_similar_plants(result, plant_care_data) # Show suggestions

def find_care_instructions(plant_name, care_data):
    """Find care instructions using exact, partial, and fuzzy matching."""
    if not plant_name or not care_data:
        return None
    
    plant_name_lower = plant_name.lower().strip()

    # 1. Try exact match
    for plant in care_data:
        if plant_name_lower == plant.get('Plant Name', '').lower().strip():
            return plant

    # 2. Try partial matches
    partial_matches = []
    for plant in care_data:
        db_name = plant.get('Plant Name', '').lower()
        if (plant_name_lower in db_name or 
            db_name in plant_name_lower or
            any(word in db_name for word in plant_name_lower.split())):
            partial_matches.append(plant)
    
    if len(partial_matches) == 1:
        return partial_matches[0]

    # 3. Try fuzzy matching
    all_plant_names = []
    plant_map = {}
    for plant in care_data:
        name = plant.get('Plant Name', '').lower().strip()
        if name:
            all_plant_names.append(name)
            plant_map[name] = plant
    
    if all_plant_names:
        best_match, score = process.extractOne(plant_name_lower, all_plant_names)
        if score > 65:  # Only use good matches
            return plant_map.get(best_match)
    
    # 4. Return first partial match if exists
    return partial_matches[0] if partial_matches else None

def display_care_instructions(care_info):
    """Display the care instructions in an organized layout."""
    st.subheader(f"🌱 {care_info['Plant Name']} Care Guide")
    
    with st.expander("📋 Care Summary", expanded=True):
        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"""
            **☀️ Light**  
            {care_info.get('Light Requirements', 'Not specified')}
            
            **💧 Water**  
            {care_info.get('Watering', 'Not specified')}
            
            **🌡️ Temperature**  
            {care_info.get('Temperature Range', 'Not specified')}
            """)
        
        with cols[1]:
            st.markdown(f"""
            **💦 Humidity**  
            {care_info.get('Humidity Preferences', 'Not specified')}
            
            **🍃 Feeding**  
            {care_info.get('Feeding Schedule', 'Not specified')}
            
            **⚠️ Toxicity**  
            {care_info.get('Toxicity', 'Not specified')}
            """)
    
    if care_info.get('Additional Care'):
        with st.expander("✨ Pro Tips"):
            st.markdown(care_info['Additional Care'])

def suggest_similar_plants(result, plant_care_data):
    """Suggest similar plants and allow selection."""
    st.info("🌿 Perhaps one of these is similar?")

    all_plant_names = []
    plant_map = {}
    for plant in plant_care_data:
        name = plant.get('Plant Name', '').strip()
        if name:
            lower_name = name.lower()
            all_plant_names.append(lower_name)
            plant_map[lower_name] = plant

    if not all_plant_names:
        st.warning("No plant names available in care data for suggestions.")
        return

    matches_to_display = []
    processed_names = set() # To avoid duplicates

    # Get matches for scientific name
    if result.get('scientific_name'):
        sci_matches = process.extract(result['scientific_name'].lower(), all_plant_names, limit=3)
        for match, score in sci_matches:
            if score > 50 and match not in processed_names:
                 matches_to_display.append((match, score))
                 processed_names.add(match)

    # Get matches for common name (add if different from scientific matches)
    if result.get('common_name'):
         common_matches = process.extract(result['common_name'].lower(), all_plant_names, limit=3)
         for match, score in common_matches:
             if score > 50 and match not in processed_names and len(matches_to_display) < 3: # Limit total suggestions
                 matches_to_display.append((match, score))
                 processed_names.add(match)

    # Sort by score
    matches_to_display.sort(key=lambda item: item[1], reverse=True)

    if not matches_to_display:
        st.info("Couldn't find any close matches in the care database.")
        return

    # Use display_plant_matches to show buttons
    display_plant_matches(matches_to_display, plant_map)

def display_plant_matches(matches, plant_map):
    """Display matched plants as selectable cards."""
    for match, score in matches:
        if score > 50:  # Only show decent matches
            plant = plant_map.get(match)
            if plant:
                with st.expander(f"🌱 {plant.get('Plant Name', 'Unknown')}"):
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"""
                        **☀️ Light**  
                        {plant.get('Light Requirements', 'Not specified')}
                        
                        **💧 Water**  
                        {plant.get('Watering', 'Not specified')}
                        """)
                    with cols[1]:
                        st.markdown(f"""
                        **🌡️ Temp**  
                        {plant.get('Temperature Range', 'Not specified')}
                        
                        **⚠️ Toxicity**  
                        {plant.get('Toxicity', 'Not specified')}
                        """)
                    
                    if st.button("Select this plant", 
                               key=f"select_{plant.get('Plant Name', '')}"):
                        display_care_instructions(plant)
                        initialize_chatbot(plant)
                        st.rerun()

def initialize_chatbot(care_info):
    """Modern chatbot with proper message containment"""
    new_plant_name = care_info.get("Plant Name", "Unknown Plant")
    st.subheader(f"💬 Chat with {care_info['Plant Name']}")
    # Initialize or Reset if:
    # 1. Chat history doesn't exist OR
    # 2. The new plant name is different from the chatbot's current plant
    current_chatbot_plant = st.session_state.get("current_chatbot_plant_name")

    # # --- Add these lines ---
    # st.info(f"DEBUG: Initializing chat UI for '{new_plant_name}'")
    # st.info(f"DEBUG: Comparing with current state name: '{current_chatbot_plant}'")
    # # --- End Add ---
    if "chat_history" not in st.session_state or current_chatbot_plant != new_plant_name:
        # st.write(f"DEBUG: Resetting chatbot for {new_plant_name}") # Optional debug message
        st.session_state.chat_history = []  # Reset history
        st.session_state.plant_chatbot = PlantChatbot(care_info) # Create new chatbot instance
        st.session_state.current_chatbot_plant_name = new_plant_name # Track the current plant
    # --- END MODIFIED Logic ---

    # Use the name stored in session state for consistency in the UI after initialization
    chatbot_display_name = st.session_state.get("current_chatbot_plant_name", new_plant_name)
    # Custom CSS for chat interface
    st.markdown("""
    <style>
        .user-message {
            background: #0078d4;
            color: white;
            border-radius: 18px 18px 0 18px;
            padding: 10px 16px;
            margin: 8px 0;
            width: fit-content;  /* Adjusts width to content */
            max-width: 90%;      /* Optional: Prevent extreme stretching */
            margin-left: auto;   /* Keeps user messages right-aligned */
            word-wrap: break-word;
            animation: fadeIn 0.3s;
        }

        .bot-message {
            background: #f3f3f3;
            color: #333;
            border-radius: 18px 18px 18px 0;
            padding: 10px 16px;
            margin: 8px 0;
            width: fit-content;  /* Adjusts width to content */
            max-width: 90%;      /* Optional: Prevent extreme stretching */
            word-wrap: break-word;
            animation: fadeIn 0.01s;
        }
        .message-meta {
            font-size: 0.75rem;
            opacity: 0.8;
            margin-top: 4px;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .stChatInput {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            max-width: 800px;
            z-index: 100;
        }
        .stButton>button {
            border-radius: 20px;
            padding: 8px 16px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Chat container - Use a dedicated div for better scrolling control
    with st.container():
        st.markdown('<div class="chat-container" id="chat-window">', unsafe_allow_html=True)
        chat_history = st.session_state.get("chat_history", [])
        if chat_history:
            for message in chat_history:
                role = message.get("role")
                content = message.get("content", "")
                time = message.get("time", "")
                if role == "user":
                    st.markdown(
                        f'<div class="user-message">{content}<div class="message-meta">You • {time}</div></div>',
                        unsafe_allow_html=True
                    )
                elif role == "assistant":
                    st.markdown(
                        f'<div class="bot-message">🌿 {content}<div class="message-meta">{chatbot_display_name} • {time}</div></div>',
                        unsafe_allow_html=True
                    )
        else:
            # Placeholder when chat is empty
            st.markdown(f"<p style='text-align: center; color: grey;'>Start chatting with {chatbot_display_name}!</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Auto-scroll to bottom Javascript (keep your original JS)
    # Note: Might need adjustment if chat-container ID changes or structure differs.
    st.markdown("""
        <script>
            const chatWindow = document.getElementById('chat-window');
            if (chatWindow) {
                 // Scroll down fully
                 chatWindow.scrollTop = chatWindow.scrollHeight;
                 // console.log("Scrolled down"); // Debugging

                 // Optional: Re-scroll on updates (might be slightly delayed)
                  const observer = new MutationObserver(function(mutations) {
                     chatWindow.scrollTop = chatWindow.scrollHeight;
                  });
                  observer.observe(chatWindow, { childList: true });

                  // Disconnect on unload
                  window.addEventListener('beforeunload', () => observer.disconnect());
            }
        </script>
    """, unsafe_allow_html=True)


    # Chat input (positioned at bottom via CSS)
    if prompt := st.chat_input(f"Ask {chatbot_display_name}..."):
        # Ensure chatbot and history are available before adding messages
        if "plant_chatbot" not in st.session_state or "chat_history" not in st.session_state:
            st.error("Chatbot is not initialized properly. Please identify a plant again.")
            st.stop() # Stop execution if state is inconsistent

        eastern = pytz.timezone('US/Eastern')
        timestamp = datetime.now(eastern).strftime("%H:%M")

        # Add user message
        st.session_state.chat_history.append({
            "role": "user", "content": prompt, "time": timestamp
        })

        # Get bot response
        bot_response = st.session_state.plant_chatbot.respond(prompt)

        # Add bot response
        st.session_state.chat_history.append({
            "role": "assistant", "content": bot_response, "time": datetime.now(eastern).strftime("%H:%M")
        })

        # Rerun to update the chat display *immediately*
        st.rerun()

    # Clear button (place it below the input logic)
    # Using columns for potential layout control, though may not be needed with fixed input
    # col1, col2 = st.columns([0.8, 0.2])
    # with col2:
    if st.button("Clear Chat", key="clear_chat_button"): # Use a unique key
        if "chat_history" in st.session_state:
            st.session_state.chat_history = []
            # Decide if clearing chat should also clear the current plant tracking
            # If you want the chat to restart blank *for the same plant*, don't delete the name
            # If you want it fully reset, uncomment below:
            # if "current_chatbot_plant_name" in st.session_state:
            #     del st.session_state.current_chatbot_plant_name
        st.rerun()

if __name__ == "__main__":
    main()