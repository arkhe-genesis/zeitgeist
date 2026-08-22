// FILE: crates/safe-core-utils/src/architectural_audit.rs
//! Registro append-only de decisoes arquiteturais com encadeamento criptografico,
//! fork resolution, e persistencia em disco.
//!
//! Design decisions:
//! - Hash chains para forward integrity
//! - Indice bidirecional para travessia O(1)
//! - Fork detection e resolution por timestamp + comprimento
//! - Persistencia append-only com fsync
//! - Determinismo via postcard

use crate::architectural_decision::{ArchitecturalDecision, DecisionHash};
use crate::persistence::AppendOnlyLog;
use std::collections::HashMap;
use std::path::Path;
use uuid::Uuid;

/// Estado de quiescencia do sistema (I76.1 / I79.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QuiescenceState {
    /// Operando normalmente.
    Active,
    /// Fork detectado, aguardando resolucao.
    ForkDetected,
    /// Particao detectada, aguardando consenso.
    PartitionDetected,
    /// Em quiescencia — nenhuma acao nova ate resolucao.
    Quiescent,
}

/// Registro append-only de decisoes arquiteturais com encadeamento criptografico.
#[derive(Debug)]
pub struct ArchitecturalAudit {
    decisions: HashMap<Uuid, ArchitecturalDecision>,
    hash_to_id: HashMap<DecisionHash, Uuid>,
    id_to_hash: HashMap<Uuid, DecisionHash>,
    next_index: HashMap<DecisionHash, Uuid>,
    head: Option<DecisionHash>,
    tail: Option<DecisionHash>,
    /// Estado de quiescencia atual.
    pub quiescence: QuiescenceState,
    /// Timestamp em que a quiescencia foi ativada (se ativa).
    pub quiescence_since: Option<u64>,
    /// Log de persistencia opcional.
    log: Option<AppendOnlyLog>,
}

impl ArchitecturalAudit {
    /// Cria um novo registro de auditoria vazio (in-memory).
    pub fn new() -> Self {
        Self {
            decisions: HashMap::new(),
            hash_to_id: HashMap::new(),
            id_to_hash: HashMap::new(),
            next_index: HashMap::new(),
            head: None,
            tail: None,
            quiescence: QuiescenceState::Active,
            quiescence_since: None,
            log: None,
        }
    }

    /// Cria um registro com persistencia em disco.
    /// Recupera decisoes existentes do log e reconstrói o estado.
    pub fn with_persistence<P: AsRef<Path>>(path: P) -> Result<Self, AuditError> {
        let mut audit = Self::new();
        let log = AppendOnlyLog::open(path)
            .map_err(|e| AuditError::Persistence(e.to_string()))?;

        // Recupera decisoes do log
        for entry in log.recover()
            .map_err(|e| AuditError::Persistence(e.to_string()))? {
            let decision: ArchitecturalDecision = postcard::from_bytes(&entry)
                .map_err(|e| AuditError::Serialization(e.to_string()))?;
            audit.record(decision)?; // re-hashing para consistencia
        }

        audit.log = Some(log);
        Ok(audit)
    }

    /// Registra uma decisao, encadeando-a a cabeca da cadeia.
    /// Se houver log de persistencia, escreve em disco com fsync.
    pub fn record(&mut self, mut decision: ArchitecturalDecision) -> Result<DecisionHash, AuditError> {
        // Verifica quiescencia
        if self.quiescence == QuiescenceState::Quiescent {
            return Err(AuditError::Quiescent);
        }

        decision.previous_decision_hash = decision.previous_decision_hash.or(self.head);

        let serialized = postcard::to_stdvec(&decision)
            .map_err(|e| AuditError::Serialization(e.to_string()))?;
        let hash = DecisionHash(*blake3::hash(&serialized).as_bytes());
        let id = decision.id;

        decision.decision_hash = hash;

        if let Some(prev_hash) = decision.previous_decision_hash {
            self.next_index.insert(prev_hash, id);
        }

        self.hash_to_id.insert(hash, id);
        self.id_to_hash.insert(id, hash);
        self.decisions.insert(id, decision);

        if self.tail.is_none() {
            self.tail = Some(hash);
        }
        self.head = Some(hash);

        // Persiste em disco se log estiver configurado
        if let Some(ref mut log) = self.log {
            let entry = postcard::to_stdvec(self.decisions.get(&id).unwrap())
                .map_err(|e| AuditError::Serialization(e.to_string()))?;
            log.append(&entry)
                .map_err(|e| AuditError::Persistence(e.to_string()))?;
        }

        // Verifica forks apos cada insercao
        self.check_and_handle_forks()?;

        Ok(hash)
    }

