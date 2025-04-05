🌿 Smart Plant Identifier + Care Companion



A modern, interactive tool that lets you identify plants from images, learn how to care for them, and even chat with them via AI! 🌱🧠✨

🌟 Features
🔍 Plant Identification via Image

Upload a plant photo.

The app identifies it using the PlantNet API.

🪴 Personalized Plant Care

See detailed care guides: watering, light, temperature, feeding, etc.

🤖 Talk to Your Plant (LLM-powered)

Fun, AI-generated personalities for each plant.

Chat with your leafy companion using personality prompts.

🔎 Fuzzy Name Matching

Finds best matches for care instructions using string similarity (even if the plant isn’t an exact match).

📸 Preview
(Optional: add a Streamlit screenshot or gif here)

🛠️ Installation
🔹 1. Clone the repo
bash
Copy
Edit
git clone https://github.com/your-username/plant-identifier-app.git
cd plant-identifier-app
🔹 2. Set up your environment
bash
Copy
Edit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
🔹 3. Install required packages
bash
Copy
Edit
pip install -r requirements.txt
🔹 4. Configure your API key
Create a file called api_config.py:

python
Copy
Edit
PLANTNET_API_KEY = "your_api_key_here"
🔹 5. Run the app
bash
Copy
Edit
streamlit run streamlit_app.py
🧠 LLM Integration (Optional)
If you're using an LLM (like OpenAI, Claude, or Mistral), each plant has a structured "Personality" you can use as a prompt seed.

json
Copy
Edit
"Personality": {
  "Title": "The Drama Queen",
  "Traits": [
    "Sensitive to dry air",
    "Sunlight diva",
    "Leaves curl when upset"
  ],
  "Prompt": "I adore bright indirect light and despise dry air! If you forget to mist me, I will wilt in protest. I’m dramatic but totally worth it."
}
💬 You can structure the prompt like this:

text
Copy
Edit
You are a plant named Stromanthe Peacock. Your personality is "The Night Owl" with traits like: prayer-moving leaves, color-shifting showoff, humidity addict. You love being misted daily and hate direct sun. Respond in character.
You can pass this to your favorite LLM API and let users chat with their plant 🌱💬

📁 Project Structure
graphql
Copy
Edit
.
├── streamlit_app.py               # Main Streamlit app
├── plant_care_instructions.json  # Local plant care database
├── api_config.py                 # Contains your PlantNet API key
├── requirements.txt              # Python dependencies
├── README.md                     # This file
🔧 JSON Care Entry Format
Each entry in plant_care_instructions.json should follow this format:

json
Copy
Edit
{
  "Plant Name": "Money Plant",
  "Light Requirements": "...",
  "Watering": "...",
  "Humidity Preferences": "...",
  "Temperature Range": "...",
  "Feeding Schedule": "...",
  "Toxicity": "...",
  "Additional Care": "...",
  "Personality": {
    "Title": "The Lucky Star",
    "Traits": ["Lush & leafy", "Thrives with love", "Symbol of fortune"],
    "Prompt": "I’m your Money Plant! Treat me with care and maybe I’ll bring you fortune. I adore bright light and a cozy corner to grow in!"
  }
}
❤️ Acknowledgments
PlantNet API

Streamlit community for app inspiration

Everyone who loves their plants!

📖 License
Licensed under the MIT License.
Feel free to fork, improve, and grow your own version of the app 🌱

