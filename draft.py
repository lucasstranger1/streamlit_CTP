import streamlit as st
import requests
from PIL import Image
import os

class PlantNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        # Updated to the current correct endpoint (as of July 2024)
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

def main():
    st.set_page_config(page_title="Plant Identifier", page_icon="🌿")
    st.title("🌿 Plant Identification App")
    
    # Get API key - replace with your actual key from https://my.plantnet.org/
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
            
            st.subheader("Results")
            if "Error" in result:
                st.error(result)
                st.markdown("""
                **Troubleshooting Tips:**
                - Use a clear, close-up photo of leaves/flowers
                - Ensure your API key is valid and not expired
                - Try a different plant image
                - Check [PlantNet Status](https://status.plantnet.org/) for API outages
                """)
            else:
                st.success(result)
                st.balloons()
                
        except Exception as e:
            st.error(f"Error processing image: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    main()