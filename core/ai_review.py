from google import genai
from google.genai import types
import json
from core.utils import read_json, format_json
from core.path_manager import PathManager

# Load configuration and initialize the client
try:
    GEMINI_API_KEY = read_json(PathManager.CONFIG_FILE, "GEMINI_API_KEY")
    MODEL_NAME = read_json(PathManager.CONFIG_FILE, "GEMINI_MODEL")
    prompts_data = read_json(PathManager.PROMPTS_FILE)
except ValueError as e:
    print(f"Error: {e}")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

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
    
    try:
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
        
    except json.JSONDecodeError:
        return {"error": "The AI did not return a valid JSON format."}
    except Exception as e:
        return {"error": f"Connection or API error: {str(e)}"}
    
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