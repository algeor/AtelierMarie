#!/usr/bin/env node
/**
 * Browser-audit storefront cookies/storage and sync Cookie Policy inventory.
 *
 * Usage:
 *   FRONTEND_URL=https://theateliermarie.com node scripts/audit_cookie_inventory.mjs
 *   COOKIE_AUDIT_ROUTES="/,/en,/bg,/en/products" node scripts/audit_cookie_inventory.mjs
 */

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..");
const FRONTEND_URL = (
  process.env.FRONTEND_URL ||
  process.env.COOKIE_AUDIT_FRONTEND_URL ||
  process.env.NEXT_PUBLIC_SITE_URL ||
  "http://127.0.0.1:3000"
).replace(/\/$/, "");
const ROUTES = (process.env.COOKIE_AUDIT_ROUTES || "/,/en,/bg,/en/products,/en/cookies,/en/privacy,/en/checkout")
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findChrome() {
  const found = CHROME_CANDIDATES.find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error("Chrome executable not found. Set CHROME_PATH for cookie audit.");
  }
  return found;
}

function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
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
    }).on("error", reject);
  });
}

async function waitForHttp(url, timeoutMs = 30_000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url, { redirect: "manual" });
      if (response.status < 500) return;
    } catch {
      await sleep(250);
    }
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = http.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

function isProcessExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

async function stopProcess(child) {
  if (!child || isProcessExited(child)) return;
  child.kill("SIGTERM");
  await sleep(1500);
  if (!isProcessExited(child)) child.kill("SIGKILL");
}

async function waitForDevTools(port, chrome, stderrLines) {
  const started = Date.now();
  const versionUrl = `http://127.0.0.1:${port}/json/version`;
  while (Date.now() - started < 30_000) {
    if (isProcessExited(chrome)) {
      throw new Error(`Chrome exited before DevTools was ready\n${stderrLines.join("\n")}`.trim());
    }
    try {
      const version = await httpGetJson(versionUrl);
      if (version.webSocketDebuggerUrl) return version.webSocketDebuggerUrl;
    } catch {
      await sleep(250);
    }
  }
  throw new Error(`Timed out waiting for Chrome DevTools at ${versionUrl}`);
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

  waitFor(method, timeoutMs = 20_000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Timed out waiting for ${method}`)), timeoutMs);
      const listener = (params) => {
        clearTimeout(timer);
        const listeners = (this.listeners.get(method) ?? []).filter((item) => item !== listener);
        this.listeners.set(method, listeners);
        resolve(params);
      };
      const listeners = this.listeners.get(method) ?? [];
      listeners.push(listener);
      this.listeners.set(method, listeners);
    });
  }

  close() {
    this.ws?.close();
  }
}

async function evaluate(client, expression) {
  const { result, exceptionDetails } = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.text || "Runtime evaluation failed");
  return result?.value;
}

function durationFromCookie(cookie) {
  if (!cookie.expires || cookie.expires < 0) return "Session cookie.";
  return `Until ${new Date(cookie.expires * 1000).toISOString().slice(0, 10)}.`;
}

function cookieType(cookie) {
  const parts = [];
  if (cookie.httpOnly) parts.push("HttpOnly");
  if (cookie.secure) parts.push("Secure");
  parts.push("cookie");
  return parts.join(" ");
}

function storagePurpose(name) {
  if (name === "localStorage:announcement_dismissed_key") {
    return "Remembers that the visitor dismissed the current announcement banner.";
  }
  if (name === "sessionStorage:auth_redirect_to") {
    return "Temporarily keeps the return path during sign-in redirect.";
  }
  return "Stores storefront browser state detected during deployment audit.";
}

function mergeItem(map, name, item, route) {
  const current = map.get(name) || { ...item, observed_on: [] };
  current.observed_on = Array.from(new Set([...(current.observed_on || []), route]));
  map.set(name, current);
}

async function collectObserved(client, route, observed) {
  const cookies = (await client.send("Network.getAllCookies")).cookies || [];
  for (const cookie of cookies) {
    mergeItem(
      observed,
      cookie.name,
      {
        name: cookie.name,
        purpose_en: "Detected during the deployment browser audit.",
        type_en: cookieType(cookie),
        duration_en: durationFromCookie(cookie),
        source: "browser_cookie_audit",
      },
      route
    );
  }

  const storage = await evaluate(
    client,
    `(() => ({
      localStorage: Object.keys(window.localStorage || {}),
      sessionStorage: Object.keys(window.sessionStorage || {})
    }))()`
  );
  for (const key of storage?.localStorage || []) {
    const name = `localStorage:${key}`;
    mergeItem(
      observed,
      name,
      {
        name,
        purpose_en: storagePurpose(name),
        type_en: "Local storage",
        duration_en: "Until the banner/content changes or browser storage is cleared.",
        source: "browser_storage_audit",
      },
      route
    );
  }
  for (const key of storage?.sessionStorage || []) {
    const name = `sessionStorage:${key}`;
    mergeItem(
      observed,
      name,
      {
        name,
        purpose_en: storagePurpose(name),
        type_en: "Session storage",
        duration_en: "Until the browser tab/session is closed.",
        source: "browser_storage_audit",
      },
      route
    );
  }
}

function pythonBinary() {
  if (process.env.PYTHON) return process.env.PYTHON;
  const venvPython = path.join(REPO_ROOT, ".venv", "bin", "python");
  return existsSync(venvPython) ? venvPython : "python3";
}

function syncInventory(items) {
  const payload = JSON.stringify({ source: `deploy_audit:${FRONTEND_URL}`, items });
  if (process.env.COOKIE_AUDIT_SYNC_COMMAND) {
    const result = spawnSync(process.env.COOKIE_AUDIT_SYNC_COMMAND, {
      cwd: REPO_ROOT,
      input: payload,
      encoding: "utf8",
      env: process.env,
      shell: true,
    });
    if (result.status !== 0) {
      throw new Error(`Cookie inventory sync failed\n${result.stdout || ""}${result.stderr || ""}`.trim());
    }
    return result.stdout.trim();
  }
  const result = spawnSync(pythonBinary(), ["scripts/sync_cookie_inventory.py"], {
    cwd: REPO_ROOT,
    input: payload,
    encoding: "utf8",
    env: process.env,
  });
  if (result.status !== 0) {
    throw new Error(`Cookie inventory sync failed\n${result.stdout || ""}${result.stderr || ""}`.trim());
  }
  return result.stdout.trim();
}

async function main() {
  await waitForHttp(FRONTEND_URL);
  const userDataDir = await mkdtemp(path.join(os.tmpdir(), "atelier-cookie-audit-"));
  const chromeDebugPort = await getFreePort();
  const stderrLines = [];
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
      client.send("Network.enable"),
    ]);

    const observed = new Map();
    for (const route of ROUTES) {
      const url = `${FRONTEND_URL}${route.startsWith("/") ? route : `/${route}`}`;
      const loaded = client.waitFor("Page.loadEventFired");
      await client.send("Page.navigate", { url });
      await loaded;
      await sleep(750);
      await collectObserved(client, route, observed);
      await evaluate(
        client,
        `(() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const accept = buttons.find((button) => /Accept analytics|Приемам аналитика/i.test(button.innerText));
          if (accept) { accept.click(); return true; }
          return false;
        })()`
      );
      await sleep(250);
      await collectObserved(client, route, observed);
    }

    const output = syncInventory(Array.from(observed.values()));
    console.log(output);
  } finally {
    client?.close();
    await stopProcess(chrome);
    await rm(userDataDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
