import { spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";

const dirname = path.dirname(fileURLToPath(import.meta.url));
// frontend/src/api/ -> repository root
const repoRoot = path.resolve(dirname, "..", "..", "..");
const pythonPath = path.join(repoRoot, ".venv", "Scripts", "python.exe");

const STARTUP_TIMEOUT_MS = 10_000;
const POLL_INTERVAL_MS = 200;
const TEARDOWN_TIMEOUT_MS = 5_000;

async function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address && typeof address === "object") {
        server.close(() => resolve(address.port));
      } else {
        server.close();
        reject(new Error("no free port"));
      }
    });
  });
}

function killTree(child: ChildProcess): void {
  if (child.pid === undefined || child.exitCode !== null) return;
  try {
    spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  } catch {
    child.kill();
  }
}

async function waitForHealth(baseUrl: string): Promise<void> {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${baseUrl}/api/health`);
      if (response.ok) return;
    } catch {
      // uvicorn not accepting connections yet
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error(`uvicorn did not become healthy within ${STARTUP_TIMEOUT_MS}ms`);
}

it("real generated getHealth() through the central module returns the typed health data", async () => {
  const port = await findFreePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  const previousProcessBaseUrl = process.env.VITE_API_BASE_URL;
  const previousImportMetaBaseUrl = import.meta.env.VITE_API_BASE_URL;
  const child = spawn(
    pythonPath,
    [
      "-m",
      "uvicorn",
      "backend.app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(port),
      "--log-level",
      "warning",
    ],
    { cwd: repoRoot, stdio: "ignore", windowsHide: true },
  );

  try {
    await waitForHealth(baseUrl);

    // Configure the central module for the ephemeral test server before it
    // is imported, so the real call runs through the handwritten central
    // configuration exactly as production would.
    process.env.VITE_API_BASE_URL = baseUrl;
    import.meta.env.VITE_API_BASE_URL = baseUrl;
    const { getHealth } = await import("./client");

    const result = await getHealth();
    expect(result.error).toBeUndefined();
    expect(result.data).toEqual({ status: "ok" });
  } finally {
    if (previousProcessBaseUrl === undefined) {
      delete process.env.VITE_API_BASE_URL;
    } else {
      process.env.VITE_API_BASE_URL = previousProcessBaseUrl;
    }
    import.meta.env.VITE_API_BASE_URL = previousImportMetaBaseUrl;
    killTree(child);
    const exited = await Promise.race([
      new Promise<boolean>((resolve) => child.once("exit", () => resolve(true))),
      new Promise<boolean>((resolve) => setTimeout(() => resolve(false), TEARDOWN_TIMEOUT_MS)),
    ]);
    if (!exited) killTree(child);
  }
}, 15_000);
