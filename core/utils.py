import json

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
        print(f"Error: {file} file not found.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: {file} is not a valid JSON.")
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
        print(f"Error writing {file}: {e}")
        return False