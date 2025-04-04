import streamlit as st
import requests
from PIL import Image
import os
import json

class PlantNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
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
                        return {
                            'scientific_name': scientific_name,
                            'common_name': common_name,
                            'confidence': confidence
                        }
                    return {'error': "No plant match found."}
                else:
                    return {'error': f"API Error {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'error': f"Processing Error: {str(e)}"}

def load_plant_care_data():
    with open('plant_care_instructions.json') as f:
        return json.load(f)

def find_care_instructions(plant_name, care_data):
    plant_name_lower = plant_name.lower()
    for plant in care_data:
        if plant_name_lower in plant['Plant Name'].lower():
            return plant
    return None

def main():
    st.set_page_config(page_title="Plant Identifier", page_icon="🌿")
    st.title("🌿 Smart Plant Identifier + Care Guide")
    
    # Load plant care data
    plant_care_data = load_plant_care_data()
    
    # Get API key
    api_key = st.text_input("Enter your PlantNet API Key", type="password")
    
    if not api_key or api_key == "your-api-key-here":
        st.warning("Please enter a valid PlantNet API key")
        st.markdown("[Get your API key](https://my.plantnet.org/)")
        return
    
    plantnet = PlantNetAPI(api_key)
    
    uploaded_file = st.file_uploader(
        "Upload a clear plant photo (leaves, flowers, or fruits work best)",
        type=["jpg", "jpeg", "png"]
    )
    
    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True, caption="Uploaded Image")
            
            # Save to temp file
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
                Common Name: {result['common_name']}  
                Confidence: {result['confidence']}%
                """)
                
                # Find care instructions
                care_info = find_care_instructions(result['common_name'], plant_care_data) or \
                          find_care_instructions(result['scientific_name'], plant_care_data)
                
                if care_info:
                    st.subheader("🌱 Care Instructions")
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"""
                        **☀️ Light Requirements**  
                        {care_info['Light Requirements']}
                        
                        **💧 Watering**  
                        {care_info['Watering']}
                        
                        **🌡️ Temperature Range**  
                        {care_info['Temperature Range']}
                        """)
                    with cols[1]:
                        st.markdown(f"""
                        **💦 Humidity Preferences**  
                        {care_info['Humidity Preferences']}
                        
                        **🌿 Feeding Schedule**  
                        {care_info['Feeding Schedule']}
                        
                        **⚠️ Toxicity**  
                        {care_info['Toxicity']}
                        """)
                    st.markdown(f"""
                    **📝 Additional Care**  
                    {care_info['Additional Care']}
                    """)
                else:
                    st.warning("No care instructions found for this plant.")
                
        except Exception as e:
            st.error(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()