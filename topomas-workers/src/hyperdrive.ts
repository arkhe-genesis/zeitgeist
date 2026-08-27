// src/hyperdrive.ts
export interface Env {
  HYPERDRIVE: Hyperdrive;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/api/sql/query' && request.method === 'POST') {
      const { query, params } = await request.json();

      // Usa Hyperdrive para executar consulta no SQL Server/PostgreSQL
      const result = await env.HYPERDRIVE.query(query, params);
      return Response.json(result);
    }

    // Endpoint para obter métricas do projeto
    if (url.pathname === '/api/metrics') {
      const rows = await env.HYPERDRIVE.query(
        `SELECT * FROM vw_ProjectSummary WHERE ProjectID = $1`,
        [url.searchParams.get('projectId')]
      );
      return Response.json(rows);
    }

    return new Response('Not found', { status: 404 });
  }
};
