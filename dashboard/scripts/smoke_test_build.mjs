/**
 * Headless Chromium E2E Smoke Test for SidraLake Evidence.dev static build.
 *
 * Serves `dashboard/build/` mounted at `/sidralake/` (exact GitHub Pages mirror),
 * opens EVERY page in real Chromium with DuckDB-WASM active, and fails the CI/CD
 * pipeline BEFORE `actions/deploy-pages` if any runtime, SQL, scale, formatting,
 * layout, or asset defect is detected.
 */

import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DASHBOARD_DIR = path.resolve(__dirname, '..');
const BUILD_DIR = path.join(DASHBOARD_DIR, 'build');
const PAGES_DIR = path.join(DASHBOARD_DIR, 'pages');
const BASE_PATH = '/sidralake';

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.parquet': 'application/octet-stream',
  '.arrow': 'application/octet-stream',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
};

function discoverRoutes() {
  const files = fs
    .readdirSync(PAGES_DIR)
    .filter((f) => f.endsWith('.md'))
    .sort();
  return files.map((f) => {
    const stem = f.replace(/\.md$/, '');
    return stem === 'index' ? `${BASE_PATH}/` : `${BASE_PATH}/${stem}/`;
  });
}

function resolveChromeExecutable() {
  const candidates = [
    process.env.CHROME_PATH,
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return undefined;
}

function startStaticServer() {
  const server = http.createServer((req, res) => {
    const rawUrl = (req.url || '/').split('?')[0];
    if (rawUrl === '/' || rawUrl === BASE_PATH) {
      res.writeHead(302, { Location: `${BASE_PATH}/` });
      res.end();
      return;
    }
    if (!rawUrl.startsWith(`${BASE_PATH}/`)) {
      res.writeHead(404);
      res.end('Not found (outside basePath)');
      return;
    }

    let relPath;
    try {
      relPath = decodeURIComponent(rawUrl.slice(BASE_PATH.length));
    } catch {
      res.writeHead(400);
      res.end('Bad Request: malformed URL encoding');
      return;
    }

    if (relPath.endsWith('/')) {
      relPath += 'index.html';
    }

    const fullPath = path.resolve(BUILD_DIR, `.${relPath}`);
    const relFromBuild = path.relative(BUILD_DIR, fullPath);
    if (relFromBuild.startsWith('..') || path.isAbsolute(relFromBuild)) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    let target = fullPath;
    if (fs.existsSync(target) && fs.statSync(target).isDirectory()) {
      target = path.join(target, 'index.html');
    }

    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      res.writeHead(404);
      res.end(`Not found: ${relPath}`);
      return;
    }

    const ext = path.extname(target).toLowerCase();
    res.writeHead(200, {
      'Content-Type': MIME_TYPES[ext] || 'application/octet-stream',
      'Cache-Control': 'no-store',
    });
    fs.createReadStream(target).pipe(res);
  });

  return new Promise((resolve, reject) => {
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      if (!addr || typeof addr === 'string') {
        reject(new Error('Failed to bind local smoke test server'));
        return;
      }
      resolve({ server, port: addr.port });
    });
  });
}

const FATAL_TEXT_PATTERNS = [
  /Catalog Error:/i,
  /Binder Error:/i,
  /Parser Error:/i,
  /Conversion Error:/i,
  /Runtime Error:/i,
  /Query Error/i,
  /\b(?:Big Value|Bar Chart|Line Chart|Area Chart|Data Table|Bubble Chart|Scatter Plot|Heatmap)\s*\n\s*error\b/i,
  /\b\d+\s+records?\s+with\s+\d+\s+propert/i,
];

async function waitForEvidenceHydration(page) {
  await page.waitForLoadState('networkidle', { timeout: 30_000 });
  let hydrationTimedOut = false;
  await page
    .waitForFunction(
      () => {
        const canvases = Array.from(document.querySelectorAll('canvas'));
        const hasRenderedCanvas = canvases.some((c) => {
          const rect = c.getBoundingClientRect();
          return rect.width > 100 && rect.height > 80;
        });
        const loadingText = document.body.innerText.includes('Loading...');
        return hasRenderedCanvas && !loadingText;
      },
      { timeout: 30_000 },
    )
    .catch(() => {
      hydrationTimedOut = true;
    });
  await page.waitForTimeout(1500);
  return { hydrationTimedOut };
}

