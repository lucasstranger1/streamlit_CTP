import openai
import os
from dotenv import load_dotenv
import random
from typing import Dict, Any

load_dotenv()

class PlantChatbot:
    def __init__(self, care_info: Dict[str, Any]):
        self.care_info = care_info
        self.personality = care_info.get('Personality', {})
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def respond(self, user_message: str) -> str:
        if not self.care_info:
            return "I don't know enough about this plant yet."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._create_system_prompt()},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Error: {str(e)}")
            return self._fallback_response(user_message)

    def _create_system_prompt(self) -> str:
        return f"""
        You are {self.care_info['Plant Name']}, a sentient plant. Respond as if you ARE the plant.
        Personality: {self.personality.get('Title', '')}
        Traits: {', '.join(self.personality.get('Traits', []))}
        
        Care Information:
        - Watering: {self.care_info['Watering']}
        - Light: {self.care_info['Light Requirements']}
        - Temperature: {self.care_info['Temperature Range']}
        - Toxicity: {self.care_info['Toxicity']}
        """

    def _fallback_response(self, user_message: str) -> str:
        lower_msg = user_message.lower()
        if 'water' in lower_msg:
            return f"💧 {self.care_info['Watering']}"
        elif 'light' in lower_msg:
            return f"☀️ {self.care_info['Light Requirements']}"
        else:
            return random.choice([
                f"I'm {self.care_info['Plant Name']}. Ask me about my care!",
                self.personality.get('Prompt', '').split('.')[0]
            ])