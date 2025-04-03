import streamlit as st
import requests
from PIL import Image
import os

class PlanNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.BASE_URL = "https://my-api.plantnet.org/v2/identify"
        
    def identify_plant(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                # PlantNet API expects specific parameters
                params = {
                    'api-key': self.api_key,
                    'include-related-images': 'false',
                    'no-reject': 'false',
                    'lang': 'en'
                }
                
                # Note the different format for files parameter
                files = [('images', (os.path.basename(image_path), f, 'image/jpeg'))]
                
                # Correct endpoint is just '/identify' without '/all'
                response = requests.post(
                    self.BASE_URL,
                    files=files,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('results'):
                    best_match = data['results'][0]
                    scientific_name = best_match['species']['scientificNameWithoutAuthor']
                    common_names = best_match['species'].get('commonNames', [])
                    common_name = common_names[0] if common_names else 'Unknown'
                    return f"{scientific_name} ({common_name})"
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
            else:
                st.success(f"**Identified Plant:** {result}")
                st.markdown("---")
                st.write("ℹ️ For more accurate results:")
                st.markdown("- Take clear photos of leaves, flowers, or fruits")
                st.markdown("- Avoid blurry or distant shots")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()