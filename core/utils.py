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
import time
from functools import wraps
import json
from core.logger import app_logger
import yfinance as yf

def read_json(file, parameter_name=None):
    """
    Reads a JSON file and retrieves either a specific parameter or the entire dataset.

    Attempts to load the specified JSON file. If a parameter name is provided,
    it returns the corresponding value; otherwise, it returns the fully parsed JSON 
    object. If the file is missing or contains invalid JSON, the function 
    prints an error message and terminates the program.

    Args:
        file (str): The path to the JSON file to be read.
        parameter_name (str, optional): The specific key to extract from the 
            JSON data. Defaults to None.

    Returns:
        Any: The value associated with `parameter_name` if provided, or the 
            entire dictionary/list parsed from the JSON file. Returns None 
            if `parameter_name` is requested but not found in the file.
    """
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # if parameter_name is provided, return that specific value, otherwise return the whole dictionary
        if parameter_name:
            return data.get(parameter_name)
        return data

    except FileNotFoundError:
        app_logger.error(f"Error: {file} file not found.")
        exit(1)
    except json.JSONDecodeError:
        app_logger.error(f"Error: {file} is not a valid JSON.")
        exit(1)

def format_json(data):
    """
    Formats a Python dictionary or list as a pretty-printed JSON string.

    Args:
        data (dict | list): The Python object to serialize.

    Returns:
        str: A formatted JSON string with 4-space indentation and UTF-8 
            characters preserved (ensure_ascii=False).
    """
    return json.dumps(data, indent=4, ensure_ascii=False)

def write_json(file, data):
    """
    Writes a Python dictionary to a JSON file with standard formatting.

    Opens the specified file in write mode and serializes the provided data 
    with 4-space indentation and UTF-8 encoding. Safely catches any writing 
    exceptions and prints the error instead of crashing the application.

    Args:
        file (str): The destination path for the JSON file.
        data (dict | list): The Python object to serialize and save.

    Returns:
        bool: True if the file was written successfully, False if an 
            exception occurred during the writing process.
    """
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        app_logger.error(f"Error writing {file}: {e}")
        return False
    
def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0):
    """
    Synchronous decorator that retries a function execution in case of 503 or 429 errors.
    It uses exponential backoff to calculate the wait time between attempts.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    if "503" in error_str:
                        if attempt == max_retries:
                            app_logger.error(f"[{func.__name__}] Failed permanently after {max_retries} attempts: {e}")
                            raise e
                        delay = base_delay * (2 ** attempt)
                        app_logger.warning(
                            f"[{func.__name__}] API Error (503)"
                            f"Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay) 
                    else:
                        raise e
        return wrapper
    return decorator

def get_invalid_tickers(tickers: list[str]) -> list[str]:
    """
    Validates a list of tickers using Yahoo Finance.
    Downloads 5 days of history to verify existence, avoiding issues 
    
    Returns a list of invalid or unfound tickers.
    """
    invalid_tickers = []
    
    unique_tickers = list(set([t for t in tickers if t]))
    
    if not unique_tickers:
        return []

    app_logger.info(f"Validating tickers via Yahoo Finance: {unique_tickers}")
    
    for ticker in unique_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if hist.empty:
                app_logger.warning(f"Ticker validation failed: {ticker} not found or returned empty data.")
                invalid_tickers.append(ticker)
                
        except Exception as e:
            app_logger.error(f"Error during validation of {ticker}: {e}")
            invalid_tickers.append(ticker)
            
    return invalid_tickers