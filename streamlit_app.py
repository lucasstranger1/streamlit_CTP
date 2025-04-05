import streamlit as st
from PIL import Image
import os
import json
import tempfile
from fuzzywuzzy import process
from plant_net import PlantNetAPI
from plant_chatbot import PlantChatbot
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="Plant Identifier",
        page_icon="🌿",
        layout="centered"
    )
    
    st.title("🌿 Plant Identifier")
    st.write("Upload a plant photo to get care information")

    # Initialize services
    plant_care_data = load_plant_care_data()
    plantnet = PlantNetAPI(os.getenv("PLANTNET_API_KEY"))

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a plant image",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        process_uploaded_image(uploaded_file, plantnet, plant_care_data)

def load_plant_care_data():
    """Load plant care instructions from JSON file."""
    try:
        with open('plant_care_instructions.json') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load care instructions: {str(e)}")
        return []

def process_uploaded_image(uploaded_file, plantnet, plant_care_data):
    """Handle the image upload and processing."""
    try:
        with st.spinner("Analyzing..."):
            # Display image in one column
            col1, col2 = st.columns([1, 2])
            
            with col1:
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True)

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_path = tmp.name

            # Identify plant
            result = plantnet.identify_plant(temp_path)
            
            with col2:
                if 'error' in result:
                    st.error(result['error'])
                    return

                # Show identification results
                st.subheader("Results")
                st.write(f"**Scientific Name:** {result.get('scientific_name', 'Unknown')}")
                st.write(f"**Common Name:** {result.get('common_name', 'Unknown')}")
                st.write(f"**Confidence:** {result.get('confidence', 0)}%")

                # Find and show care instructions
                care_info = find_care_instructions(result, plant_care_data)
                if care_info:
                    show_care_instructions(care_info)
                else:
                    st.warning("No care info found")
                    suggest_similar_plants(result, plant_care_data)

    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

def find_care_instructions(result, care_data):
    """Find care instructions for the identified plant."""
    if not result or not care_data:
        return None
    
    # Try scientific name first
    for name in [result.get('scientific_name'), result.get('common_name')]:
        if not name:
            continue
            
        name_lower = name.lower().strip()
        for plant in care_data:
            if name_lower == plant.get('Plant Name', '').lower().strip():
                return plant
    
    return None

def show_care_instructions(care_info):
    """Display care instructions simply."""
    st.subheader(f"Care Guide for {care_info['Plant Name']}")
    
    st.write("**Light:**", care_info.get('Light Requirements', 'Not specified'))
    st.write("**Water:**", care_info.get('Watering', 'Not specified'))
    st.write("**Temperature:**", care_info.get('Temperature Range', 'Not specified'))
    st.write("**Humidity:**", care_info.get('Humidity Preferences', 'Not specified'))
    st.write("**Feeding:**", care_info.get('Feeding Schedule', 'Not specified'))
    st.write("**Toxicity:**", care_info.get('Toxicity', 'Not specified'))
    
    if care_info.get('Additional Care'):
        st.write("**Notes:**", care_info['Additional Care'])
    
    # Initialize simple chatbot
    initialize_simple_chatbot(care_info)

def suggest_similar_plants(result, plant_care_data):
    """Show similar plants simply."""
    st.write("Similar plants:")
    
    # Simple list display
    for plant in plant_care_data[:3]:  # Just show first 3 as examples
        st.write(f"- {plant.get('Plant Name', 'Unknown')}")

def initialize_simple_chatbot(care_info):
    """Simplified chat interface"""
    st.divider()
    st.write(f"Ask {care_info['Plant Name']} questions:")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for msg in st.session_state.messages:
        role = "👤 You" if msg["role"] == "user" else f"🌿 {care_info['Plant Name']}"
        st.write(f"{role}: {msg['content']}")
    
    # Chat input
    if prompt := st.text_input("Type your question", key="chat_input"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get bot response
        bot = PlantChatbot(care_info)
        response = bot.respond(prompt)
        
        # Add bot response
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update
        st.rerun()
    
    # Clear button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()