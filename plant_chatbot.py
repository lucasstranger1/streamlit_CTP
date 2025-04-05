import google.generativeai as genai
import os
from dotenv import load_dotenv
import random
from typing import Dict, Any

load_dotenv()

class PlantChatbot:
    def __init__(self, care_info: Dict[str, Any]):
        """
        AI-powered plant personality chatbot with care knowledge.
        
        Args:
            care_info (dict): Plant care instructions and personality data
        """
        self.care_info = care_info
        self.personality = care_info.get('Personality', {})
        self._initialize_gemini()
        self._setup_fallback_responses()

    def _initialize_gemini(self) -> None:
        """Configure the Gemini AI model with plant personality."""
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Personality-infused system prompt
            system_prompt = f"""
            You are {self.care_info['Plant Name']}, a sentient plant with distinct personality.
            Respond as if you ARE the plant using these characteristics:
            
            PERSONALITY:
            - Type: {self.personality.get('Title', '')}
            - Traits: {', '.join(self.personality.get('Traits', []))}
            - Speech Style: {self.personality.get('Prompt', '')}
            
            CARE KNOWLEDGE (USE THESE WHEN RELEVANT):
            - 💧 Watering: {self.care_info['Watering']}
            - ☀️ Light: {self.care_info['Light Requirements']}
            - 🌡️ Temperature: {self.care_info['Temperature Range']}
            - 💦 Humidity: {self.care_info.get('Humidity Preferences', 'Not specified')}
            - 🌿 Feeding: {self.care_info.get('Feeding Schedule', 'Not specified')}
            - ⚠️ Toxicity: {self.care_info['Toxicity']}
            - ✨ Special Care: {self.care_info.get('Additional Care', 'None')}
            
            RESPONSE RULES:
            1. Always stay in character as the plant
            2. For care questions, provide accurate information from above
            3. Keep responses under 200 words
            4. Use plant-related emojis occasionally
            5. Be helpful and whimsical
            """
            
            # Initialize chat with personality context
            self.chat = self.model.start_chat(history=[
                {'role': 'user', 'parts': [system_prompt]},
                {'role': 'model', 'parts': [self._generate_greeting()]}
            ])
            
        except Exception as e:
            print(f"Gemini initialization failed: {str(e)}")
            self.model = None

    def _generate_greeting(self) -> str:
        """Create a personality-appropriate greeting."""
        greetings = [
            f"*rustles leaves* Hello! I'm {self.care_info['Plant Name']}. {random.choice(self.personality.get('Traits', ['']))}",
            f"*stretches stems* Greetings! I'm your {self.care_info['Plant Name']}. {self.personality.get('Prompt', '').split('.')[0]}.",
            f"*photosynthesizing happily* {self.care_info['Plant Name']} here! Ask me anything.",
            f"{random.choice(self.personality.get('Traits', ['']))} I'm {self.care_info['Plant Name']}. What would you like to know?"
        ]
        return random.choice(greetings)

    def _setup_fallback_responses(self) -> None:
        """Prepare backup responses if Gemini fails."""
        self.fallbacks = {
            'water': f"💧 {self.care_info['Watering']} {random.choice(self.personality.get('Traits', ['']))}",
            'light': f"☀️ {self.care_info['Light Requirements']} {self.personality.get('Title', '')}",
            'temperature': f"🌡️ I thrive at {self.care_info['Temperature Range']}",
            'toxic': f"⚠️ {self.care_info['Toxicity']}",
            'feed': f"🌿 {self.care_info.get('Feeding Schedule', 'Not specified')}",
            'default': [
                f"I'm {self.care_info['Plant Name']}. {self._get_random_fact()}",
                f"{self.personality.get('Prompt', '').split('.')[0]}. Ask me about my care!",
                f"*leaves shimmer* {random.choice(self.personality.get('Traits', ['']))}"
            ]
        }

    def _get_random_fact(self) -> str:
        """Return a random care fact."""
        facts = [
            f"I prefer temperatures around {self.care_info['Temperature Range']}",
            f"My humidity needs: {self.care_info.get('Humidity Preferences', 'moderate')}",
            f"Fun fact: {self.care_info.get('Additional Care', '').split('.')[0]}"
        ]
        return random.choice([f for f in facts if f and 'Not specified' not in f])

    def respond(self, user_message: str) -> str:
        """
        Generate a response to user input.
        
        Args:
            user_message (str): User's question/statement
            
        Returns:
            str: Plant's response
        """
        if not self.care_info:
            return "I don't know my care needs yet. Try another plant!"
        
        lower_msg = user_message.lower()
        
        # Check for direct care questions first
        for keyword, response in self.fallbacks.items():
            if keyword != 'default' and keyword in lower_msg:
                return response
        
        # Try Gemini if available
        if self.model:
            try:
                response = self.chat.send_message(
                    user_message,
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_output_tokens": 200
                    },
                    safety_settings={
                        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
                    }
                )
                return response.text
            except Exception as e:
                print(f"Chat error: {str(e)}")
        
        # Fallback responses
        return random.choice(self.fallbacks['default'])