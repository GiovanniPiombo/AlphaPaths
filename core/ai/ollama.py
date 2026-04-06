import json
import requests
from core.ai.base import BaseAIProvider
from core.utils import enrich_and_format_positions, read_json
from core.path_manager import PathManager
from core.logger import app_logger

class OllamaProvider(BaseAIProvider):
    """
    Implementation of the local AI provider using Ollama.
    """
    def __init__(self, endpoint: str, model_name: str):
        self.endpoint = endpoint.rstrip('/')
        self.model_name = model_name

    def analyze_portfolio(self, portfolio_data: dict) -> dict:
        """
        Sends the prompt to the local Ollama endpoint and parses the result.
        """
        if not self.endpoint or not self.model_name:
            return {"error": "Ollama Endpoint or Model not configured. Check settings."}

        try:
            prompts_data = read_json(PathManager.PROMPTS_FILE)
            if not prompts_data:
                app_logger.error("Could not load prompts.json for Ollama.")
                return {"error": "Could not load prompts.json"}

            template = prompts_data["portfolio_analysis"]["user_prompt_template"]
            system_instruction = prompts_data["portfolio_analysis"]["system_instruction"]

            if "ai_positions" not in portfolio_data:
                raw_pos = portfolio_data.get("positions", [])
                portfolio_data["ai_positions"] = enrich_and_format_positions(raw_pos)
            
            prompt = template.format(**portfolio_data)
            app_logger.info(f"Sending analysis request to Ollama ({self.model_name}) at {self.endpoint}...")

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_instruction,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.4
                }
            }

            response = requests.post(f"{self.endpoint}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
            result_text = response.json().get("response", "")
            cleaned_text = result_text.replace("```json", "").replace("```", "").strip()
            app_logger.debug("Successfully received response from Ollama.")
            return json.loads(cleaned_text)

        except requests.exceptions.RequestException as e:
            app_logger.error(f"Connection error with Ollama: {str(e)}")
            return {"error": f"Connection error: Is Ollama running at {self.endpoint}?"}
        except json.JSONDecodeError:
            app_logger.error("Ollama did not return a valid JSON format.")
            return {"error": "The AI did not return a valid JSON format."}
        except KeyError as e:
            app_logger.error(f"Missing key in prompts configuration: {e}")
            return {"error": "Configuration error in prompts.json."}
        except Exception as e:
            app_logger.error(f"Unexpected error with Ollama: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}