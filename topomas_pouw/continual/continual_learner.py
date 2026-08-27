# topomas_pouw/continual/continual_learner.py

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from collections import defaultdict
from typing import Dict, Any, List, Tuple
from topomas_v9_2 import BaseAgent, TopoMASConfig, MetricsCollector, ResultCache, ModelRegistry

class ContinualLearner:
    def __init__(self, model: nn.Module, importance: float = 1e3):
        self.model = model
        self.importance = importance
        self.fisher = defaultdict(float)
        self.opt_params = {n: p.clone() for n, p in model.named_parameters() if p.requires_grad}

    def compute_fisher(self, data_loader, criterion, device='cpu'):
        self.model.eval() # Usa eval para得到 gradientes mais precisos da loss real
        self.fisher = defaultdict(float)
        for inputs, labels in data_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = self.model(inputs)
            loss = criterion(outputs, labels)

            self.model.zero_grad()
            loss.backward()

            for n, p in self.model.named_parameters():
                if p.grad is not None and p.requires_grad:
                    self.fisher[n] += p.grad.data.pow(2)

        # Normalização segura
        n_samples = max(1, len(data_loader.dataset))
        for n in self.fisher:
            self.fisher[n] /= n_samples

    def ewc_loss(self) -> torch.Tensor:
        loss = torch.tensor(0.0, device=next(self.model.parameters()).device)
        for n, p in self.model.named_parameters():
            if n in self.fisher and p.requires_grad:
                loss += (self.fisher[n] * (p - self.opt_params[n]).pow(2)).sum()
        return self.importance * loss

class ContinualLearningAgent(BaseAgent):
    name = "ContinualLearner"

    def __init__(self, config: TopoMASConfig, target_model: nn.Module, metrics: MetricsCollector,
                 cache: ResultCache, model_registry: ModelRegistry, **kwargs):
        super().__init__(self.name, config, metrics, cache, model_registry, notification_bus=kwargs.get("notification_bus"), msg_bus=kwargs.get("msg_bus"))

        self.learner = ContinualLearner(target_model)
        self.target_model = target_model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.optimizer = optim.Adam(self.target_model.parameters(), lr=1e-4)
        self.criterion = nn.MSELoss()

    def run(self, state: Dict) -> Dict:
        with self.metrics.time("agent_duration_seconds", {"agent": self.name}):
            new_data = state.get("verified_dft_results") # Espera dados validados

            if not new_data:
                self.metrics.inc("cl_skips_total", 1)
                return {"continual_update": "skipped_no_data"}

            # Cria DataLoader de forma segura
            try:
                X = torch.stack([d["features"] for d in new_data]).float()
                y = torch.stack([d["target"] for d in new_data]).float()
                loader = DataLoader(TensorDataset(X, y), batch_size=32, shuffle=True)
            except Exception as e:
                self.logger.error(f"Falha ao criar DataLoader contínuo: {e}")
                return {"continual_update": "error"}

            # 1. Calcula Fisher Information Matrix antes do update
            self.learner.compute_fisher(loader, self.criterion, self.device)

            # 2. Loop de treino com penalidade EWC
            self.target_model.train()
            total_loss = 0.0
            for batch_x, batch_y in loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                self.optimizer.zero_grad()

                preds = self.target_model(batch_x)
                task_loss = self.criterion(preds, batch_y)
                ewc_penalty = self.learner.ewc_loss()

                (task_loss + ewc_penalty).backward()
                self.optimizer.step()
                total_loss += task_loss.item()

            # 3. Salva novo checkpoint no Model Registry
            self.model_registry.register("PhysicoFM_FNO_Continual", self.target_model,
                                          {"loss": total_loss/len(loader), "n_samples": len(new_data)})

            # 4. Atualiza parâmetros ótimos do EWC para o próximo ciclo
            self.learner.opt_params = {n: p.clone() for n, p in self.target_model.named_parameters() if p.requires_grad}

            self.metrics.gauge("cl_last_loss", total_loss/len(loader))
            self.logger.info(f"EWC Update concluído. Loss: {total_loss/len(loader):.4f}")
            return {"continual_update": "success", "loss": total_loss/len(loader)}
