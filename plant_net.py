import requests
import os
from typing import Dict, Any
import json

class PlantNetAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://my-api.plantnet.org/v2/identify/all"

    def identify_plant(self, image_path: str) -> Dict[str, Any]:
        """
        Identify plant from image with robust error handling.
        
        Returns:
            Dict with either:
            - Success: {'scientific_name': str, 'common_name': str, 'confidence': float}
            - Error: {'error': str}
        """
        try:
            # Validate image exists
            if not os.path.exists(image_path):
                return {'error': "Image file not found"}

            with open(image_path, 'rb') as img_file:
                files = [('images', (os.path.basename(image_path), img_file, 'image/jpeg'))]
                params = {'api-key': self.api_key}
                data = {'organs': ['auto']}

                response = requests.post(
                    self.base_url,
                    files=files,
                    params=params,
                    data=data,
                    timeout=15
                )

                # Check for API errors
                if response.status_code != 200:
                    try:
                        error_msg = response.json().get('message', response.text)
                    except:
                        error_msg = response.text
                    return {'error': f"API Error {response.status_code}: {error_msg}"}

                return self._parse_response(response.json())

        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            return {'error': f"Network/API Error: {str(e)}"}
        except Exception as e:
            return {'error': f"Unexpected Error: {str(e)}"}

    def _parse_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Safely parse the API response."""
        try:
            if not isinstance(api_response, dict):
                return {'error': "Invalid API response format"}

            results = api_response.get('results', [])
            if not results:
                return {'error': "No plant matches found"}

            best_match = results[0]
            if not isinstance(best_match, dict):
                return {'error': "Invalid match data format"}

            species = best_match.get('species', {})
            if not isinstance(species, dict):
                return {'error': "Invalid species data format"}

            return {
                'scientific_name': species.get('scientificNameWithoutAuthor', 'Unknown'),
                'common_name': (species.get('commonNames', ['Unknown']) or ['Unknown'])[0],
                'confidence': round(float(best_match.get('score', 0)) * 100, 1),
                'raw_data': best_match  # For debugging
            }

        except Exception as e:
            return {'error': f"Response parsing error: {str(e)}"}