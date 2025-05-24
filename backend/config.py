import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Debug configuration
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
FLASK_ENV = os.getenv('FLASK_ENV', 'development')

# Server configuration
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 5001))

# CORS configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')

# Story generation configuration
ITERATION_LIMIT = int(os.getenv('ITERATION_LIMIT', 3))
# Story evaluation configuration
EVALUATION_LIMIT = int(os.getenv('EVALUATION_LIMIT', 3))
# Validate required environment variables
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")