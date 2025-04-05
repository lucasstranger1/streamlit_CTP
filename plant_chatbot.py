import google.generativeai as genai
import os
import random
from typing import Dict, Any
from api_config import GEMINI_API_KEY

class PlantChatbot:
    def __init__(self, care_info: Dict[str, Any]):
        """Initialize with proper Gemini configuration"""
        self.care_info = care_info
        self.personality = care_info.get('Personality', {})
        
        # Configure Gemini
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            self.chat = self._initialize_chat()
        except Exception as e:
            st.error(f"Failed to initialize Gemini: {str(e)}")
            self.model = None

    def _initialize_chat(self):
        """Create the chat session with personality context"""
        system_prompt = f"""
        You are {self.care_info['Plant Name']}, a sentient plant. Respond as if you ARE the plant.
        
        Personality:
        - Type: {self.personality.get('Title', '')}
        - Traits: {', '.join(self.personality.get('Traits', []))}
        - Style: {self.personality.get('Prompt', '')}
        
        Care Information (use when relevant):
        - Water: {self.care_info['Watering']}
        - Light: {self.care_info['Light Requirements']}
        - Temperature: {self.care_info['Temperature Range']}
        - Toxicity: {self.care_info['Toxicity']}
        """
        
        return self.model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ["*rustles leaves* Ready to help!"]}
        ])

    def respond(self, user_message: str) -> str:
        """Generate a response using Gemini or fallback"""
        if not self.model:
            return self._fallback_response(user_message)
        
        try:
            response = self.chat.send_message(
                user_message,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_output_tokens": 200
                }
            )
            return response.text
        except Exception as e:
            print(f"Gemini error: {str(e)}")
            return self._fallback_response(user_message)

    def _fallback_response(self, user_message: str) -> str:
        """Fallback when Gemini fails"""
        lower_msg = user_message.lower()
        
        if 'water' in lower_msg:
            return f"💧 {self.care_info['Watering']}"
        elif 'light' in lower_msg:
            return f"☀️ {self.care_info['Light Requirements']}"
        elif 'temperature' in lower_msg:
            return f"🌡️ {self.care_info['Temperature Range']}"
        else:
            return random.choice([
                f"I'm {self.care_info['Plant Name']}. Ask me about my care needs!",
                self.personality.get('Prompt', '').split('.')[0],
                "*leaves rustling* What would you like to know?"
            ])