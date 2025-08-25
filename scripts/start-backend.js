#!/usr/bin/env node

const fs = require("fs");
const { spawn } = require("child_process");
const path = require("path");

// Read .env file from project root
const rootDir = path.resolve(__dirname, "..");
const envPath = path.join(rootDir, ".env");
let backendPort = "8000"; // default

if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, "utf8");
    const viteBackendPort = envContent.match(/VITE_BACKEND_PORT=(\d+)/);
    if (viteBackendPort) {
        backendPort = viteBackendPort[1];
    }
}

console.log(`Starting backend on port ${backendPort} from ${rootDir}`);

// Kill existing process
spawn("pkill", ["-f", `uvicorn.*src\\.web\\.app:app.*${backendPort}`], {
    stdio: "inherit",
});

setTimeout(() => {
    // Start MongoDB
    spawn("docker-compose", ["up", "-d", "mongodb"], {
        stdio: "inherit",
        cwd: rootDir,
    });

    setTimeout(() => {
        // Start backend
        const backendProcess = spawn(
            "bash",
            [
                "-c",
                `cd backend && source venv/bin/activate && uvicorn src.web.app:app --reload --host 0.0.0.0 --port ${backendPort}`,
            ],
            {
                stdio: "inherit",
                cwd: rootDir,
            }
        );

        backendProcess.on("error", (err) => {
            console.error("Failed to start backend:", err);
        });
    }, 2000);
}, 2000);
