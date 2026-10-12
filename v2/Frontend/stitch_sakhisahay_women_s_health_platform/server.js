const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const DEFAULT_PORT = parseInt(process.env.PORT, 10) || 3000;
const BASE_DIR = __dirname;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf': 'font/ttf',
  '.txt': 'text/plain; charset=utf-8'
};

function serveFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        // Fallback to index.html for SPA client-side routes
        const indexPath = path.join(BASE_DIR, 'index.html');
        fs.readFile(indexPath, (idxErr, indexContent) => {
          if (idxErr) {
            res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end('404 Not Found');
          } else {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(indexContent);
          }
        });
      } else {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end(`500 Internal Server Error: ${err.message}`);
      }
    } else {
      const headers = { 'Content-Type': contentType };
      // Always revalidate app code so updates are picked up without a hard refresh.
      if (['.html', '.js', '.css'].includes(ext)) headers['Cache-Control'] = 'no-cache';
      res.writeHead(200, headers);
      res.end(content);
    }
  });
}

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url);
  let pathname = decodeURIComponent(parsedUrl.pathname);

  // Reverse proxy API and health calls to Python FastAPI backend (port 8000)
  if (pathname.startsWith('/api/') || pathname === '/health' || pathname === '/docs' || pathname === '/openapi.json') {
    const proxyReq = http.request({
      hostname: '127.0.0.1',
      port: 8000,
      path: req.url,
      method: req.method,
      headers: req.headers
    }, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });
    proxyReq.on('error', (err) => {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        error: 'Backend API unavailable',
        detail: 'Please run: python start.py in the Backend folder',
        code: err.code
      }));
    });
    req.pipe(proxyReq);
    return;
  }

  // Default to index.html
  if (pathname === '/' || pathname === '') {
    return serveFile(res, path.join(BASE_DIR, 'index.html'));
  }

  // Prevent directory traversal
  const safePath = path.normalize(pathname).replace(/^(\.\.[\/\\])+/, '');
  let filePath = path.join(BASE_DIR, safePath);

  fs.stat(filePath, (err, stats) => {
    if (!err && stats.isDirectory()) {
      const indexInDir = path.join(filePath, 'code.html');
      fs.stat(indexInDir, (codeErr, codeStats) => {
        if (!codeErr && codeStats.isFile()) {
          return serveFile(res, indexInDir);
        }
        const htmlInDir = path.join(filePath, 'index.html');
        return serveFile(res, htmlInDir);
      });
    } else {
      serveFile(res, filePath);
    }
  });
});

function startServer(port) {
  server.listen(port, () => {
    console.log(`\n=============================================================`);
    console.log(`  🌸 SakhiSahay Platform is running live!`);
    console.log(`  👉 Local Server URL: http://localhost:${port}`);
    console.log(`  🕒 Started at: ${new Date().toLocaleTimeString()}`);
    console.log(`=============================================================\n`);
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.warn(`Port ${port} in use, attempting port ${port + 1}...`);
      startServer(port + 1);
    } else {
      console.error('Server error:', err);
    }
  });
}

startServer(DEFAULT_PORT);
