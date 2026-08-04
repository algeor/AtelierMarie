#!/usr/bin/env node
/**
 * Dependency-free Chrome smoke test for the local frontend.
 *
 * Usage:
 *   FRONTEND_URL=http://127.0.0.1:3000 node scripts/chrome_smoke.mjs
 *   CHROME_SMOKE_START_SERVERS=1 node scripts/chrome_smoke.mjs
 *
 * By default, the script expects the frontend server to already be running.
 * With CHROME_SMOKE_START_SERVERS=1 it seeds a temporary DB, starts a fake
 * Speedy boundary plus local backend/frontend servers, and runs customer/admin
 * Speedy + Econt shipping flows in Chrome. It fails on browser/page errors, 5xx responses,
 * unexpected 4xx responses, or blank render output.
 */

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const FRONTEND_URL = (process.env.FRONTEND_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const BACKEND_URL = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const START_SERVERS = process.env.CHROME_SMOKE_START_SERVERS === "1";
const RUN_FLOWS = process.env.CHROME_SMOKE_RUN_FLOWS !== "0";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || "chrome-smoke-admin-key";
const JWT_SECRET = process.env.JWT_SECRET || "chrome-smoke-jwt-secret-with-enough-length";
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..");
const FRONTEND_DIR = path.join(REPO_ROOT, "frontend");
const ROUTES = (process.env.CHROME_SMOKE_ROUTES || "/en,/en/products,/en/checkout,/en/orders,/en/admin/orders")
  .split(",")
  .map((route) => route.trim())
  .filter(Boolean);

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);

function findChrome() {
  const found = CHROME_CANDIDATES.find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error("Chrome executable not found. Set CHROME_PATH to run browser smoke tests.");
  }
  return found;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isProcessExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

function waitForExit(child, timeoutMs) {
  if (isProcessExited(child)) return Promise.resolve(true);
  return new Promise((resolve) => {
    const timeout = setTimeout(() => resolve(false), timeoutMs);
    child.once("exit", () => {
      clearTimeout(timeout);
      resolve(true);
    });
  });
}

async function stopProcess(child) {
  if (!child || isProcessExited(child)) return;

  child.kill("SIGTERM");
  if (!(await waitForExit(child, 3_000)) && !isProcessExited(child)) {
    child.kill("SIGKILL");
    await waitForExit(child, 2_000);
  }
}

function runChecked(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: REPO_ROOT,
    encoding: "utf8",
    ...options,
  });
  if (result.status !== 0) {
    throw new Error(
      `${command} ${args.join(" ")} failed\n${result.stdout || ""}${result.stderr || ""}`.trim()
    );
  }
  return result.stdout;
}

function seedSmokeDatabase(databasePath) {
  const script = String.raw`
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from app.database import init_db
from app.models.users import UserResponse
from app.services.auth_service import create_jwt

db_path = ${JSON.stringify(databasePath)}
init_db(db_path)

now = datetime.now(UTC)
created = now.strftime("%Y-%m-%d %H:%M:%S")
expires = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
admin_session_id = str(uuid.uuid4())
admin_user_id = "chrome-smoke-admin"

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys=ON")
try:
    products = [
        ("lavender-dream", "Lavender Dream", "Лавандулова мечта", 2500, 20, "A calm lavender candle for checkout smoke testing."),
        ("midnight-amber", "Midnight Amber", "Полунощен амбър", 3500, 10, "Warm amber candle used by browser tests."),
    ]
    for product in products:
        conn.execute(
            """
            INSERT INTO products (
                id, name_en, name_bg, price_cents, stock, is_active, description_en,
                weight_grams, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, 300, datetime('now'), datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                stock=excluded.stock,
                is_active=excluded.is_active,
                updated_at=datetime('now')
            """,
            product,
        )

    conn.execute(
        """
        INSERT INTO users (id, google_id, email, name, is_admin, created_at, last_login_at)
        VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'))
        ON CONFLICT(id) DO UPDATE SET is_admin=1, last_login_at=datetime('now')
        """,
        (admin_user_id, "chrome-smoke-google", "admin@atelier-smoke.test", "Chrome Smoke Admin"),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO sessions (id, user_id, created_at, expires_at, preferred_locale)
        VALUES (?, ?, ?, ?, 'en')
        """,
        (admin_session_id, admin_user_id, created, expires),
    )
    conn.commit()
finally:
    conn.close()

admin = UserResponse(
    id=admin_user_id,
    email="admin@atelier-smoke.test",
    name="Chrome Smoke Admin",
    avatar_url=None,
    is_admin=True,
)
print(json.dumps({"admin_session_id": admin_session_id, "admin_jwt": create_jwt(admin, admin_session_id)}))
`;

  const output = runChecked(".venv/bin/python", ["-c", script], {
    env: {
      ...process.env,
      DATABASE_PATH: databasePath,
      ENVIRONMENT: "test",
      JWT_SECRET,
      ADMIN_API_KEY,
      SESSION_COOKIE_SECURE: "false",
    },
  });
  return JSON.parse(output.trim().split("\n").at(-1));
}

