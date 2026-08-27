// src/ontology.ts
export interface Env {
  AI: any;
  HYPERDRIVE: Hyperdrive;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Consulta semântica sobre ontologias oncológicas
    if (url.pathname === '/api/ontology/search' && request.method === 'POST') {
      const { query } = await request.json();

      // 1. Busca conceitos no NCIt via API externa (ou usa Workers AI)
      // Aqui usamos Workers AI para gerar embeddings e buscar similaridade
      const embeddingResponse = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
        text: query
      });
      const embedding = embeddingResponse.data;

      // 2. Busca no banco de ontologias (Neo4j ou SQL) via Hyperdrive
      // Exemplo: busca conceitos de câncer por similaridade de embedding
      const concepts = await env.HYPERDRIVE.query(
        `SELECT * FROM CancerConcepts WHERE embedding <-> $1 < 0.5`,
        [JSON.stringify(embedding)]
      );

      return Response.json(concepts);
    }

    // Mapeia material para câncer (baseado em ontologias)
    if (url.pathname === '/api/ontology/material-cancer' && request.method === 'POST') {
      const { materialFormula } = await request.json();

      // Usa Workers AI para inferir associação
      const prompt = `Given the material ${materialFormula}, which cancer types might it be associated with? Use NCIt and OncoTree terms.`;
      const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
        messages: [{ role: 'user', content: prompt }]
      });

      return Response.json({ associations: response.response });
    }

    return new Response('Not found', { status: 404 });
  }
};
