import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { createServer as createTcpServer } from "node:net";
import { createServer } from "vite";

function requireFreePort(port) {
  return new Promise((resolve, reject) => {
    const probe = createTcpServer();
    probe.once("error", () =>
      reject(
        new Error(
          `E2E port ${port} is occupied. No existing process will be stopped.`,
        ),
      ),
    );
    probe.listen(port, "127.0.0.1", () => probe.close(resolve));
  });
}
export default async function setup() {
  const backendPort = Number(process.env.MOTOR_E2E_BACKEND_PORT || 18001);
  const frontendPort = Number(process.env.MOTOR_E2E_FRONTEND_PORT || 15173);
  if (
    [backendPort, frontendPort].some(
      (port) => !Number.isInteger(port) || port < 1024 || port > 65535,
    ) ||
    backendPort === frontendPort
  )
    throw new Error(
      "Use distinct MOTOR_E2E_BACKEND_PORT and MOTOR_E2E_FRONTEND_PORT values between 1024 and 65535.",
    );
  const backendUrl = `http://127.0.0.1:${backendPort}`;
  // Direct child ownership avoids shell process-tree cleanup on corporate Windows.
  await Promise.all([
    requireFreePort(backendPort),
    requireFreePort(frontendPort),
  ]);
  const interpreter =
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python";
  const python =
    process.env.PYTHON ||
    [
      path.resolve("../.venv", interpreter),
      path.resolve("../backend/.venv", interpreter),
    ].find(existsSync) ||
    "python";
  const backend = spawn(python, ["e2e/backend.py"], {
    cwd: process.cwd(),
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  let exited = false;
  let server;
  backend.on("error", () => {
    exited = true;
  });
  backend.on("exit", () => {
    exited = true;
  });
  // Drain without printing model/user payloads; harness has sanitized request telemetry.
  backend.stdout.resume();
  backend.stderr.resume();
  const cleanup = async () => {
    if (server) await server.close();
    if (!exited) backend.kill();
  };
  try {
    let ready = false;
    // Corporate Windows may cold-load the Python environment slowly.
    const startupDeadline = Date.now() + 60000;
    while (Date.now() < startupDeadline && !exited) {
      try {
        ready = (
          await fetch(`${backendUrl}/api/v1/health`, {
            signal: AbortSignal.timeout(1000),
          })
        ).ok;
      } catch {
        /* Wait for startup. */
      }
      if (ready) break;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    if (!ready)
      throw new Error(
        "The test-only FastAPI harness did not start. Install backend dev dependencies and set PYTHON if needed.",
      );
    process.env.API_PROXY_TARGET = backendUrl;
    server = await createServer({
      server: { host: "127.0.0.1", port: frontendPort, strictPort: true },
    });
    await server.listen();
    return cleanup;
  } catch (error) {
    await cleanup();
    throw error;
  }
}