async function waitForProcessHttp(child, url, label) {
  try {
    await waitForHttp(url, 45_000);
  } catch (error) {
    child.kill("SIGTERM");
    throw new Error(`${label} did not start: ${error.message}`);
  }
}

async function startFakeSpeedyServer() {
  const pdf = Buffer.from("%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n");
  const server = http.createServer((req, res) => {
    req.on("end", () => {
      if (req.url === "/calculate") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ calculations: [{ serviceId: 505, deliveryDeadline: 2, price: { total: 6.5 } }] }));
        return;
      }
      if (req.url === "/shipment") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ id: "63689182611" }));
        return;
      }
      if (req.url === "/track") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ parcels: [{ operations: [{ description: "Shipment in transit" }] }] }));
        return;
      }
      if (req.url === "/print") {
        res.writeHead(200, { "content-type": "application/pdf" });
        res.end(pdf);
        return;
      }
      res.writeHead(404, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: "unknown fake speedy endpoint" } }));
    });
    req.resume();
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const { port } = server.address();
  return {
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function startFakeEcontServer() {
  const server = http.createServer((req, res) => {
    req.on("end", () => {
      if (req.url === "/calculate") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ label: { totalPrice: 5.9, deliveryDays: 1 } }));
        return;
      }
      res.writeHead(404, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: "unknown fake econt endpoint" } }));
    });
    req.resume();
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const { port } = server.address();
  return {
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function startManagedServers() {
  const tempDir = await mkdtemp(path.join(os.tmpdir(), "atelier-smoke-stack-"));
  const databasePath = process.env.DATABASE_PATH || path.join(tempDir, "atelier_chrome_smoke.db");
  let fakeSpeedy;
  let fakeEcont;
  let backend;
  let frontend;

  try {
    fakeSpeedy = await startFakeSpeedyServer();
    fakeEcont = await startFakeEcontServer();
    const adminAuth = seedSmokeDatabase(databasePath);

    backend = spawn(
      ".venv/bin/uvicorn",
      ["app.main:app", "--host", "127.0.0.1", "--port", new URL(BACKEND_URL).port || "8000"],
      {
        cwd: REPO_ROOT,
        stdio: ["ignore", "pipe", "pipe"],
        env: {
          ...process.env,
          DATABASE_PATH: databasePath,
          ENVIRONMENT: "test",
          ADMIN_API_KEY,
          JWT_SECRET,
          SESSION_COOKIE_SECURE: "false",
          FRONTEND_URL,
          CORS_ORIGINS: JSON.stringify([FRONTEND_URL]),
          SPEEDY_BASE_URL: fakeSpeedy.url,
          SPEEDY_API_USERNAME: "chrome-smoke",
          SPEEDY_API_PASSWORD: "chrome-smoke",
          SPEEDY_CLIENT_ID: "123456",
          ECONT_CALCULATE_URL: `${fakeEcont.url}/calculate`,
          ECONT_API_USERNAME: "chrome-smoke",
          ECONT_API_PASSWORD: "chrome-smoke",
          EMAIL_PROVIDER: "console",
          EMAIL_API_KEY: "",
          ADMIN_NOTIFICATION_EMAIL: "",
          ZEPTOMAIL_WEBHOOK_AUTH_KEY: "",
        },
      }
    );
    backend.stdout.on("data", (chunk) => process.stdout.write(`[backend] ${chunk}`));
    backend.stderr.on("data", (chunk) => process.stderr.write(`[backend] ${chunk}`));
    await waitForProcessHttp(backend, `${BACKEND_URL}/v1/products?limit=1`, "Backend");

    frontend = spawn(
      "npm",
      ["run", "dev", "--", "--hostname", "127.0.0.1", "--port", new URL(FRONTEND_URL).port || "3000"],
      {
        cwd: FRONTEND_DIR,
        stdio: ["ignore", "pipe", "pipe"],
        env: {
          ...process.env,
          NEXT_PUBLIC_API_URL: BACKEND_URL,
          NEXT_PUBLIC_USE_MOCK_API: "false",
        },
      }
    );
    frontend.stdout.on("data", (chunk) => process.stdout.write(`[frontend] ${chunk}`));
    frontend.stderr.on("data", (chunk) => process.stderr.write(`[frontend] ${chunk}`));
    await waitForProcessHttp(frontend, `${FRONTEND_URL}/en/products/lavender-dream`, "Frontend");

    return {
      adminAuth,
      databasePath,
      async cleanup() {
        frontend?.kill("SIGTERM");
        backend?.kill("SIGTERM");
        await fakeSpeedy?.close();
        await fakeEcont?.close();
        if (process.env.CHROME_SMOKE_KEEP_DB !== "1") {
          await rm(tempDir, { recursive: true, force: true });
        }
      },
    };
  } catch (error) {
    frontend?.kill("SIGTERM");
    backend?.kill("SIGTERM");
    await fakeSpeedy?.close();
    await fakeEcont?.close();
    if (process.env.CHROME_SMOKE_KEEP_DB !== "1") {
      await rm(tempDir, { recursive: true, force: true });
    }
    throw error;
  }
}

function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(10_000, () => {
      req.destroy(new Error(`Timed out fetching ${url}`));
    });
  });
}

