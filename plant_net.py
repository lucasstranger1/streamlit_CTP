import requests

class PlantNetAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"

    def identify_plant(self, image_path):
        with open(image_path, 'rb') as f:
            files = {'images': f}
            params = {'api-key': self.api_key}

            response = requests.post(self.PLANTNET_URL, files=files, params=params)

        if response.status_code == 200:
            data = response.json()
            if "results" in data and data["results"]:
                plant_name1 = data["results"][0]["species"]["scientificNameWithoutAuthor"]
                return plant_name1
            else:
                return "No plant match found."
        else:
            return f"Error: {response.status_code}"
