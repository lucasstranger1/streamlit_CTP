import streamlit as st
import requests
from PIL import Image
import os
import json

class PlanNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        # Updated to the correct production API endpoint
        self.BASE_URL = "https://plantnet.org/api/v2/identify"
        
    def identify_plant(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                # PlantNet API v2 expects these parameters
                params = {
                    'api-key': self.api_key,
                    'include-related-images': 'false',
                    'no-reject': 'false',
                    'lang': 'en'
                }
                
                # Correct format for files (must include plant organ type)
                files = [
                    ('images', (os.path.basename(image_path), f, 'image/jpeg'))
                ]
                
                # Add organs parameter (required for v2)
                data = {'organs': ['auto']}
                
                response = requests.post(
                    self.BASE_URL,
                    files=files,
                    params=params,
                    data=data
                )
                
                # For debugging - print the full request
                print(f"Request URL: {response.request.url}")
                print(f"Request Headers: {response.request.headers}")
                print(f"Response Status: {response.status_code}")
                print(f"Response Body: {response.text}")
                
                response.raise_for_status()
                data = response.json()
                
                if data.get('results'):
                    best_match = data['results'][0]
                    scientific_name = best_match['species']['scientificNameWithoutAuthor']
                    common_names = best_match['species'].get('commonNames', [])
                    common_name = common_names[0] if common_names else 'Unknown'
                    confidence = round(best_match['score'] * 100, 1)
                    return f"{scientific_name} ({common_name}) - Confidence: {confidence}%"
                return "No plant match found."
                
        except requests.exceptions.HTTPError as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Processing Error: {str(e)}"

def main():
    st.set_page_config(page_title="Plant Identifier", page_icon="🌿")
    st.title("🌿 Plant Identification App")
    st.write("Upload an image of a plant to identify its species")
    
    # Get API key - use st.secrets for production
    api_key = "2b10X3YLMd8PNAuKOCVPt7MeUe"  # Replace with your actual key
    
    plantnet = PlanNetAPI(api_key)
    
    uploaded_file = st.file_uploader(
        "Choose a plant image", 
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            st.image(
                image, 
                caption="Uploaded Image", 
                use_container_width=True
            )
            
            # Save to temp file with proper extension
            temp_file = f"temp_plant.{uploaded_file.name.split('.')[-1]}"
            with open(temp_file, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            with st.spinner("Identifying plant..."):
                result = plantnet.identify_plant(temp_file)
            
            st.subheader("Identification Result")
            if "Error" in result:
                st.error(result)
                st.info("Make sure your image clearly shows leaves, flowers, or fruits")
            else:
                st.success(f"**Identified Plant:** {result}")
                st.markdown("---")
                st.write("ℹ️ Tips for better results:")
                st.markdown("- Take clear, close-up photos of plant parts")
                st.markdown("- Ensure good lighting and focus")
                st.markdown("- Avoid images with multiple plants")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()