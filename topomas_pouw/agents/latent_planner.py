# topomas_pouw/agents/latent_planner.py

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Any, Optional
from topomas_v9_2 import BaseAgent, TopoMASConfig, MetricsCollector, ResultCache, ModelRegistry

class LatentRecurrentPlanner(nn.Module):
    def __init__(self, state_dim: int = 128, action_dim: int = 64, n_iterations: int = 10, hebbian_lr: float = 0.1):
        super().__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.n_iterations = n_iterations
        self.hebbian_lr = hebbian_lr
        self.W = nn.Parameter(torch.randn(state_dim, state_dim) * 0.01)
        self.input_proj = nn.Linear(state_dim + action_dim, state_dim)
        self.output_proj = nn.Linear(state_dim, action_dim)

    def forward(self, context: torch.Tensor, memory: Optional[torch.Tensor] = None) -> torch.Tensor:
        batch_size = context.size(0)
        if memory is None:
            state = torch.zeros(batch_size, self.state_dim, device=context.device)
        else:
            state = memory

        for _ in range(self.n_iterations):
            hebbian_update = F.linear(state, self.W.T)
            state = state + self.hebbian_lr * torch.tanh(hebbian_update)

            gate = torch.sigmoid(self.input_proj(torch.cat([context, state], dim=-1)))
            state = gate * state + (1 - gate) * context
            state = F.layer_norm(state, (self.state_dim,))

        return self.output_proj(state)

class LatentPlannerAgent(BaseAgent):
    """
    Agente de raciocínio sem tokens. Planeja a próxima iteração via latência Hebbiana.
    """
    name = "LatentPlanner"

    def __init__(self, config: TopoMASConfig, metrics: MetricsCollector, cache: ResultCache,
                 model_registry: ModelRegistry, **kwargs):
        super().__init__(self.name, config, metrics, cache, model_registry, notification_bus=kwargs.get("notification_bus"), msg_bus=kwargs.get("msg_bus"))

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.planner = LatentRecurrentPlanner().to(self.device)
        self.memory_state: Optional[torch.Tensor] = None

    def _build_context_vector(self, state: Dict) -> torch.Tensor:
        """Extrai vetor de contexto do estado atual do pipeline de forma segura."""
        pareto = state.get("pareto_front", [])
        preds = state.get("predictions", {})

        topo_avg = np.mean([p.get("score", 0.5) for p in pareto]) if pareto else 0.5
        stab_avg = np.mean([p.get("stability", 0.5) for p in pareto]) if pareto else 0.5
        n_candidates = len(pareto)
        uncertainty = 1.0 - np.mean(preds.get("confidences", [0.5]))

        # Vetor base [topo, stab, n, unc, ...] -> Padding para 128
        base_vec = torch.tensor([topo_avg, stab_avg, n_candidates/100.0, uncertainty], dtype=torch.float32)
        context = F.pad(base_vec, (0, 128 - base_vec.shape[0]), "constant", 0)
        return context.unsqueeze(0).to(self.device)

    def run(self, state: Dict) -> Dict:
        # Usa o context manager nativo do v9.2 para métricas
        with self.metrics.time("agent_duration_seconds", {"agent": self.name}):
            context = self._build_context_vector(state)

            # Forward pass recorrente
            action_vec = self.planner(context, self.memory_state)

            # Atualiza memória persistente do agente
            self.memory_state = 0.9 * (self.memory_state if self.memory_state is not None else context) + 0.1 * context

            # Decodificação segura das ações
            raw_probs = F.softmax(action_vec[0, :3], dim=0).cpu().detach().numpy()

            decision = {
                "generate_new": bool(raw_probs[0] > 0.6), # CORRIGIDO: syntax error do prompt original
                "n_structures": int(5 + 10 * raw_probs[0]),
                "refine_pareto": bool(raw_probs[1] > 0.5),
                "request_dft": bool(raw_probs[2] > 0.7)
            }

            state["latent_decision"] = decision
            self.logger.info(f"Decisão latente decodificada: {decision}")
            return state