async function auditRoute(context, origin, route) {
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => {
    pageErrors.push(err.message);
  });
  page.on('response', (resp) => {
    const url = resp.url();
    if (url.startsWith(origin) && resp.status() >= 400) {
      failedRequests.push(`${resp.status()} ${url}`);
    }
  });
  page.on('requestfailed', (req) => {
    const url = req.url();
    const errText = req.failure()?.errorText || 'unknown';
    // Ignore benign cancelled background prefetches; fail on genuine transport errors
    if (url.startsWith(origin) && errText !== 'net::ERR_ABORTED') {
      failedRequests.push(`FAILED(${errText}) ${url}`);
    }
  });

  const failures = [];
  const url = `${origin}${route}`;

  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    if (!response || response.status() !== 200) {
      failures.push(`HTTP status ${response ? response.status() : 'null'}`);
      return failures;
    }

    const { hydrationTimedOut } = await waitForEvidenceHydration(page);

    const domAudit = await page.evaluate(() => {
      const bodyText = document.body.innerText || '';
      const hasLoadingText = bodyText.includes('Loading...');
      const canvases = Array.from(document.querySelectorAll('canvas')).map((c) => {
        const r = c.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height) };
      });
      const renderedCanvases = canvases.filter((c) => c.w > 100 && c.h > 80).length;

      const visibleSqlInspectors = Array.from(document.querySelectorAll('details')).filter((el) => {
        const style = window.getComputedStyle(el);
        const text = el.innerText || '';
        return (
          style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          (/\brecords?\s+with\b/i.test(text) || /\bselect\b[\s\S]+\bfrom\b/i.test(text))
        );
      }).length;

      // Only audit DataTable columns whose header is a year column (avoids false positives
      // on salary/company counts between 2,010 and 2,029).
      const badYearCells = [];
      for (const table of Array.from(document.querySelectorAll('table'))) {
        const headers = Array.from(table.querySelectorAll('thead th')).map((th) =>
          (th.innerText || '').trim(),
        );
        const yearColIndices = headers
          .map((h, i) => (/\bano\b/i.test(h) ? i : -1))
          .filter((i) => i >= 0);
        if (yearColIndices.length === 0) continue;

        for (const tr of Array.from(table.querySelectorAll('tbody tr'))) {
          const cells = Array.from(tr.querySelectorAll('td'));
          for (const colIdx of yearColIndices) {
            const val = (cells[colIdx]?.innerText || '').trim();
            if (/^20[12]\d\.0$/.test(val) || /^2,0[12]\d$/.test(val)) {
              badYearCells.push(val);
            }
          }
        }
      }

      const mainEl = document.querySelector('main') || document.body;
      const mainText = mainEl.innerText || '';
      // Matches both integer and decimal comma-thousands percentages (e.g., 5,270% and 5,270.0%)
      const commaPctMatches = mainText.match(/\b\d{1,3}(?:,\d{3})+(?:\.\d+)?%/g) || [];
      const hugePctMatches = [];
      for (const m of mainText.matchAll(/(?<![\d.,])(\d{3,}(?:\.\d+)?)%/g)) {
        if (Number(m[1]) >= 250) {
          hugePctMatches.push(m[0]);
        }
      }

      const overflowPx = document.documentElement.scrollWidth - window.innerWidth;

      return {
        bodyText,
        hasLoadingText,
        renderedCanvases,
        visibleSqlInspectors,
        badYearCells: badYearCells.slice(0, 5),
        commaPctMatches: commaPctMatches.slice(0, 5),
        hugePctMatches: hugePctMatches.slice(0, 5),
        overflowPx,
      };
    });

    if (hydrationTimedOut || domAudit.hasLoadingText) {
      failures.push(
        `Page hydration incomplete (timedOut=${hydrationTimedOut}, loadingTextPresent=${domAudit.hasLoadingText})`,
      );
    }

    for (const pattern of FATAL_TEXT_PATTERNS) {
      const m = domAudit.bodyText.match(pattern);
      if (m) {
        failures.push(`Fatal error/debug pattern found in DOM: "${m[0]}"`);
      }
    }

    if (domAudit.visibleSqlInspectors > 0) {
      failures.push(`Found ${domAudit.visibleSqlInspectors} exposed SQL inspector block(s)`);
    }
    if (domAudit.renderedCanvases === 0) {
      failures.push('No rendered chart <canvas> (>100x80px) found on page');
    }
    if (domAudit.badYearCells.length > 0) {
      failures.push(`Malformed year values in DataTable: ${domAudit.badYearCells.join(', ')}`);
    }
    if (domAudit.commaPctMatches.length > 0 || domAudit.hugePctMatches.length > 0) {
      const allBad = [...domAudit.commaPctMatches, ...domAudit.hugePctMatches];
      failures.push(`Suspected 100x percentage scale bug in DOM: ${allBad.join(', ')}`);
    }
    if (domAudit.overflowPx > 4) {
      failures.push(`Horizontal page overflow detected: +${domAudit.overflowPx}px at 1440x900`);
    }
    if (failedRequests.length > 0) {
      failures.push(`Failed same-origin asset requests: ${failedRequests.join(' | ')}`);
    }
    if (pageErrors.length > 0) {
      failures.push(`Uncaught page errors: ${pageErrors.join(' | ')}`);
    }
    if (consoleErrors.length > 0) {
      failures.push(`Console errors: ${consoleErrors.join(' | ')}`);
    }
  } finally {
    await page.close();
  }

  return failures;
}

async function main() {
  if (!fs.existsSync(BUILD_DIR)) {
    console.error(`FAIL: build directory not found at ${BUILD_DIR}`);
    process.exit(1);
  }

  const routes = discoverRoutes();
  const executablePath = resolveChromeExecutable();
  const { server, port } = await startStaticServer();
  const origin = `http://127.0.0.1:${port}`;

  console.log(
    `[smoke_test_build] Serving ${BUILD_DIR} at ${origin}${BASE_PATH}/ (routes=${routes.length}, chrome=${executablePath || 'playwright-default'})`,
  );

  let browser;
  const allFailures = [];
  try {
    browser = await chromium.launch({
      headless: true,
      ...(executablePath ? { executablePath } : {}),
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

    for (const route of routes) {
      const start = Date.now();
      const failures = await auditRoute(context, origin, route);
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      if (failures.length === 0) {
        console.log(`  PASS ${route} (${elapsed}s)`);
      } else {
        console.error(`  FAIL ${route} (${elapsed}s):`);
        for (const f of failures) {
          console.error(`    - ${f}`);
          allFailures.push(`${route}: ${f}`);
        }
      }
    }
  } finally {
    if (browser) {
      await browser.close();
    }
    server.close();
  }

  if (allFailures.length > 0) {
    console.error(
      `\n[smoke_test_build] FAILED with ${allFailures.length} issue(s). Blocking deploy!`,
    );
    process.exit(1);
  }

  console.log(
    `\n[smoke_test_build] ALL ${routes.length} routes passed headless Chromium E2E verification!`,
  );
}

main().catch((err) => {
  console.error('[smoke_test_build] Unexpected error:', err);
  process.exit(1);
});
