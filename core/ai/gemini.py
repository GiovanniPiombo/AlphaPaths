import json
from google import genai
from google.genai import types

from core.ai.base import BaseAIProvider
from core.utils import enrich_and_format_positions, read_json, retry_with_backoff
from core.path_manager import PathManager
from core.logger import app_logger

class GeminiProvider(BaseAIProvider):
    """
    Implementation of the Google Gemini API for portfolio analysis.
    """
    def __init__(self, api_key: str, model_name: str):
        """Initializes the Gemini client with the provided API key and model name."""
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                app_logger.error(f"Failed to initialize Gemini client: {e}")
        else:
            app_logger.warning("Missing Gemini API Key. Provider will not function.")

    def analyze_portfolio(self, portfolio_data: dict) -> dict:
        """
        Formats the prompt and sends the analysis request to Gemini.
        """
        if not self.client:
            return {"error": "Gemini API Key not configured. Please check your settings."}

        try:
            prompts_data = read_json(PathManager.PROMPTS_FILE)
            if not prompts_data:
                return {"error": "Could not load prompts.json"}

            template = prompts_data["portfolio_analysis"]["user_prompt_template"]
            system_instruction = prompts_data["portfolio_analysis"]["system_instruction"]

            if "ai_positions" not in portfolio_data:
                raw_pos = portfolio_data.get("positions", [])
                portfolio_data["ai_positions"] = enrich_and_format_positions(raw_pos)
            
            prompt = template.format(**portfolio_data)
            app_logger.info("Sending analysis request to Gemini API...")

            result = self._call_api(prompt, system_instruction)
            app_logger.debug("Successfully received response from Gemini.")
            return result
            
        except json.JSONDecodeError:
            app_logger.error("Gemini AI did not return a valid JSON format.")
            return {"error": "The AI did not return a valid JSON format."}
        except KeyError as e:
            app_logger.error(f"Missing expected key in prompts configuration: {e}")
            return {"error": "Configuration error in prompts.json."}
        except Exception as e:
            app_logger.error(f"Connection or API error with Gemini: {str(e)}")
            return {"error": f"Connection or API error: {str(e)}"}

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def _call_api(self, prompt: str, system_instruction: str) -> dict:
        """
        Helper function that actually executes the API call.
        Decorated to automatically retry on network or quota failures.
        """
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", 
                temperature=0.4
            )
        )
        return json.loads(response.text)