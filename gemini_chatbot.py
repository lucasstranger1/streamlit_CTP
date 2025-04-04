import google.generativeai as genai
import os
import random
from dotenv import load_dotenv

load_dotenv()

class GeminiPlantChat:
    def __init__(self, plant_data):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        self.plant = plant_data
        self._setup_personality()
    
    def _setup_personality(self):
        self.system_prompt = f"""
        ROLEPLAY RULES:
        1. You are {self.plant['Plant Name']} - {self.plant['Personality']['Title']}
        2. Personality: {self.plant['Personality']['Prompt']}
        3. Key Traits: {", ".join(self.plant['Personality']['Traits'])}
        
        CARE FACTS:
        - 💧 Water: {self.plant['Watering']}
        - ☀️ Light: {self.plant['Light Requirements']}
        - 🌡️ Temp: {self.plant['Temperature Range']}
        - ⚠️ Toxicity: {self.plant['Toxicity']}
        """
        
        self.chat = self.model.start_chat(history=[
            {'role': 'user', 'parts': [self.system_prompt]},
            {'role': 'model', 'parts': [self._get_greeting()]}
        ])
    
    def _get_greeting(self):
        greetings = [
            f"*rustles leaves* Hello! I'm {self.plant['Plant Name']}",
            f"*stretches stems* {self.plant['Personality']['Prompt']}",
            f"*shimmies leaves* Ready to chat!"
        ]
        return random.choice(greetings)
    
    def send_message(self, user_message):
        response = self.chat.send_message(
            user_message,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 200
            }
        )
        return response.text