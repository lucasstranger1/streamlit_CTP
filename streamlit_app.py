import streamlit as st
import requests
from PIL import Image
import os

class PlantNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.BASE_URL = "https://my-api.plantnet.org/v2/identify"
        
    def identify_plant(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                # Correct API parameters
                params = {
                    'api-key': self.api_key
                }
                
                # Correct file format with organ type
                files = [
                    ('images', (os.path.basename(image_path), f, 'image/jpeg'))
                ]
                
                # Required data field
                data = {
                    'organs': ['auto']  # Let API detect plant part automatically
                }
                
                response = requests.post(
                    self.BASE_URL,
                    files=files,
                    params=params,
                    data=data
                )
                
                # For debugging
                print("API Response:", response.status_code, response.text)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        best_match = data['results'][0]
                        scientific_name = best_match['species']['scientificNameWithoutAuthor']
                        common_names = best_match['species'].get('commonNames', [])
                        common_name = common_names[0] if common_names else 'Unknown'
                        confidence = round(best_match['score'] * 100, 1)
                        return f"{scientific_name} ({common_name}) - Confidence: {confidence}%"
                    return "No plant match found."
                else:
                    return f"API Error {response.status_code}: {response.text}"
                
        except Exception as e:
            return f"Error: {str(e)}"

def main():
    st.set_page_config(page_title="Plant Identifier", page_icon="🌿")
    st.title("🌿 Plant Identification App")
    
    # Get API key - replace with your actual key
    api_key = st.text_input("Enter your PlantNet API Key", "2b10X3YLMd8PNAuKOCVPt7MeUe")
    
    plantnet = PlantNetAPI(api_key)
    
    uploaded_file = st.file_uploader(
        "Upload a clear plant photo (leaves, flowers, or fruits work best)",
        type=["jpg", "jpeg", "png"]
    )
    
    if uploaded_file and api_key:
        try:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
            
            # Save to temp file
            temp_file = "temp_plant.jpg"
            with open(temp_file, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            with st.spinner("Analyzing plant..."):
                result = plantnet.identify_plant(temp_file)
            
            st.subheader("Results")
            if "Error" in result:
                st.error(result)
                st.info("""
                Troubleshooting tips:
                1. Use a clear, close-up photo of leaves/flowers
                2. Ensure your API key is valid
                3. Check your internet connection
                """)
            else:
                st.success(result)
                
        except Exception as e:
            st.error(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    elif not api_key:
        st.warning("Please enter your PlantNet API key")

if __name__ == "__main__":
    main()