// locahun3d-demo Worker
//
// Re-emit the public R2 demo .rad file with CORS headers attached so the
// viewer can stream it via HTTP Range requests across origins. Cloudflare
// pub-*.r2.dev URLs don't return Access-Control-Allow-Origin themselves,
// so the browser blocks the response even though R2 happily serves the
// bytes to a non-browser client (e.g. curl). This Worker sits in front of
// the bucket and adds the missing headers.
//
// Routes:
//   GET  /Kousaten_ForDemo_point_cloud.rad
//   HEAD /Kousaten_ForDemo_point_cloud.rad
//   GET  /                                     -> tiny human-readable index
//   *    (anything else)                       -> 404
//
// Range, If-Range, If-None-Match, etc. are forwarded verbatim so partial
// content + caching work end-to-end. Spark's fetchRange relies on a real
// 206 Partial Content response with a correct Content-Range header.

const UPSTREAM_BASE = 'https://pub-6fe11fc6301a424ba739695a7c4d2dd9.r2.dev';

// Files this proxy is willing to forward. Whitelisted so the Worker
// cannot be abused as a generic open proxy if the bucket gains new
// objects later. Add new entries here when new demo scenes ship.
const ALLOWED_PATHS = new Set([
  '/Kousaten_ForDemo_point_cloud.rad',
]);

// CORS headers added to every response. * is fine — the Worker only
// serves public demo assets and never reads cookies or credentials,
// so there's no benefit to listing specific origins.
const CORS_HEADERS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
  'Access-Control-Allow-Headers': 'Range, If-Range, If-None-Match, If-Modified-Since',
  'Access-Control-Expose-Headers':'Content-Range, Content-Length, Accept-Ranges, ETag, Last-Modified',
  'Access-Control-Max-Age':       '86400',
};

function withCors(resp){
  // Clone headers so we can mutate them — Response.headers from fetch()
  // is a read-only view bound to the underlying network response.
  const h = new Headers(resp.headers);
  for(const [k, v] of Object.entries(CORS_HEADERS)) h.set(k, v);
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h });
}

function corsPreflight(){
  return new Response(null, {
    status: 204,
    headers: { ...CORS_HEADERS, 'Content-Length': '0' },
  });
}

async function proxy(request, path){
  // Forward upstream-relevant headers only — passing along `host`, `cf-*`
  // and other Worker-injected headers would confuse R2. Range matters for
  // chunked streaming; the conditional-request headers help with caching.
  const fwd = new Headers();
  const r = request.headers.get('range');           if(r) fwd.set('range', r);
  const ir = request.headers.get('if-range');       if(ir) fwd.set('if-range', ir);
  const inm = request.headers.get('if-none-match'); if(inm) fwd.set('if-none-match', inm);
  const ims = request.headers.get('if-modified-since'); if(ims) fwd.set('if-modified-since', ims);

  const upstreamUrl = UPSTREAM_BASE + path;
  const upstreamResp = await fetch(upstreamUrl, {
    method: request.method,
    headers: fwd,
    redirect: 'follow',
  });
  return withCors(upstreamResp);
}

const INDEX_HTML = `<!doctype html><meta charset=utf-8>
<title>locahun3d-demo</title>
<style>body{font-family:ui-sans-serif,system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 16px;color:#222;line-height:1.55}code{background:#f3f3f3;padding:2px 5px;border-radius:4px}</style>
<h1>locahun3d-demo</h1>
<p>CORS-enabled passthrough for the public R2 demo .rad. Available paths:</p>
<ul>
${[...ALLOWED_PATHS].map(p => `<li><a href="${p}"><code>${p}</code></a></li>`).join('\n')}
</ul>
<p style="color:#777;font-size:.9em">Source: <code>demo-proxy/src/index.js</code> in the Locahun3D repo.</p>`;

export default {
  async fetch(request){
    if(request.method === 'OPTIONS') return corsPreflight();

    const url = new URL(request.url);
    if(url.pathname === '/' || url.pathname === '/index.html'){
      return new Response(INDEX_HTML, {
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8', ...CORS_HEADERS },
      });
    }
    if(!ALLOWED_PATHS.has(url.pathname)){
      return new Response('Not found', {
        status: 404,
        headers: { 'Content-Type': 'text/plain; charset=utf-8', ...CORS_HEADERS },
      });
    }
    if(request.method !== 'GET' && request.method !== 'HEAD'){
      return new Response('Method not allowed', {
        status: 405,
        headers: { 'Content-Type': 'text/plain; charset=utf-8', Allow: 'GET, HEAD, OPTIONS', ...CORS_HEADERS },
      });
    }
    return proxy(request, url.pathname);
  },
};
