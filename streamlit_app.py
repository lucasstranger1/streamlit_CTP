import streamlit as st
from PIL import Image
import os
import json
import tempfile
from plant_chatbot import PlantChatbot
from plant_net import PlantNetAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="Plant Identifier", 
        page_icon="🌿",
        layout="centered"
    )
    
    st.title("🌿 Smart Plant Identifier + Care Guide")
    st.markdown("Upload a clear photo of your plant to get care instructions and chat with it!")
    
    # Initialize services
    plant_care_data = load_plant_care_data()
    plantnet = PlantNetAPI(os.getenv("PLANTNET_API_KEY"))
    
    # File upload section
    with st.expander("📤 Upload Plant Photo", expanded=True):
        uploaded_file = st.file_uploader(
            "Choose an image (leaves, flowers, or fruits work best)",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )
    
    if uploaded_file:
        process_plant_photo(uploaded_file, plantnet, plant_care_data)
    
    # Sidebar with additional info
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This app helps you:
        - Identify unknown plants
        - Get personalized care instructions
        - Chat with your plant's personality
        
        Works best with clear photos of:
        - Leaves (top and underside)
        - Flowers or fruits
        - Whole plant when possible
        """)

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

def process_plant_photo(uploaded_file, plantnet, plant_care_data):
    """Handle the plant photo processing pipeline."""
    try:
        # Display uploaded image
        with st.spinner("Processing your plant..."):
            col1, col2 = st.columns([1, 2])
            with col1:
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True, caption="Your Plant")
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_path = tmp.name
            
            # Identify plant
            result = plantnet.identify_plant(temp_path)
            
            if 'error' in result:
                st.error(result['error'])
                return
            
            with col2:
                display_identification_results(result)
                care_info = find_care_instructions(result, plant_care_data)
                
                if care_info and validate_care_info(care_info):
                    display_care_instructions(care_info)
                    initialize_chatbot(care_info)
                else:
                    st.warning("No complete care instructions found for this plant")
                    suggest_similar_plants(result.get('scientific_name', ''), plant_care_data)
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

def validate_care_info(care_info: dict) -> bool:
    """Check if care info has required fields."""
    required_fields = [
        'Plant Name', 
        'Light Requirements',
        'Watering',
        'Temperature Range',
        'Toxicity'
    ]
    return all(field in care_info for field in required_fields)

def display_identification_results(result):
    """Show plant identification results."""
    st.subheader("🔍 Identification Results")
    
    confidence = result.get('confidence', 0)
    confidence_color = (
        "green" if confidence > 80 
        else "orange" if confidence > 50 
        else "red"
    )
    
    st.markdown(f"""
    - 🧪 **Scientific Name**: `{result.get('scientific_name', 'Unknown')}`
    - 🌎 **Common Name**: `{result.get('common_name', 'Unknown')}`
    - 🎯 **Confidence**: <span style='color:{confidence_color}'>{confidence}%</span>
    """, unsafe_allow_html=True)

def find_care_instructions(result, plant_care_data):
    """Match identified plant with care instructions."""
    # Try common name first
    if result.get('common_name'):
        care_info = search_care_data(result['common_name'], plant_care_data)
        if care_info:
            return care_info
    
    # Fall back to scientific name
    return search_care_data(result.get('scientific_name', ''), plant_care_data)

def search_care_data(plant_name, plant_care_data):
    """Search for plant in care data with flexible matching."""
    if not plant_name or not plant_care_data:
        return None
    
    plant_name_lower = plant_name.lower().strip()
    
    # Exact match
    for plant in plant_care_data:
        if plant_name_lower == plant.get('Plant Name', '').lower().strip():
            return plant
    
    # Partial match
    for plant in plant_care_data:
        if plant_name_lower in plant.get('Plant Name', '').lower():
            return plant
    
    return None

def display_care_instructions(care_info):
    """Display plant care information in an organized layout."""
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

def initialize_chatbot(care_info):
    """Set up and manage the chatbot interface."""
    st.divider()
    st.subheader(f"💬 Chat with {care_info['Plant Name']}")
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.plant_chatbot = PlantChatbot(care_info)
    
    # Display chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input(f"Ask {care_info['Plant Name']}..."):
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get bot response
        bot_response = st.session_state.plant_chatbot.respond(prompt)
        
        # Display bot response
        with st.chat_message("assistant", avatar="🌿"):
            st.markdown(bot_response)
        
        # Add bot response to history
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
    
    # Clear chat button
    if st.session_state.chat_history and st.button("Clear Chat", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

def suggest_similar_plants(scientific_name, plant_care_data):
    """Suggest similar plants when exact match isn't found."""
    if not scientific_name or not plant_care_data:
        return
    
    st.info("Try these similar plants:")
    similar_plants = [
        p for p in plant_care_data 
        if isinstance(p, dict) and 
        any(word in p.get('Plant Name', '').lower() 
        for word in scientific_name.lower().split()[:2])
    ][:3]
    
    for plant in similar_plants:
        with st.expander(f"🌿 {plant.get('Plant Name', 'Unknown')}"):
            st.markdown(f"**Light:** {plant.get('Light Requirements', 'Not specified')}")
            st.markdown(f"**Water:** {plant.get('Watering', 'Not specified')}")

if __name__ == "__main__":
    main()