    /// Travessia do mais recente (head) ao mais antigo (tail).
    pub fn trail_backwards(&self) -> Vec<&ArchitecturalDecision> {
        let mut trail = Vec::new();
        let mut current_hash = self.head;
        while let Some(hash) = current_hash {
            let id = match self.hash_to_id.get(&hash) {
                Some(id) => *id,
                None => break,
            };
            let decision = match self.decisions.get(&id) {
                Some(d) => d,
                None => break,
            };
            trail.push(decision);
            current_hash = decision.previous_decision_hash;
        }
        trail
    }

    /// Travessia do mais antigo (tail) ao mais recente (head).
    pub fn trail_forwards(&self) -> Vec<&ArchitecturalDecision> {
        let mut trail = Vec::new();
        let mut current_id = self.tail.and_then(|h| self.hash_to_id.get(&h).copied());
        while let Some(id) = current_id {
            let decision = match self.decisions.get(&id) {
                Some(d) => d,
                None => break,
            };
            trail.push(decision);
            current_id = self.next_index.get(&decision.decision_hash).copied();
        }
        trail
    }

    /// Cadeia cronologica (audit trail imutavel).
    pub fn trail_chronological(&self) -> Vec<&ArchitecturalDecision> {
        self.trail_forwards()
    }

    /// Decisoes ativas (grafo de vigencia).
    pub fn trail_current(&self) -> Vec<&ArchitecturalDecision> {
        self.decisions
            .values()
            .filter(|d| matches!(d.status, crate::architectural_decision::DecisionStatus::Accepted))
            .collect()
    }

    // ==================== I76.1 — FORK RESOLUTION ====================

