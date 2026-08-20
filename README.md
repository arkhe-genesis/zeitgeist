# zeitgeist-safe v1.0.0-stable

Spectral Regime Detection with Safety Guarantees

## Overview
zeitgeist-safe is a production-stable library for detecting regime changes in high-dimensional data streams. It combines:
* Incremental SVD (Brand, 2006) for O(n·k²) spectral updates
* Information-theoretic divergences (JS, Wasserstein-1) for regime comparison
* Permutation bootstrap for adaptive thresholds without manual calibration
* Full state serialization for reproducibility and audit trails

## Ontological Classification (v2.0)
Every component is classified by epistemic status:

| Tag | Meaning | Example |
| --- | --- | --- |
| [MATH] | Formal mathematical guarantee | JS divergence, Shannon entropy |
| [STRUCT] | Architectural analogy | Synaptic plasticity ↔ forgetting factor |
| [HEUR] | Empirical heuristic | Topological stability index |

## Installation

```bash
pip install zeitgeist-safe
```

## Quick Start

```python
from zeitgeist import SafeCorePolynomialBridge
import numpy as np

# Initialize detector
bridge = SafeCorePolynomialBridge(
    n_dims=100,      # Dimensionality of your data
    max_rank=20,     # Spectral truncation rank
    forgetting_factor=0.8,  # Adaptation rate
)

# Stream data
for vector in data_stream:
    bridge.record_experience(vector)

    # Check for regime change every 60 samples
    if bridge._n_recorded % 60 == 0:
        report = bridge.get_regime_divergence(
            window=60,
            method="mean",      # "mean", "median", "pairwise_mean", "wasserstein"
            adaptive=True,      # Use permutation bootstrap
            confidence=0.95,
        )
        if report.passed:
            print(f"REGIME CHANGE at step {bridge._n_recorded}")
            print(f"  Divergence: {report.divergence:.4f}")
            print(f"  p-value: {report.p_value:.4f}")
```

## Stable API

### SafeCorePolynomialBridge

```python
class SafeCorePolynomialBridge:
    def __init__(
        self,
        n_dims: int,
        max_rank: int = 15,
        max_history: int = 500,
        forgetting_factor: float = 0.8,
        rng: np.random.Generator | None = None,
    )

    def record_experience(self, vector: np.ndarray, reward: float = 1.0) -> None

    def get_regime_divergence(
        self,
        window: int = 60,
        method: Literal["mean", "median", "pairwise_mean", "wasserstein"] = "mean",
        adaptive: bool = True,
        confidence: float = 0.95,
        n_permutations: int = 200,
        threshold_fixed: float = 0.1,
        rng: np.random.Generator | None = None,
    ) -> DivergenceReport

    def get_state_history(self) -> list[BridgeState]

    def save_state(self, path: str | Path) -> None

    def load_state(self, path: str | Path) -> None
```

### DivergenceReport

```python
@dataclass
class DivergenceReport:
    divergence: float      # Computed divergence value
    threshold: float       # Threshold (adaptive or fixed)
    p_value: float | None  # Bootstrap p-value (None if adaptive=False)
    passed: bool           # True if divergence > threshold
    method: str            # Method used
    window: int            # Window size
```

### BridgeState

```python
@dataclass
class BridgeState:
    eigenvalues: np.ndarray              # Normalized spectral distribution
    timestamp: float                     # Monotonic clock
    n_samples: int                       # Total samples processed
    entropy: float                       # [MATH] Shannon entropy
    effective_rank: float                # [MATH] 2^entropy
    spectral_purity: float               # [MATH] Σp²
    spectral_variation_rate: float       # [HEUR] Empirical
    topological_stability_index: float   # [HEUR] Empirical (see docs)
```

## Validation Framework

```python
from zeitgeist.validators import SyntheticDataGenerator, RegimeValidator

# Generate ground-truth data
data, true_changes = SyntheticDataGenerator.generate_trajectory(
    n_total=1000, n_dims=50, change_points=[300, 600]
)

# Validate your detector
detected = [...]  # Your detector's output
validator = RegimeValidator(tolerance=20)
result = validator.validate(detected, true_changes, total_samples=len(data))

print(result)
# ValidationResult(sensitivity=0.85, specificity=0.99, precision=0.92, f1=0.88, mean_delay=12.3)
```

## Testing

```bash
python -m zeitgeist.tests
```

All 9 tests must pass:
* T1: JS divergence properties
* T2: Wasserstein-1 properties
* T3: Incremental SVD correctness
* T4-T7: Regime detection (4 methods)
* T8: State persistence
* T9: Validation framework

## Safety & Ethics
This library is designed for safe AI monitoring:
* All improvements are logged and reversible (save_state/load_state)
* Adaptive thresholds require no manual calibration (reducing human error)
* Full provenance of every detection decision
* For recursive self-improvement applications, see zeitgeist.metrics.RSIMetrics and the companion paper on meta-regime detection.

## Citation

```bibtex
@software{zeitgeist_safe_2026,
  title={zeitgeist-safe: Spectral Regime Detection},
  author={Arkhe(n) Research Group},
  year={2026},
  url={https://github.com/arkhe-genesis/zeitgeist}
}
```

Arkhe(n) Research Group / Safe Core • 2026