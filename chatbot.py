import random
from plant_data import get_plant

class PlantChatbot:
    def __init__(self, plant_name):
        self.plant = get_plant(plant_name)
        self.personality = self.plant.get("Personality", {}) if self.plant else {}
    
    def respond(self, user_message):
        if not self.plant:
            return "I'm not a recognized plant, sorry!"
        
        # Key care responses
        lower_msg = user_message.lower()
        if "water" in lower_msg:
            return f"💧 {self.plant['Watering']} {self._add_personality()}"
        elif "light" in lower_msg:
            return f"☀️ {self.plant['Light Requirements']} {self._add_personality()}"
        elif "toxic" in lower_msg:
            return f"⚠️ {self.plant['Toxicity']} {random.choice(self.personality.get('Traits', ['']))}"
        
        # Personality-based fallbacks
        return self._generate_personality_response()
    
    def _add_personality(self):
        return random.choice([
            f"| {self.personality.get('Title', '')}",
            f"| {random.choice(self.personality.get('Traits', ['']))}",
            ""
        ])
    
    def _generate_personality_response(self):
        prompts = [
            f"I'm {self.plant['Plant Name']}. {self.personality.get('Prompt', '')}",
            f"{random.choice(self.personality.get('Traits', ['']))}. Ask me about watering or light!",
            "I'm feeling leafy today! What would you like to know?"
        ]
        return random.choice(prompts)