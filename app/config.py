import os

API_KEY = os.getenv("GA_API_KEY", "demo-key-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./idp_gateway.db")
CONFIDENCE_THRESHOLD = 0.95
