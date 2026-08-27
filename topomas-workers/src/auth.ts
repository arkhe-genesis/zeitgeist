// src/auth.ts
import { EIP712Verifier } from './eip712'; // Implementação do verifier (já temos)
import { signJWT, verifyJWT } from './jwt';

export interface Env {
  JWT_SECRET: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Endpoint para verificar assinatura e obter JWT
    if (url.pathname === '/api/auth/verify' && request.method === 'POST') {
      const { signature, message } = await request.json();
      const verifier = new EIP712Verifier();

      // Verifica assinatura (com nonce e expiração)
      const isValid = await verifier.verify(message.account, signature, message);
      if (!isValid) {
        return new Response('Invalid signature or expired nonce', { status: 401 });
      }

      // Gera JWT com escopo
      const payload = {
        sub: message.account,
        tenant: message.tenant,
        sessionId: message.sessionId,
        scope: message.scope || 'user', // 'miner', 'scientist', 'admin'
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 86400 // 24h
      };
      const token = await signJWT(payload, env.JWT_SECRET);

      return Response.json({ token });
    }

    // Endpoint para validar JWT (para outros Workers)
    if (url.pathname === '/api/auth/validate' && request.method === 'GET') {
      const authHeader = request.headers.get('Authorization');
      if (!authHeader?.startsWith('Bearer ')) {
        return new Response('Missing token', { status: 401 });
      }
      const token = authHeader.slice(7);
      try {
        const payload = await verifyJWT(token, env.JWT_SECRET);
        return Response.json({ valid: true, payload });
      } catch {
        return Response.json({ valid: false }, { status: 401 });
      }
    }

    return new Response('Not found', { status: 404 });
  }
};
