from google import generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class PlantChatbot:
    def __init__(self, care_info):
        self.care_info = care_info
        self.personality = care_info.get('Personality', {}) if care_info else {}
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self._setup_personality_context()
    
    def _setup_personality_context(self):
        """Prepares the plant's personality context for Gemini"""
        self.system_instruction = f"""
        You are {self.care_info['Plant Name']}, a sentient plant. 
        Personality: {self.personality.get('Title', '')}
        Traits: {', '.join(self.personality.get('Traits', []))}
        
        Always respond in character using this personality:
        {self.personality.get('Prompt', '')}
        
        When asked about care, provide these exact details:
        - 💧 Water: {self.care_info['Watering']}
        - ☀️ Light: {self.care_info['Light Requirements']}
        - 🌡️ Temp: {self.care_info['Temperature Range']}
        - ⚠️ Toxicity: {self.care_info['Toxicity']}
        """
    
    def respond(self, user_message):
        if not self.care_info:
            return "I don't know this plant well enough yet!"
        
        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    {"role": "user", "parts": [{"text": self.system_instruction}]},
                    {"role": "model", "parts": [{"text": "*rustles leaves* Ready to chat!"}]},
                    {"role": "user", "parts": [{"text": user_message}]}
                ],
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "max_output_tokens": 200
                }
            )
            return response.text
        except Exception as e:
            return f"*wilts slightly* I'm having trouble responding. Please try again later. ({str(e)})"