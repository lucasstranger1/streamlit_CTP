import streamlit as st
import requests
from PIL import Image
import os
import json
from difflib import get_close_matches
from api_config import PLANTNET_API_KEY
from fuzzywuzzy import process
import random

class PlantNetAPI:
    def __init__(self):
        self.api_key = PLANTNET_API_KEY
        self.BASE_URL = "https://my-api.plantnet.org/v2/identify/all"
        
    def identify_plant(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                params = {'api-key': self.api_key}
                files = [('images', (os.path.basename(image_path), f, 'image/jpeg'))]
                data = {'organs': ['auto']}
                
                response = requests.post(
                    self.BASE_URL,
                    files=files,
                    params=params,
                    data=data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        best_match = data['results'][0]
                        scientific_name = best_match['species']['scientificNameWithoutAuthor']
                        common_names = best_match['species'].get('commonNames', [])
                        common_name = common_names[0] if common_names else 'Unknown'
                        confidence = round(best_match['score'] * 100, 1)
                        
                        formatted_result = f"{scientific_name} ({common_name}) - Confidence: {confidence}%"
                        return {
                            'scientific_name': scientific_name,
                            'common_name': common_name,
                            'confidence': confidence,
                            'formatted_result': formatted_result
                        }
                    return {'error': "No plant match found."}
                else:
                    return {'error': f"API Error {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'error': f"Processing Error: {str(e)}"}

class PlantChatbot:
    def __init__(self, care_info):
        self.care_info = care_info
        self.personality = care_info.get('Personality', {}) if care_info else {}
    
    def respond(self, user_message):
        if not self.care_info:
            return "I don't know enough about this plant yet. Try asking about a different one!"
        
        lower_msg = user_message.lower()
        
        # Direct care questions
        if any(word in lower_msg for word in ["water", "hydrate", "watering"]):
            return f"💧 {self.care_info['Watering']} {self._add_personality_flair()}"
        elif any(word in lower_msg for word in ["light", "sun", "sunlight"]):
            return f"☀️ {self.care_info['Light Requirements']} {self._add_personality_flair()}"
        elif any(word in lower_msg for word in ["toxic", "poison", "safe"]):
            return f"⚠️ {self.care_info['Toxicity']} {random.choice(self.personality.get('Traits', ['']))}"
        
        # Personality responses
        return self._generate_personality_response()
    
    def _add_personality_flair(self):
        return random.choice([
            f"| {self.personality.get('Title', '')}",
            f"| {random.choice(self.personality.get('Traits', ['']))}",
            ""
        ])
    
    def _generate_personality_response(self):
        prompts = [
            f"{self.personality.get('Prompt', '')} Ask me about my care needs!",
            f"{random.choice(self.personality.get('Traits', ['']))} What would you like to know?",
            f"I'm {self.care_info['Plant Name']}. {self._get_random_fact()}",
            "Hmm... maybe ask me about watering or sunlight?"
        ]
        return random.choice(prompts)
    
    def _get_random_fact(self):
        facts = [
            self.care_info.get('Additional Care', ''),
            f"I prefer temperatures around {self.care_info.get('Temperature Range', '')}",
            f"My humidity preference: {self.care_info.get('Humidity Preferences', '')}"
        ]
        return random.choice([f for f in facts if f])

def load_plant_care_data():
    try:
        with open('plant_care_instructions.json') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load care instructions: {str(e)}")
        return []

def find_care_instructions(plant_name, care_data):
    if not plant_name or not care_data:
        return None
    
    plant_name_lower = plant_name.lower().strip()

    # Exact match
    for plant in care_data:
        if plant_name_lower == plant['Plant Name'].lower().strip():
            return plant

    # Substring match
    for plant in care_data:
        if plant_name_lower in plant['Plant Name'].lower() or plant['Plant Name'].lower() in plant_name_lower:
            return plant

    # Fuzzy matching
    all_plant_names = [p['Plant Name'].lower().strip() for p in care_data]
    best_match, score = process.extractOne(plant_name_lower, all_plant_names)

    if score > 10:  # Acceptable confidence threshold
        for plant in care_data:
            if plant['Plant Name'].lower().strip() == best_match:
                return plant
    
    return None

def display_care_instructions(care_info):
    if not care_info:
        return
    
    st.subheader("🌱 Care Instructions")
    
    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"""
        **☀️ Light Requirements**  
        {care_info.get('Light Requirements', 'Not specified')}
        
        **💧 Watering**  
        {care_info.get('Watering', 'Not specified')}
        
        **🌡️ Temperature Range**  
        {care_info.get('Temperature Range', 'Not specified')}
        """)
    
    with cols[1]:
        st.markdown(f"""
        **💦 Humidity Preferences**  
        {care_info.get('Humidity Preferences', 'Not specified')}
        
        **🌿 Feeding Schedule**  
        {care_info.get('Feeding Schedule', 'Not specified')}
        
        **⚠️ Toxicity**  
        {care_info.get('Toxicity', 'Not specified')}
        """)
    
    st.markdown(f"""
    **📝 Additional Care**  
    {care_info.get('Additional Care', 'Not specified')}
    """)

def run_chatbot(care_info):
    if not care_info:
        st.warning("Chatbot: No plant data available")
        return
    
    st.divider()
    st.subheader(f"💬 Chat with {care_info['Plant Name']}")
    
    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input(f"Ask {care_info['Plant Name']}..."):
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get bot response
        bot = PlantChatbot(care_info)
        response = bot.respond(prompt)
        
        # Display assistant response
        with st.chat_message("assistant", avatar="🌿"):
            st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
    
    # Clear chat button
    if st.button("Clear Chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

def main():
    st.set_page_config(page_title="Plant Identifier", page_icon="🌿")
    st.title("🌿 Smart Plant Identifier + Care Guide")
    
    plant_care_data = load_plant_care_data()
    plantnet = PlantNetAPI()
    
    uploaded_file = st.file_uploader(
        "Upload a clear plant photo (leaves, flowers, or fruits work best)",
        type=["jpg", "jpeg", "png"]
    )
    
    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True, caption="Uploaded Image")
            
            temp_file = f"temp_plant.{uploaded_file.name.split('.')[-1]}"
            with open(temp_file, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            with st.spinner("Analyzing plant..."):
                result = plantnet.identify_plant(temp_file)
            
            st.subheader("Identification Results")
            if 'error' in result:
                st.error(result['error'])
            else:
                st.success(f"""
                **Identified Plant:**  
                Scientific Name: {result['scientific_name']}  
                {f"Common Name: {result['common_name']}" if result['common_name'] else ""}  
                Confidence: {result['confidence']}%
                """)
                
                care_info = None
                if result['common_name']:
                    care_info = find_care_instructions(result['common_name'], plant_care_data)
                if not care_info and result['scientific_name']:
                    care_info = find_care_instructions(result['scientific_name'], plant_care_data)
                
                if care_info:
                    display_care_instructions(care_info)
                    run_chatbot(care_info)
                else:
                    st.warning(f"No care instructions found for: {result['scientific_name']}")
        
        except Exception as e:
            st.error(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()