async function waitForHttp(url, timeoutMs = 30_000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
          res.resume();
          if (res.statusCode && res.statusCode < 500) resolve();
          else reject(new Error(`HTTP ${res.statusCode}`));
        });
        req.on("error", reject);
        req.setTimeout(2_000, () => req.destroy(new Error("timeout")));
      });
      return;
    } catch {
      await sleep(500);
    }
  }
  throw new Error(`Frontend did not become available at ${url}`);
}

async function getFreePort() {
  const server = http.createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const { port } = server.address();
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function waitForDevTools(port, chrome, stderrLines) {
  const started = Date.now();
  const versionUrl = `http://127.0.0.1:${port}/json/version`;
  while (Date.now() - started < 30_000) {
    if (isProcessExited(chrome)) {
      throw new Error(
        `Chrome exited before DevTools became available\n${stderrLines.join("\n")}`.trim()
      );
    }
    try {
      const version = await httpGetJson(versionUrl);
      if (version.webSocketDebuggerUrl) return version.webSocketDebuggerUrl;
    } catch {
      await sleep(250);
    }
  }
  throw new Error(
    `Timed out waiting for Chrome DevTools endpoint at ${versionUrl}\n${stderrLines.join("\n")}`.trim()
  );
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    this.ws.addEventListener("message", (event) => this.handleMessage(event));
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
  }

  handleMessage(event) {
    const message = JSON.parse(event.data);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result ?? {});
      return;
    }
    const listeners = this.listeners.get(message.method) ?? [];
    for (const listener of listeners) listener(message.params ?? {});
  }

  send(method, params = {}) {
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP command timed out: ${method}`));
        }
      }, 20_000);
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  waitFor(method, timeoutMs = 20_000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Timed out waiting for ${method}`)), timeoutMs);
      const listener = (params) => {
        clearTimeout(timer);
        const listeners = (this.listeners.get(method) ?? []).filter((item) => item !== listener);
        this.listeners.set(method, listeners);
        resolve(params);
      };
      this.on(method, listener);
    });
  }

  close() {
    this.ws?.close();
  }
}

