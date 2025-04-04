import streamlit as st
from gemini_plant_chat import GeminiPlantChat
import json
import os
from PIL import Image
import random

# Load plant data
def load_plant_data():
    with open('plant_care_instructions.json') as f:
        return json.load(f)

# Initialize session state
if "plant_chat" not in st.session_state:
    st.session_state.plant_chat = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def main():
    st.set_page_config(page_title="Plant Personality Chat", page_icon="🌿")
    st.title("🌿 Chat with Your Plant")
    
    plant_data = load_plant_data()
    
    # Plant selection (replace with your image identification logic)
    selected_plant = st.selectbox(
        "Select your plant:",
        [p["Plant Name"] for p in plant_data],
        index=None
    )
    
    if selected_plant:
        care_info = next(p for p in plant_data if p["Plant Name"] == selected_plant)
        
        # Initialize chatbot
        if st.session_state.plant_chat is None or st.session_state.plant_chat.plant["Plant Name"] != selected_plant:
            st.session_state.plant_chat = GeminiPlantChat(care_info)
            st.session_state.chat_history = [
                {"role": "assistant", "content": st.session_state.plant_chat._get_greeting()}
            ]
        
        # Display care info
        with st.expander(f"🔍 {selected_plant} Care Guide"):
            st.write(f"💧 **Watering:** {care_info['Watering']}")
            st.write(f"☀️ **Light:** {care_info['Light Requirements']}")
            st.write(f"🌡️ **Temperature:** {care_info['Temperature Range']}")
            st.write(f"⚠️ **Toxicity:** {care_info['Toxicity']}")
        
        # Chat interface
        st.divider()
        st.subheader(f"💬 Chat with {selected_plant}")
        
        # Display chat history
        for msg in st.session_state.chat_history:
            avatar = "🌿" if msg["role"] == "assistant" else None
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])
        
        # User input
        if prompt := st.chat_input(f"Ask {selected_plant}..."):
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # Get bot response
            response = st.session_state.plant_chat.send_message(prompt)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            # Rerun to update
            st.rerun()
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.chat_history = [
                {"role": "assistant", "content": st.session_state.plant_chat._get_greeting()}
            ]
            st.rerun()

if __name__ == "__main__":
    main()