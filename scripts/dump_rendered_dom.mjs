import puppeteer from 'puppeteer';
import http from 'http';
import fs from 'fs';
import path from 'path';

const PORT = 3002;
const DIST = path.resolve('site/dist');

// Static server with SPA fallback
const server = http.createServer((req, res) => {
  let filePath = path.join(DIST, req.url.split('?')[0]);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(DIST, 'index.html');
  }
  const ext = path.extname(filePath);
  const contentTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.svg': 'image/svg+xml',
    '.json': 'application/json'
  };
  res.writeHead(200, { 'Content-Type': contentTypes[ext] || 'text/plain' });
  res.end(fs.readFileSync(filePath));
});

server.listen(PORT, async () => {
  console.log(`Server running on http://127.0.0.1:${PORT}`);
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // 1. Landing Page
  await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'networkidle0' });
  const landingH1 = await page.$eval('h1', el => el.innerText);
  const landingSub = await page.$eval('p', el => el.innerText);
  const landingCode = await page.$eval('pre code', el => el.innerText);

  console.log('\n--- [1] RENDERED DOM: LANDING PAGE (/) ---');
  console.log('H1:', landingH1);
  console.log('Subheadline:', landingSub);
  console.log('Live Code Snippet:\n' + landingCode);

  // 2. Docs Page
  await page.goto(`http://127.0.0.1:${PORT}/docs`, { waitUntil: 'networkidle0' });
  const docsH1 = await page.$eval('h1', el => el.innerText);
  const docsFirstStep = await page.$eval('#quickstart h3', el => el.innerText);

  console.log('\n--- [2] RENDERED DOM: DOCS PAGE (/docs) ---');
  console.log('H1:', docsH1);
  console.log('First Step:', docsFirstStep);

  // 3. Blog Page
  await page.goto(`http://127.0.0.1:${PORT}/blog/deterministic-safety-imperative`, { waitUntil: 'networkidle0' });
  const blogH1 = await page.$eval('h1', el => el.innerText);
  const blogH2 = await page.$eval('h2', el => el.innerText);

  console.log('\n--- [3] RENDERED DOM: ESSAY PAGE (/blog/deterministic-safety-imperative) ---');
  console.log('H1:', blogH1);
  console.log('First Section:', blogH2);

  await browser.close();
  server.close();
  process.exit(0);
});