function isExpectedHttpError(url, status) {
  if ((status === 401 || status === 403) && url.includes("/v1/auth/me")) return true;
  return false;
}

async function evaluate(client, expression) {
  const { result, exceptionDetails } = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (exceptionDetails) {
    throw new Error(exceptionDetails.text || "Runtime evaluation failed");
  }
  return result?.value;
}

async function waitForEval(client, expression, description, timeoutMs = 20_000) {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeoutMs) {
    try {
      const value = await evaluate(client, expression);
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${description}${lastError ? `: ${lastError.message}` : ""}`);
}

async function navigate(client, pathOrUrl) {
  const url = pathOrUrl.startsWith("http")
    ? pathOrUrl
    : `${FRONTEND_URL}${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;
  const loaded = client.waitFor("Page.loadEventFired");
  await client.send("Page.navigate", { url });
  await loaded;
  await sleep(500);
  return url;
}

async function clickByText(client, text, selector = "button,a,label") {
  const textJson = JSON.stringify(text);
  const selectorJson = JSON.stringify(selector);
  await waitForEval(
    client,
    `(() => {
      const needle = ${textJson};
      const elements = Array.from(document.querySelectorAll(${selectorJson}));
      const el = elements.find((item) => (item.innerText || item.textContent || '').trim().includes(needle));
      if (!el) return false;
      el.scrollIntoView({ block: 'center', inline: 'center' });
      el.click();
      return true;
    })()`,
    `clickable text ${text}`
  );
}

async function fillSelector(client, selector, value) {
  const selectorJson = JSON.stringify(selector);
  const valueJson = JSON.stringify(value);
  await waitForEval(
    client,
    `(() => {
      const el = document.querySelector(${selectorJson});
      if (!el) return false;
      el.scrollIntoView({ block: 'center', inline: 'center' });
      el.focus();
      const proto = el instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) setter.call(el, ${valueJson});
      else el.value = ${valueJson};
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`,
    `input ${selector}`
  );
}

async function selectFirstStatusTransition(client, value) {
  const valueJson = JSON.stringify(value);
  await waitForEval(
    client,
    `(() => {
      const select = Array.from(document.querySelectorAll('select'))
        .find((item) => Array.from(item.options).some((option) => option.value === ${valueJson}));
      if (!select) return false;
      select.scrollIntoView({ block: 'center', inline: 'center' });
      select.value = ${valueJson};
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`,
    `status transition ${value}`
  );
}

async function assertBodyIncludes(client, text, timeoutMs = 20_000) {
  const textJson = JSON.stringify(text);
  await waitForEval(
    client,
    `document.body.innerText.includes(${textJson})`,
    `body text ${text}`,
    timeoutMs
  );
}

async function setAdminCookies(client, adminAuth) {
  for (const cookie of [
    { name: "session_id", value: adminAuth.admin_session_id },
    { name: "atelier_auth", value: adminAuth.admin_jwt },
  ]) {
    await client.send("Network.setCookie", {
      name: cookie.name,
      value: cookie.value,
      url: FRONTEND_URL,
      path: "/",
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    });
  }
}

async function runCustomerSpeedyDoorFlow(client) {
  await navigate(client, "/en/products/lavender-dream");
  await assertBodyIncludes(client, "Lavender Dream");
  await clickByText(client, "Add to Cart", "button");
  await clickByText(client, "Proceed to Checkout", "a");
  await waitForEval(client, "location.pathname.endsWith('/checkout')", "checkout route");

  await fillSelector(client, "#checkout-email", "chrome-smoke@example.com");
  await fillSelector(client, "#checkout-name", "Chrome Smoke");
  await clickByText(client, "Door delivery", "label");
  await clickByText(client, "Speedy", "label");
  await fillSelector(client, "input[placeholder='e.g., Sofia']", "Sof");
  await clickByText(client, "Sofia", "button");
  await fillSelector(client, "input[placeholder='e.g., Vitosha Blvd 100']", "Vitosha Blvd 1");
  await fillSelector(client, "input[placeholder='+359...']", "+359888123456");
  await waitForEval(
    client,
    "document.querySelector('#checkout-form')?.dataset.deliveryPhase === 'ready'",
    "ready delivery quote",
    20_000
  );
  await clickByText(client, "Place Order", "button");
  await waitForEval(client, "location.pathname.includes('/confirmation')", "order confirmation", 20_000);
  await assertBodyIncludes(client, "chrome-smoke@example.com");
  console.log("ok flow customer-speedy-door-checkout");
}

async function runCustomerEcontOfficeFlow(client) {
  await navigate(client, "/en/products/midnight-amber");
  await assertBodyIncludes(client, "Midnight Amber");
  await clickByText(client, "Add to Cart", "button");
  await clickByText(client, "Proceed to Checkout", "a");
  await waitForEval(client, "location.pathname.endsWith('/checkout')", "checkout route");

  await fillSelector(client, "#checkout-email", "econt-smoke@example.com");
  await fillSelector(client, "#checkout-name", "Econt Smoke");
  await clickByText(client, "Pick up from office", "label");
  await clickByText(client, "Econt", "label");
  await fillSelector(client, "input[placeholder='Search city...']", "Sof");
  await clickByText(client, "Sofia", "button");
  await clickByText(client, "Ekont Tochka", "button");
  await fillSelector(client, "input[placeholder='+359...']", "+359888123457");
  await waitForEval(
    client,
    "document.querySelector('#checkout-form')?.dataset.deliveryPhase === 'ready'",
    "ready Econt office quote",
    20_000
  );
  await clickByText(client, "Place Order", "button");
  await waitForEval(client, "location.pathname.includes('/confirmation')", "Econt order confirmation", 20_000);
  await assertBodyIncludes(client, "econt-smoke@example.com");
  console.log("ok flow customer-econt-office-checkout");
}

async function runAdminShippingFlow(client, adminAuth) {
  await setAdminCookies(client, adminAuth);
  await navigate(client, "/en/admin/orders");
  await assertBodyIncludes(client, "c***@example.com");
  await selectFirstStatusTransition(client, "confirmed");
  await assertBodyIncludes(client, "Confirmed");
  const confirmedOrder = await waitForEval(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders?page=1&limit=100`)}, { credentials: "include" })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => data?.items?.find((order) =>
        order.customer_email === "chrome-smoke@example.com" &&
        order.status === "confirmed"
      ) || null)`,
    "confirmed smoke order"
  );
  const shipResult = await evaluate(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders/${confirmedOrder.id}/status`)}, {
      method: "PATCH",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        status: "shipped",
        tracking_number: "63689182611",
        tracking_carrier: "speedy",
      }),
    }).then((res) => res.ok ? res.json() : null)`
  );
  if (shipResult?.status !== "shipped") {
    throw new Error(`Expected admin ship status update to return shipped, got ${JSON.stringify(shipResult)}`);
  }
  await navigate(client, "/en/admin/orders");
  await assertBodyIncludes(client, "Shipped");
  const shippedOrder = await waitForEval(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders?page=1&limit=100`)}, { credentials: 'include' })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => data?.items?.find((order) =>
        order.customer_email === 'chrome-smoke@example.com' &&
        order.status === 'shipped' &&
        order.tracking_number === '63689182611' &&
        String(order.tracking_url || '').includes('speedy.bg')
      ) || null)`,
    "shipped order with Speedy tracking"
  );
  await navigate(client, `/en/admin/orders/${shippedOrder.id}`);
  await assertBodyIncludes(client, "63689182611");
  await assertBodyIncludes(client, "Speedy");
  const trackResult = await evaluate(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders/${shippedOrder.id}/track`)}, { method: 'POST', credentials: 'include' })
      .then((res) => res.ok ? res.json() : null)
      .then((order) => order?.courier_status || null)`
  );
  if (trackResult !== "in_transit") {
    throw new Error(`Expected Speedy courier_status=in_transit, got ${trackResult}`);
  }
  const labelResult = await evaluate(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders/${shippedOrder.id}/label`)}, { credentials: 'include' })
      .then(async (res) => ({ ok: res.ok, status: res.status, type: res.headers.get('content-type'), bytes: (await res.blob()).size }))`
  );
  if (!labelResult?.ok || !String(labelResult.type || "").includes("application/pdf") || labelResult.bytes < 20) {
    throw new Error(`Expected PDF label download, got ${JSON.stringify(labelResult)}`);
  }
  console.log("ok flow admin-confirm-ship-tracking");
}

async function runAdminEcontManualShippingFlow(client, adminAuth) {
  await setAdminCookies(client, adminAuth);
  const pendingOrder = await waitForEval(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders?page=1&limit=100`)}, { credentials: 'include' })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => data?.items?.find((order) =>
        order.customer_email === 'econt-smoke@example.com' &&
        order.delivery_courier === 'econt' &&
        order.status === 'pending'
      ) || null)`,
    "pending Econt smoke order"
  );

  const confirmedOrder = await evaluate(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders/${pendingOrder.id}/status`)}, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'confirmed' }),
    }).then((res) => res.ok ? res.json() : null)`
  );
  if (confirmedOrder?.status !== "confirmed") {
    throw new Error(`Expected Econt order to confirm, got ${JSON.stringify(confirmedOrder)}`);
  }

  const shippedOrder = await evaluate(
    client,
    `fetch(${JSON.stringify(`${BACKEND_URL}/v1/admin/orders/${pendingOrder.id}/status`)}, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        status: 'shipped',
        tracking_number: 'ECONT12345',
        tracking_carrier: 'econt',
      }),
    }).then((res) => res.ok ? res.json() : null)`
  );
  if (
    shippedOrder?.status !== "shipped" ||
    shippedOrder?.tracking_carrier !== "econt" ||
    shippedOrder?.tracking_number !== "ECONT12345" ||
    !String(shippedOrder?.tracking_url || "").includes("econt.com")
  ) {
    throw new Error(`Expected manually shipped Econt order, got ${JSON.stringify(shippedOrder)}`);
  }

  await navigate(client, `/en/admin/orders/${pendingOrder.id}`);
  await assertBodyIncludes(client, "Econt");
  await assertBodyIncludes(client, "ECONT12345");
  console.log("ok flow admin-econt-manual-ship-tracking");
}

async function runMobileSmoke(client) {
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true,
  });
  await navigate(client, "/en/products/lavender-dream");
  await assertBodyIncludes(client, "Lavender Dream");
  await navigate(client, "/en/checkout");
  await waitForEval(client, "document.body.innerText.trim().length > 20", "mobile checkout body");
  await client.send("Emulation.clearDeviceMetricsOverride");
  console.log("ok flow mobile-smoke");
}

