import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
GOOGLE_DOCX_URL = os.getenv('GOOGLE_DOCX_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
POSTGRESQL = os.getenv('POSTGRESQL')
OPENAI_KEY = os.getenv('OPENAI')
OPTION = os.getenv('OPTION')
