#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

/**
 * Synchronizes port configuration from root .env to backend .env
 */
function syncPortConfig() {
    const rootDir = path.resolve(__dirname, "..");
    const rootEnvPath = path.join(rootDir, ".env");
    const backendEnvPath = path.join(rootDir, "backend", ".env");

    if (!fs.existsSync(rootEnvPath)) {
        console.error("Root .env file not found");
        process.exit(1);
    }

    // Read root .env file
    const rootEnvContent = fs.readFileSync(rootEnvPath, "utf8");

    // Extract port configuration
    const backendPortMatch = rootEnvContent.match(/VITE_BACKEND_PORT=(\d+)/);
    const frontendPortMatch = rootEnvContent.match(/VITE_FRONTEND_PORT=(\d+)/);

    if (!backendPortMatch || !frontendPortMatch) {
        console.error("Port configuration not found in root .env");
        process.exit(1);
    }

    const backendPort = backendPortMatch[1];
    const frontendPort = frontendPortMatch[1];

    // Read existing backend .env file
    let backendEnvContent = "";
    if (fs.existsSync(backendEnvPath)) {
        backendEnvContent = fs.readFileSync(backendEnvPath, "utf8");
    }

    // Remove existing port configuration if present
    backendEnvContent = backendEnvContent
        .replace(/VITE_BACKEND_PORT=\d+\n?/g, "")
        .replace(/VITE_FRONTEND_PORT=\d+\n?/g, "")
    .replace(/# Port Configuration \(synced from root \.env\)\n?/g, "");

    // Add port configuration at the end
    const portConfig = `
# Port Configuration (synced from root .env)
VITE_BACKEND_PORT=${backendPort}
VITE_FRONTEND_PORT=${frontendPort}
`;

    backendEnvContent = backendEnvContent.trim() + portConfig;

    // Write updated backend .env file
    fs.writeFileSync(backendEnvPath, backendEnvContent);

    console.log(`✅ Port configuration synced to backend/.env:`);
    console.log(`   VITE_BACKEND_PORT=${backendPort}`);
    console.log(`   VITE_FRONTEND_PORT=${frontendPort}`);
}

if (require.main === module) {
    syncPortConfig();
}

module.exports = { syncPortConfig };
