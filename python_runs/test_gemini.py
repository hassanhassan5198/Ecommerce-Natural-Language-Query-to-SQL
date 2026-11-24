import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
api_key = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-3.1-flash-lite"  # change this if the model is unavailable

if not api_key:
    print("error: api key not found in .env file")
else:
    print("api key loaded successfully")

    # timeout is in milliseconds: 30000 = 30 seconds
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=30000)
    )

    print(f"testing gemini connection with {MODEL}...")
    start = time.time()
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents="Say exactly this: The connection is alive and ready to build"
        )
        print(f"gemini says: {response.text}")
        print(f"responded in {time.time() - start:.1f} seconds")
    except Exception as e:
        print(f"connection failed after {time.time() - start:.1f} seconds: {e}")