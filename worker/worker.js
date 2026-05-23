export default {
  async fetch(request) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        }
      });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    // Health check
    if (path === '/health') {
      return new Response(JSON.stringify({ status: 'ok' }), {
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }

    // Proxy endpoint
    if (path === '/api/proxy' && request.method === 'POST') {
      try {
        const { endpoint, data } = await request.json();

        // Login to kx platform
        const loginResp = await fetch('https://kx.nopoliceman.help/api/v2/user/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user: '16689655710', pass: 'liguiteng1223' })
        });

        if (!loginResp.ok) {
          return new Response(JSON.stringify({ code: -1, msg: 'KX platform login failed' }), {
            headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
          });
        }

        const loginResult = await loginResp.json();
        if (loginResult.code !== 1) {
          return new Response(JSON.stringify({ code: -1, msg: 'KX login error: ' + (loginResult.msg || 'unknown') }), {
            headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
          });
        }

        // Get cookies from login response
        const cookies = loginResp.headers.get('set-cookie') || '';

        // Forward the API call
        const apiResp = await fetch('https://kx.nopoliceman.help' + endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Cookie': cookies,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          },
          body: JSON.stringify(data)
        });

        const result = await apiResp.json();

        return new Response(JSON.stringify(result), {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          }
        });
      } catch (e) {
        return new Response(JSON.stringify({ code: -1, msg: 'Proxy error: ' + e.message }), {
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      }
    }

    // 404
    return new Response('Not Found', { status: 404, headers: { 'Access-Control-Allow-Origin': '*' } });
  }
};
