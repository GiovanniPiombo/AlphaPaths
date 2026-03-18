from google import genai
from google.genai import types
import json
from core.utils import *

# Load configuration and initialize the client
try:
    GEMINI_API_KEY = read_json("config.json", "GEMINI_API_KEY")
    MODEL_NAME = read_json("config.json", "GEMINI_MODEL")
    prompts_data = read_json("prompts.json")
except ValueError as e:
    print(f"Error: {e}")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def get_portfolio_analysis(portfolio_data: dict) -> dict:
    """
    Sends portfolio data to the AI and returns a structured JSON analysis.
    """
    
    # Extract the user prompt template and system instruction from the prompts data
    template = prompts_data["portfolio_analysis"]["user_prompt_template"]
    system_instruction = prompts_data["portfolio_analysis"]["system_instruction"]
    
    # Format the user prompt by injecting the portfolio data into the template
    prompt = template.format(**portfolio_data)
    
    try:
        # API call leveraging the features of the genai SDK
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", 
                temperature=0.4
            )
        )
        
        # Parse the returned text into a real Python dictionary
        return json.loads(response.text)
        
    except json.JSONDecodeError:
        return {"error": "The AI did not return a valid JSON format."}
    except Exception as e:
        return {"error": f"Connection or API error: {str(e)}"}
    
# --- Test Block ---
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