    /// Detecta forks: múltiplas decisoes que nao sao predecessor de ninguem.
    pub fn detect_forks(&self) -> Vec<Vec<&ArchitecturalDecision>> {
        let mut heads: Vec<DecisionHash> = Vec::new();
        for (hash, _) in &self.hash_to_id {
            if !self.next_index.contains_key(hash) {
                heads.push(*hash);
            }
        }
        if heads.len() <= 1 {
            return Vec::new();
        }

        let mut forks: Vec<Vec<&ArchitecturalDecision>> = Vec::new();
        for head in heads {
            let mut chain = Vec::new();
            let mut current = Some(head);
            while let Some(hash) = current {
                if let Some(id) = self.hash_to_id.get(&hash) {
                    if let Some(decision) = self.decisions.get(id) {
                        chain.push(decision);
                        current = decision.previous_decision_hash;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }
            forks.push(chain);
        }
        forks
    }

    /// Verifica forks e entra em quiescencia se nao resolvido.
    fn check_and_handle_forks(&mut self) -> Result<(), AuditError> {
        let forks = self.detect_forks();
        if forks.len() > 1 {
            self.quiescence = QuiescenceState::ForkDetected;
            self.quiescence_since = Some(
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs()
            );
        }
        Ok(())
    }

    /// Resolve fork: aceita a cadeia com maior timestamp no head, depois maior comprimento.
    /// Se quiescencia > 30s e fork nao resolvido, retorna erro.
    pub fn resolve_fork(&mut self) -> Result<Vec<ArchitecturalDecision>, AuditError> {
        let mut heads: Vec<DecisionHash> = Vec::new();
        for (hash, _) in &self.hash_to_id {
            if !self.next_index.contains_key(hash) {
                heads.push(*hash);
            }
        }
        if heads.len() <= 1 {
            let mut trail = Vec::new();
            let mut current_hash = self.head;
            while let Some(hash) = current_hash {
                let id = match self.hash_to_id.get(&hash) {
                    Some(id) => *id,
                    None => break,
                };
                let decision = match self.decisions.get(&id) {
                    Some(d) => d,
                    None => break,
                };
                trail.push(decision.clone());
                current_hash = decision.previous_decision_hash;
            }
            self.quiescence = QuiescenceState::Active;
            self.quiescence_since = None;
            return Ok(trail);
        }

        let mut forks: Vec<Vec<ArchitecturalDecision>> = Vec::new();
        for head in heads {
            let mut chain = Vec::new();
            let mut current = Some(head);
            while let Some(hash) = current {
                if let Some(id) = self.hash_to_id.get(&hash) {
                    if let Some(decision) = self.decisions.get(id) {
                        chain.push(decision.clone());
                        current = decision.previous_decision_hash;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }
            forks.push(chain);
        }

        // Verifica timeout de quiescencia (30s)
        if let Some(since) = self.quiescence_since {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            if now - since > 30 {
                return Err(AuditError::ForkTimeout);
            }
        }

        // Critério: maior timestamp no head, depois maior comprimento
        let authoritative = forks.into_iter()
            .max_by_key(|chain| {
                let head_ts = chain.first().map(|d| d.timestamp).unwrap_or(0);
                let len = chain.len() as u64;
                (head_ts, len)
            })
            .ok_or(AuditError::ForkResolutionFailed)?;

        // Sai da quiescencia
        self.quiescence = QuiescenceState::Active;
        self.quiescence_since = None;

        Ok(authoritative)
    }

    /// Verifica integridade da cadeia.
    pub fn verify_chain(&self) -> Result<(), AuditError> {
        for (id, decision) in &self.decisions {
            if let Some(prev_hash) = decision.previous_decision_hash {
                if !self.hash_to_id.contains_key(&prev_hash) {
                    return Err(AuditError::BrokenChain {
                        decision_id: *id,
                        missing_hash: prev_hash.0,
                    });
                }
            }
            if let Some(&next_id) = self.next_index.get(&decision.decision_hash) {
                if let Some(next_decision) = self.decisions.get(&next_id) {
                    if next_decision.previous_decision_hash != Some(decision.decision_hash) {
                        return Err(AuditError::InconsistentNextPointer {
                            decision_id: *id,
                            next_id,
                        });
                    }
                }
            }
        }
        Ok(())
    }

    pub fn successor(&self, hash: DecisionHash) -> Option<&ArchitecturalDecision> {
        let next_id = self.next_index.get(&hash)?;
        self.decisions.get(next_id)
    }

    pub fn predecessor(&self, hash: DecisionHash) -> Option<&ArchitecturalDecision> {
        let id = self.hash_to_id.get(&hash)?;
        let decision = self.decisions.get(id)?;
        let prev_hash = decision.previous_decision_hash?;
        let prev_id = self.hash_to_id.get(&prev_hash)?;
        self.decisions.get(prev_id)
    }

    pub fn contains(&self, id: &Uuid) -> bool {
        self.decisions.contains_key(id)
    }

    pub fn len(&self) -> usize { self.decisions.len() }
    pub fn is_empty(&self) -> bool { self.decisions.is_empty() }
}

impl Default for ArchitecturalAudit {
    fn default() -> Self { Self::new() }
}

#[derive(Debug, thiserror::Error)]
pub enum AuditError {
    #[error("falha na serializacao: {0}")]
    Serialization(String),
    #[error("cadeia quebrada na decisao {decision_id}: hash anterior {missing_hash:?} nao encontrado")]
    BrokenChain { decision_id: Uuid, missing_hash: [u8; 32] },
    #[error("ponteiro 'next' inconsistente: decisao {decision_id} aponta para {next_id} com previous_hash incompativel")]
    InconsistentNextPointer { decision_id: Uuid, next_id: Uuid },
    #[error("falha de persistencia: {0}")]
    Persistence(String),
    #[error("sistema em quiescencia — nenhuma decisao pode ser registrada ate resolucao")]
    Quiescent,
    #[error("fork nao resolvido em 30s — intervencao manual necessaria")]
    ForkTimeout,
    #[error("falha na resolucao de fork")]
    ForkResolutionFailed,
}
