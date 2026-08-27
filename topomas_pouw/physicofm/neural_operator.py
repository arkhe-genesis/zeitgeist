# topomas_pouw/physicofm/neural_operator.py

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple
from topomas_v9_2 import BaseAgent, TopoMASConfig, MetricsCollector, ResultCache, ModelRegistry

class SpectralConv1d(nn.Module):
    """Convolução espectral 1D segura para operadores neurais."""
    def __init__(self, in_channels: int, out_channels: int, modes: int):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.modes = modes
        self.scale = (1 / (in_channels * out_channels))
        self.weights = nn.Parameter(self.scale * torch.rand(in_channels, out_channels, modes, dtype=torch.cfloat))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, in_channels, length = x.shape
        # FFT segura com normalização ortogonal
        x_ft = torch.fft.rfft(x, dim=-1, norm='ortho')

        # Trunca para o número real de modos disponíveis (evita index out of bounds)
        out_ft = torch.zeros(batch_size, self.out_channels, x_ft.size(-1), dtype=torch.cfloat, device=x.device)
        limit = min(self.modes, x_ft.size(-1))

        # Multiplicação espectral eficiente
        out_ft[:, :, :limit] = torch.einsum('bix,iox->box', x_ft[:, :, :limit], self.weights[:, :, :limit])

        # IFFT para voltar ao domínio espacial
        x_out = torch.fft.irfft(out_ft, n=length, dim=-1, norm='ortho')
        return x_out

class FourierNeuralOperator1D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, modes: int = 16, width: int = 64, n_layers: int = 4):
        super().__init__()
        self.fc0 = nn.Linear(in_channels, width)
        self.spectral_layers = nn.ModuleList([SpectralConv1d(width, width, modes) for _ in range(n_layers)])
        self.w_layers = nn.ModuleList([nn.Conv1d(width, width, 1) for _ in range(n_layers)])
        self.fc1 = nn.Linear(width, 128)
        self.fc2 = nn.Linear(128, out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, length, in_channels)
        x = self.fc0(x)
        x = x.permute(0, 2, 1) # (batch, width, length)

        for spec, w in zip(self.spectral_layers, self.w_layers):
            x1 = spec(x)
            x2 = w(x)
            x = F.gelu(x1 + x2)

        x = x.permute(0, 2, 1) # (batch, length, width)
        x = F.gelu(self.fc1(x))
        return self.fc2(x) # (batch, length, out_channels)

class PhysicoFMNeuralOperatorAgent(BaseAgent):
    """
    Agente FNO que modela campos contínuos de propriedades físicas.
    Mapeia sequências atômicas ordenadas para campos de energia/fônons.
    """
    name = "PhysicoFMNeuralOperator"

    def __init__(self, config: TopoMASConfig, metrics: MetricsCollector, cache: ResultCache,
                 model_registry: ModelRegistry, **kwargs):
        super().__init__(self.name, config, metrics, cache, model_registry, notification_bus=kwargs.get("notification_bus"), msg_bus=kwargs.get("msg_bus"))

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.in_channels = 8
        self.out_channels = 4
        self.model = FourierNeuralOperator1D(self.in_channels, self.out_channels).to(self.device)

    def _structure_to_1d_field(self, structure) -> torch.Tensor:
        """Converte estrutura para campo 1D ordenando átomos pela distância ao centro de massa."""
        coords = structure.cart_coords
        center = coords.mean(axis=0)
        distances = np.linalg.norm(coords - center, axis=1)
        sorted_indices = np.argsort(distances)

        sorted_coords = coords[sorted_indices]
        species = np.array([structure[i].specie.Z for i in sorted_indices])

        # Normaliza coordenadas para [0, 1]
        min_c, max_c = sorted_coords.min(axis=0), sorted_coords.max(axis=0)
        norm_coords = (sorted_coords - min_c) / (max_c - min_c + 1e-8)

        # Campo: [x, y, z, Z/100, dist, dx, dy, dz] (8 canais)
        field = np.hstack([norm_coords, (species/100.0).reshape(-1,1), (distances[sorted_indices]/10.0).reshape(-1,1), np.diff(norm_coords, axis=0, prepend=0.0)])
        return torch.tensor(field, dtype=torch.float32).unsqueeze(0).to(self.device) # (1, n_atoms, 8)

    def run(self, state: Dict) -> Dict:
        structures = state.get("structures", [])
        if not structures: return state

        predictions = []
        self.model.eval()
        with torch.no_grad():
            for struct in structures:
                field = self._structure_to_1d_field(struct)
                out_field = self.model(field) # (1, n_atoms, 4)
                # Agregação: energia total (soma), estabilidade (mínimo), etc.
                props = {
                    "total_energy": out_field[:, :, 0].sum().item(),
                    "phonon_stability": out_field[:, :, 1].min().item(),
                    "max_deformation": out_field[:, :, 2].max().item(),
                    "polarization": out_field[:, :, 3].mean().item()
                }
                predictions.append(props)

        state["neural_field_predictions"] = predictions
        self.model_registry.register("PhysicoFM_FNO", self.model, {"n_structures": len(structures)})
        return state
