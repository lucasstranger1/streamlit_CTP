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
        layout="wide"  # Changed to wide layout for larger image
    )
    
    st.title("🌿 Plant Identifier")
    st.write("Upload a plant photo to get care information")

    # Initialize services
    plant_care_data = load_plant_care_data()
    plantnet = PlantNetAPI(os.getenv("PLANTNET_API_KEY"))

    # File uploader - centered
    uploaded_file = st.file_uploader(
        "Choose a plant image (leaves, flowers, or fruits work best)",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
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
    try:
        with st.spinner("Analyzing your plant..."):
            # Create two columns - wider for image
            img_col, info_col = st.columns([2, 1])  # 2:1 ratio
            
            with img_col:
                # Display larger image
                image = Image.open(uploaded_file)
                st.image(
                    image,
                    use_column_width=True,
                    caption="Your Plant Photo",
                    width=600  # Larger initial display size
                )

            with info_col:
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    temp_path = tmp.name

                # Identify plant
                result = plantnet.identify_plant(temp_path)
                
                if 'error' in result:
                    st.error(result['error'])
                    return

                display_identification_result(result)
                handle_care_instructions(result, plant_care_data)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

def display_identification_result(result):
    """Display the plant identification results."""
    st.subheader("Identification Results")
    
    confidence = result.get('confidence', 0)
    confidence_color = "green" if confidence > 75 else "orange" if confidence > 50 else "red"
    
    st.write(f"**Scientific Name:** {result.get('scientific_name', 'Unknown')}")
    st.write(f"**Common Name:** {result.get('common_name', 'Unknown')}")
    st.write(f"**Confidence:** <span style='color:{confidence_color}'>{confidence}%</span>", 
             unsafe_allow_html=True)

def handle_care_instructions(result, plant_care_data):
    """Find and display care instructions."""
    care_info = find_care_instructions(result['scientific_name'], plant_care_data)
    if not care_info and result.get('common_name'):
        care_info = find_care_instructions(result['common_name'], plant_care_data)

    if care_info:
        display_care_instructions(care_info)
        initialize_chatbot(care_info)
    else:
        st.warning("No complete care instructions found for this plant")
        suggest_similar_plants(result, plant_care_data)

def find_care_instructions(plant_name, care_data):
    """Find care instructions using matching."""
    if not plant_name or not care_data:
        return None
    
    plant_name_lower = plant_name.lower().strip()
    
    # Try exact match first
    for plant in care_data:
        if plant_name_lower == plant.get('Plant Name', '').lower().strip():
            return plant
    
    # Then try partial matches
    partial_matches = []
    for plant in care_data:
        db_name = plant.get('Plant Name', '').lower()
        if plant_name_lower in db_name or db_name in plant_name_lower:
            partial_matches.append(plant)
    
    return partial_matches[0] if partial_matches else None

def display_care_instructions(care_info):
    """Display care instructions simply."""
    st.subheader(f"Care Guide: {care_info['Plant Name']}")
    
    st.write("**Light Requirements:**", care_info.get('Light Requirements', 'Not specified'))
    st.write("**Watering:**", care_info.get('Watering', 'Not specified'))
    st.write("**Temperature Range:**", care_info.get('Temperature Range', 'Not specified'))
    st.write("**Humidity Preferences:**", care_info.get('Humidity Preferences', 'Not specified'))
    st.write("**Feeding Schedule:**", care_info.get('Feeding Schedule', 'Not specified'))
    st.write("**Toxicity:**", care_info.get('Toxicity', 'Not specified'))
    
    if care_info.get('Additional Care'):
        st.write("**Additional Care:**", care_info['Additional Care'])

def suggest_similar_plants(result, plant_care_data):
    """Show similar plants simply."""
    st.info("Similar plants you might consider:")
    
    # Show first 3 plants as examples
    for plant in plant_care_data[:3]:
        st.write(f"- {plant.get('Plant Name', 'Unknown')}")

def initialize_chatbot(care_info):
    """Simple chat interface without complex styling"""
    st.divider()
    st.subheader(f"Chat with {care_info['Plant Name']}")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**{care_info['Plant Name']}:** {msg['content']}")
    
    # Chat input
    if prompt := st.text_input("Type your question", key="chat_input"):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "time": datetime.now().strftime("%H:%M")
        })
        
        # Get bot response
        bot = PlantChatbot(care_info)
        response = bot.respond(prompt)
        
        # Add bot response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "time": datetime.now().strftime("%H:%M")
        })
        
        # Rerun to update
        st.rerun()
    
    # Clear button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()