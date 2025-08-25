// Environment configuration
// Reads from root .env file via Vite

export const VITE_BACKEND_PORT = Number(import.meta.env.VITE_BACKEND_PORT) || 8000
export const VITE_FRONTEND_PORT = Number(import.meta.env.VITE_FRONTEND_PORT) || 5173

export const API_BASE = `http://localhost:${VITE_BACKEND_PORT}/api`
export const BACKEND_URL = `http://localhost:${VITE_BACKEND_PORT}`
