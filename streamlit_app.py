import streamlit as st
import requests
from PIL import Image
import os
import json
from difflib import get_close_matches
from api_config import PLANTNET_API_KEY  # Import API key from separate file
from fuzzywuzzy import process



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
    
    **🌟 Personality: {care_info.get('Personality', {}).get('Title', 'Not specified')}**
    
    **Traits:**  
    {' - '.join(care_info.get('Personality', {}).get('Traits', []))}
    
    **🌿 Plant's Story:**  
    {care_info.get('Personality', {}).get('Prompt', 'Not specified')}
    """)

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
                else:
                    st.warning(f"No care instructions found for: {result['scientific_name']}")
        
        except Exception as e:
            st.error(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()