async function main() {
  const managed = START_SERVERS ? await startManagedServers() : null;
  await waitForHttp(FRONTEND_URL);

  const userDataDir = await mkdtemp(path.join(os.tmpdir(), "atelier-chrome-"));
  const stderrLines = [];
  const chromeDebugPort = await getFreePort();
  const chrome = spawn(findChrome(), [
    "--headless=new",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${chromeDebugPort}`,
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  chrome.stderr.setEncoding("utf8");
  chrome.stderr.on("data", (chunk) => stderrLines.push(chunk));

  let client;
  try {
    const browserWs = await waitForDevTools(chromeDebugPort, chrome, stderrLines);
    const port = new URL(browserWs).port;
    const pages = await httpGetJson(`http://127.0.0.1:${port}/json/list`);
    const page = pages.find((entry) => entry.type === "page");
    if (!page?.webSocketDebuggerUrl) throw new Error("No Chrome page target available");

    client = new CdpClient(page.webSocketDebuggerUrl);
    await client.connect();
    await Promise.all([
      client.send("Page.enable"),
      client.send("Runtime.enable"),
      client.send("Log.enable"),
      client.send("Network.enable"),
    ]);

    const routeErrors = [];
    client.on("Runtime.exceptionThrown", (params) => {
      const details = params.exceptionDetails;
      const exception = details?.exception;
      const message = exception?.description || exception?.value || details?.text || "unknown";
      routeErrors.push(`exception: ${message}`);
    });
    client.on("Runtime.consoleAPICalled", (params) => {
      if (params.type === "error") {
        const text = (params.args ?? []).map((arg) => arg.value ?? arg.description ?? "").join(" ");
        routeErrors.push(`console.error: ${text}`);
      }
    });
    client.on("Network.responseReceived", ({ response }) => {
      if (!response) return;
      if (response.status >= 500 || (response.status >= 400 && !isExpectedHttpError(response.url, response.status))) {
        routeErrors.push(`http ${response.status}: ${response.url}`);
      }
    });
    client.on("Network.loadingFailed", ({ errorText, canceled, type }) => {
      if (!canceled) routeErrors.push(`network failed (${type}): ${errorText}`);
    });

    const smokeRoutes = managed
      ? ROUTES.filter((route) => !route.includes("/admin"))
      : ROUTES;

    for (const route of smokeRoutes) {
      routeErrors.length = 0;
      const url = `${FRONTEND_URL}${route.startsWith("/") ? route : `/${route}`}`;
      const loaded = client.waitFor("Page.loadEventFired");
      await client.send("Page.navigate", { url });
      await loaded;
      await sleep(750);
      const { result } = await client.send("Runtime.evaluate", {
        expression: `(() => ({ title: document.title, textLength: document.body.innerText.trim().length, path: location.pathname }))()`,
        returnByValue: true,
      });
      const value = result?.value ?? {};
      if (!value.textLength || value.textLength < 20) {
        routeErrors.push(`blank or tiny page body at ${url}`);
      }
      if (routeErrors.length) {
        throw new Error(`Chrome smoke failed for ${url}\n${routeErrors.join("\n")}`);
      }
      console.log(`ok ${value.path} ${value.title || "(untitled)"}`);
    }

    if (RUN_FLOWS && managed) {
      routeErrors.length = 0;
      await runCustomerSpeedyDoorFlow(client);
      if (routeErrors.length) {
        throw new Error(`Chrome customer flow errors\n${routeErrors.join("\n")}`);
      }

      routeErrors.length = 0;
      await runAdminShippingFlow(client, managed.adminAuth);
      if (routeErrors.length) {
        throw new Error(`Chrome admin flow errors\n${routeErrors.join("\n")}`);
      }

      routeErrors.length = 0;
      await runCustomerEcontOfficeFlow(client);
      if (routeErrors.length) {
        throw new Error(`Chrome Econt customer flow errors\n${routeErrors.join("\n")}`);
      }

      routeErrors.length = 0;
      await runAdminEcontManualShippingFlow(client, managed.adminAuth);
      if (routeErrors.length) {
        throw new Error(`Chrome Econt admin flow errors\n${routeErrors.join("\n")}`);
      }

      routeErrors.length = 0;
      await runMobileSmoke(client);
      if (routeErrors.length) {
        throw new Error(`Chrome mobile flow errors\n${routeErrors.join("\n")}`);
      }
    } else if (RUN_FLOWS) {
      console.log("skip flows (set CHROME_SMOKE_START_SERVERS=1 for seeded full-stack flows)");
    }
  } finally {
    client?.close();
    await stopProcess(chrome);
    await rm(userDataDir, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 });
    await managed?.cleanup();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
