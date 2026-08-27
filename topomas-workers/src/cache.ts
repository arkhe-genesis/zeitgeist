// src/cache.ts
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Exemplo: cache para consulta de materiais conhecidos
    if (url.pathname === '/api/materials/popular') {
      const cacheKey = new Request(request.url, request);
      const cache = caches.default;

      // Tenta cache
      let response = await cache.match(cacheKey);
      if (response) {
        return response;
      }

      // Se não estiver em cache, consulta Hyperdrive
      const data = await env.HYPERDRIVE.query(
        `SELECT * FROM Materials ORDER BY CreatedAt DESC LIMIT 100`
      );

      response = Response.json(data);
      // Armazena em cache com stale-while-revalidate
      await cache.put(cacheKey, response.clone());
      return response;
    }

    return new Response('Not found', { status: 404 });
  }
};
