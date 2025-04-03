import streamlit as st
import requests
from PIL import Image
import os

# PlantNet API class embedded directly in the app
class PlanNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        # Updated to the correct PlantNet API endpoint
        self.BASE_URL = "https://my-api.plantnet.org/v2/identify/all"
        
    def identify_plant(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                files = {'images': f}
                params = {
                    'api-key': self.api_key,
                    'organs': 'auto'  # Let PlantNet detect plant parts automatically
                }
                
                response = requests.post(self.BASE_URL, files=files, params=params)
                response.raise_for_status()  # Raises exception for 4XX/5XX errors
                
                data = response.json()
                
                if data.get('results'):
                    # Get the best match (first result)
                    best_match = data['results'][0]
                    scientific_name = best_match['species']['scientificNameWithoutAuthor']
                    common_name = best_match['species'].get('commonNames', ['Unknown'])[0]
                    return f"{scientific_name} ({common_name})"
                return "No plant match found."
                
        except requests.exceptions.RequestException as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Processing Error: {str(e)}"

# Streamlit App UI
def main():
    st.set_page_config(page_title="Plant Identifier", page_icon="🌿")
    st.title("🌿 Plant Identification App")
    st.write("Upload an image of a plant to identify its species")
    
    # Get API key (you can hardcode this if preferred)
    api_key = st.secrets.get("PLANTNET_API_KEY", "2b10X3YLMd8PNAuKOCVPt7MeUe")
    
    # Initialize API
    plantnet = PlanNetAPI(api_key)
    
    # Image upload
    uploaded_file = st.file_uploader(
        "Choose a plant image", 
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        try:
            # Display image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            
            # Save temp file
            temp_file = "temp_plant.jpg"
            with open(temp_file, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Process image
            with st.spinner("Identifying plant..."):
                result = plantnet.identify_plant(temp_file)
            
            # Show results
            st.subheader("Identification Result")
            if "Error" in result:
                st.error(result)
            else:
                st.success(f"**Identified Plant:** {result}")
                
                # Add some additional styling
                st.markdown("---")
                st.write("ℹ️ For more accurate results:")
                st.markdown("- Take clear photos of leaves, flowers, or fruits")
                st.markdown("- Ensure the plant is centered in the image")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()