import logging
logging.basicConfig(level=logging.INFO)
from src.services.name_to_code_resolver import resolve_name_to_code

if __name__ == "__main__":
    code = resolve_name_to_code("拼多多")
    print(f"Result: {code}")
