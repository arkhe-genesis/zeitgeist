// src/queues.ts
export interface Env {
  QUEUE: Queue;
  TOPOMAS_API: string; // URL do backend Python
}

// Consumer da fila (processa tarefas PoUW)
export default {
  async queue(batch: MessageBatch, env: Env): Promise<void> {
    for (const message of batch) {
      const { projectId, task } = message.body;

      // Chama o backend Python para processar a tarefa
      const response = await fetch(`${env.TOPOMAS_API}/task/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId, task })
      });

      if (!response.ok) {
        // Requeue com retry
        message.retry({ delaySeconds: 30 });
      } else {
        // Processa resultado
        const result = await response.json();
        // Atualiza Durable Object via API interna
        await fetch(`${env.TOPOMAS_API}/internal/update-pareto`, {
          method: 'POST',
          body: JSON.stringify({ projectId, result })
        });
      }
    }
  }
};
