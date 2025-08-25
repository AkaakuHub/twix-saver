"""
Port configuration for backend
This file reads from .env.ports file
To change ports, modify backend/.env.ports
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env.ports
load_dotenv('.env.ports')

# Backend API port (from .env.ports)
VITE_BACKEND_PORT = int(os.getenv('VITE_BACKEND_PORT', '8000'))

# Frontend development server port (for CORS, from .env.ports)
VITE_FRONTEND_PORT = int(os.getenv('VITE_FRONTEND_PORT', '5173'))

# Construct CORS origins
CORS_ORIGINS = [
    f"http://localhost:3000",
    f"http://localhost:{VITE_FRONTEND_PORT}",
]

# For development
DEV_CORS_ORIGINS = ",".join(CORS_ORIGINS)