# AlphaPaths - Advanced risk analysis, Monte Carlo simulation, and portfolio optimization.
# Copyright (C) 2026 Giovanni Piombo Nicoli
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from google import genai
from google.genai import types
import json
from core.utils import read_json, format_json, retry_with_backoff
from core.path_manager import PathManager
from core.logger import app_logger

# Load configuration and initialize the client
try:
    GEMINI_API_KEY = read_json(PathManager.CONFIG_FILE, "GEMINI_API_KEY")
    MODEL_NAME = read_json(PathManager.CONFIG_FILE, "GEMINI_MODEL")
    prompts_data = read_json(PathManager.PROMPTS_FILE)
except ValueError as e:
    app_logger.critical(f"Missing or invalid AI configuration: {e}")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

@retry_with_backoff(max_retries=3, base_delay=2.0)
def get_portfolio_analysis(portfolio_data: dict) -> dict:
    """
    Requests a structured portfolio analysis from the Gemini AI model.

    Retrieves the system instructions and user prompt templates from the 
    local configuration, formats them using the provided portfolio metrics, 
    and sends the request via the Google GenAI SDK. It explicitly configures 
    the API to return a JSON-formatted response (`application/json`) to ensure 
    predictable parsing by the application's user interface.

    Args:
        portfolio_data (dict): A dictionary containing key portfolio metrics 
            required to populate the prompt template. Expected keys include 
            'total_value', 'currency', 'risky_weight', 'cash_weight', 'mu', 
            'sigma', 'worst_case', 'median_case', and 'best_case'.

    Returns:
        dict: The AI's analytical response parsed into a Python dictionary. 
            If an API connection error occurs or the model returns invalid JSON, 
            it safely returns a dictionary containing an "error" key with the 
            failure details.
    """
    
    template = prompts_data["portfolio_analysis"]["user_prompt_template"]
    system_instruction = prompts_data["portfolio_analysis"]["system_instruction"]
    prompt = template.format(**portfolio_data)
    app_logger.info("Sending analysis request to Gemini API...")

    template = prompts_data["portfolio_analysis"]["user_prompt_template"]
    system_instruction = prompts_data["portfolio_analysis"]["system_instruction"]
    prompt = template.format(**portfolio_data)
    app_logger.info("Sending analysis request to Gemini API...")

    try:
        result = _call_gemini_api(client, prompt, system_instruction)
        app_logger.debug("Successfully received response from Gemini.")
        return result
        
    except json.JSONDecodeError:
        app_logger.error("Gemini AI did not return a valid JSON format.")
        return {"error": "The AI did not return a valid JSON format."}
    except Exception as e:
        app_logger.error(f"Connection or API error with Gemini after retries: {str(e)}")
        return {"error": f"Connection or API error: {str(e)}"}
    
@retry_with_backoff(max_retries=3, base_delay=2.0)
def _call_gemini_api(client, prompt, system_instruction):
    """
    Helper function that actually executes the API call.
    If it fails, the exception bubbles up to the decorator, triggering a retry.
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json", 
            temperature=0.4
        )
    )
    return json.loads(response.text)

if __name__ == "__main__":
    # Dummy data to test the module in isolation
    dummy_data = {
        "total_value": 100000.0,
        "currency": "EUR",
        "risky_weight": 95.0,
        "cash_weight": 5.0,
        "mu": 8.5,
        "sigma": 22.0,
        "worst_case": 65000.0,
        "median_case": 130000.0,
        "best_case": 210000.0
    }
    
    result = get_portfolio_analysis(dummy_data)
    print(format_json(result))