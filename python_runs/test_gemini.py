import os
from dotenv import load_dotenv
from google import genai

# load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("error: api key not found in .env file")
else:
    print("api key loaded successfully")

    client = genai.Client(api_key=api_key)

    print("testing gemini connection...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say exactly this: The connection is alive and ready to build"
        )
        print(f"gemini says: {response.text}")
    except Exception as e:
        print(f"connection failed: {e}")