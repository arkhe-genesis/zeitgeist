# ARKHE — FASE 0: Segurança, SBOM e Scoring
Artefatos gerados para desbloquear a conformidade CRA e transparência do projeto.
📁 Estrutura
plain
.
├── .github/
│   └── workflows/
│       ├── security-audit.yml   # cargo-deny + cargo-cyclonedx (CI)
│       └── score.yml            # Scoring por crate (CI)
├── scripts/
│   └── score-crates.py          # Script de scoring local
├── deny.toml                    # Política cargo-deny calibrada
└── README.md                    # Este arquivo
🚀 Uso Rápido
1. Instalar ferramentas localmente
bash
# cargo-deny (auditoria de vulnerabilidades + licenças)
cargo install cargo-deny --locked

# cargo-cyclonedx (SBOM CycloneDX)
cargo install cargo-cyclonedx --locked
2. Executar auditoria de segurança
bash
cargo deny check advisories licenses bans
3. Gerar SBOM
bash
cargo cyclonedx --format json --output sbom.json
4. Executar scoring por crate
bash
python3 scripts/score-crates.py --json --badge
Saída:
score-report.json — relatório detalhado por crate
score-badge.svg — badge para README
⚙️ Configuração cargo-deny (deny.toml)
Planilhas
Seção	Política	Justificativa
advisories	CVSS ≥ 4.0 = deny	Alinhado com CRA e NVD
licenses	GPL = warn (não deny)	Evita quebra de builds com deps transitivas
bans	openssl, failure, rustc-serialize = deny	Crates deprecados/inseguros
sources	Apenas crates.io	Supply chain security
📊 Metodologia de Scoring
Planilhas
Dimensão	Peso	Como medido
Compilabilidade	30%	cargo check -p <crate>
Testes	25%	cargo test -p <crate>
Stubs	25%	Heurística: todo!(), unimplemented!(), Ok(vec![])
Documentação	20%	README, exemplos, docstrings
Threshold para merge: 60/100
🔄 Integração CI/CD
Os workflows são executados em:
Push para main ou develop
Pull requests para main
Diariamente às 06:00 UTC (security audit)
📝 Próximos Passos
Copiar .github/workflows/ para o repositório ARKHE
Copiar deny.toml para a raiz do workspace
Copiar scripts/score-crates.py para scripts/
Executar cargo deny check localmente para validar
Corrigir violações de licença/vulnerabilidade antes do merge
🏷️ Selo
plain
ARKHE-PHASE0-SECURITY-SBOM-SCORING-2026-08-23🏷️ Selo
plain
ARKHE-PHASE0-SECURITY-SBOM-SCORING-2026-08-23
