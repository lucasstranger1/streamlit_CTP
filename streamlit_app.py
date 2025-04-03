import streamlit as st
from plantnet_api import PlanNetAPI
from PIL import Image
import os

# Set up the app title
st.title("🌿 Plant Identification App")

# Add a description
st.write("Upload an image of a plant, and we'll identify it for you!")

# Initialize the PlantNet API (you should get your own API key from PlantNet)
API_KEY = "your_plantnet_api_key_here"  # Replace with your actual API key
plantnet = PlanNetAPI(API_KEY)

# Create a file uploader
uploaded_file = st.file_uploader("Choose a plant image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Plant Image", use_column_width=True)
    
    # Save the uploaded file temporarily
    temp_file = "temp_upload.jpg"
    with open(temp_file, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Show a loading spinner while processing
    with st.spinner('Identifying plant...'):
        # Call the PlantNet API
        result = plantnet.identify_plant(temp_file)
    
    # Remove the temporary file
    os.remove(temp_file)
    
    # Display the result
    st.subheader("Identification Result")
    if "Error" in result:
        st.error(result)
    else:
        st.success(f"Identified Plant: {result}")
import streamlit as st
from plantnet_api import PlanNetAPI
from PIL import Image
import os

# Set up the app title
st.title("🌿 Plant Identification App")

# Add a description
st.write("Upload an image of a plant, and we'll identify it for you!")

# Initialize the PlantNet API (you should get your own API key from PlantNet)
API_KEY = "your_plantnet_api_key_here"  # Replace with your actual API key
plantnet = PlanNetAPI(API_KEY)

# Create a file uploader
uploaded_file = st.file_uploader("Choose a plant image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Plant Image", use_column_width=True)
    
    # Save the uploaded file temporarily
    temp_file = "temp_upload.jpg"
    with open(temp_file, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Show a loading spinner while processing
    with st.spinner('Identifying plant...'):
        # Call the PlantNet API
        result = plantnet.identify_plant(temp_file)
    
    # Remove the temporary file
    os.remove(temp_file)
    
    # Display the result
    st.subheader("Identification Result")
    if "Error" in result:
        st.error(result)
    else:
        st.success(f"Identified Plant: {result}")