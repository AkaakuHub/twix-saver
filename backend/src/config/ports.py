"""
Port configuration for backend
This file reads from root .env file and backend .env file
To change ports, modify root .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env and backend .env
root_env_path = Path(__file__).parent.parent.parent.parent / ".env"
backend_env_path = Path(__file__).parent.parent.parent / ".env"

# Load both env files (backend .env takes precedence)
load_dotenv(root_env_path)
load_dotenv(backend_env_path)

# Backend API port (from .env.ports)
VITE_BACKEND_PORT = int(os.getenv("VITE_BACKEND_PORT", "8000"))

# Frontend development server port (for CORS, from .env.ports)
VITE_FRONTEND_PORT = int(os.getenv("VITE_FRONTEND_PORT", "5173"))

# Construct CORS origins
CORS_ORIGINS = [
    "http://localhost:3000",
    f"http://localhost:{VITE_FRONTEND_PORT}",
]

# For development
DEV_CORS_ORIGINS = ",".join(CORS_ORIGINS)
