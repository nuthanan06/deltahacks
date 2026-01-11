import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "Inventory")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.28))
FLASK_ENV = os.getenv("FLASK_ENV", "production")
FLASK_DEBUG = bool(int(os.getenv("FLASK_DEBUG", 0)))

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
