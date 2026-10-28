# Architecture — Project ARGUS (Modular Monolith)

Stable architectural decisions for Project ARGUS (Adversarially Robust
Graph-based Unified Screening for Synthetic Identity KYC Fraud Detection).
Treat entries here as load-bearing: other modules and tasks assume they hold.

---

## 1. Module Map

```
app/
├── core/                  — Domain interfaces (Protocol/ABC), config, shared types, base errors.
│                            No framework or vendor-specific imports.
├── infrastructure/        — Concrete database sessions, cache/rate limiting, artifact/file storage.
│                            (No external message brokers; pure PostgreSQL lease queue).
├── modules/
│   ├── identity/          — User authentication, Argon2id, JWT sessions, API keys, role-based access.
│   ├── kyc/               — KYC application ingestion, applicant state machine, PII pseudonymization.
│   ├── graph/             — Relational identity graph, bounded 2-hop ego-networks (NetworkX), ring detection.
│   ├── forensics/         — Document OCR extraction, field consistency, tampering detection adapters.
│   ├── fusion/            — Multi-source evidence fusion models (M0 Rules, M1 Tabular, M2 Graph, M3 Fusion).
│   ├── investigation/     — Case management, fraud ring review queues, auditable decision history.
│   └── evaluation/        — Controlled corruption benchmarks (clean, missing links, camouflage), metrics reporting.
├── worker/                — Reliable lease-based job worker with explicit handler registry.
└── main.py                — Application bootstrap, router composition, exception handlers, telemetry.
```

---

## 2. Interfaces / Contracts

### `ForensicExtractor` (Protocol)
- `extract_fields(document_bytes: bytes, mime_type: str) -> ExtractedDocument`
- `assess_tampering(document_bytes: bytes, mime_type: str) -> TamperingSignal`
- Consumed by: `modules/kyc`, `modules/fusion`. Implemented by: `modules/forensics`.
- Adding a new document OCR or forgery model requires implementing this protocol; core KYC flow never imports vision libraries directly.

### `IdentityGraphEngine` (Protocol)
- `add_identity_node(applicant_id: str, attributes: dict[str, str]) -> None`
- `find_linked_clusters(applicant_id: str, depth: int = 2) -> GraphSubnetwork`
- `compute_graph_features(applicant_id: str) -> GraphFeatureVector`
- Consumed by: `modules/fusion`, `modules/investigation`. Implemented by: `modules/graph`.
- Guarantee: Only loads bounded 2-hop ego-networks from PostgreSQL; never holds an unconstrained global graph in memory.

### `FraudModel` (Protocol)
- `predict_risk(features: ApplicationEvidence) -> RiskAssessment`
- Guarantee: Returns calibrated `risk_score` (0.0 to 1.0), `risk_tier` (`APPROVE`, `REVIEW`, `REJECT`), and `evidence_attributions`.
- Consumed by: `modules/kyc`, `modules/investigation`. Implemented by: `modules/fusion` (`M0_Rules`, `M1_Tabular`, `M2_Graph`, `M3_Fusion`).

### `ArtifactStore` (Protocol)
- `save_artifact(applicant_id: str, artifact_type: str, data: bytes, mime_type: str) -> str`
- `load_artifact(storage_uri: str) -> bytes`
- Guarantee: Handles files outside database rows to prevent PostgreSQL table/WAL bloat.

---

## 3. Boundaries & Invariant Rules

1. **PII Minimization & Pseudonymization at Ingestion Boundary:**
   - Raw identity attributes (Aadhaar, SSN, phone numbers, email addresses, national IDs) must be pseudonymized via salted HMAC-SHA256 before being stored in the identity graph or exported in logs.
   - Core domain models reference pseudonymized identifiers (`identity_hash`, `device_fingerprint_hash`).
2. **Dual-Plane Separation:**
   - Synchronous Plane: `POST /api/v1/kyc/applications` executes instant validation, PII pseudonymization, deterministic rules (M0), and immediate 1-hop graph lookup in < 200ms.
   - Asynchronous Plane: Heavy forensic extraction (OCR, image tampering) and 2-hop graph ring recalculations execute in the background worker via PostgreSQL lease claims.
3. **No Dynamic Code or Unbounded Payloads:**
   - Worker handlers are strictly registered via an explicit Handler Registry. No `eval`, dynamic imports, or arbitrary callable execution.
   - Binary files (images/PDFs) must never be stored inside PostgreSQL `JSONB` columns. They are written to `ArtifactStore` and referenced by URI.
4. **Resilience & Missing-Signal Discipline:**
   - Missing evidence (e.g. absent biometric signal or unreadable document) must be explicitly recorded as `EvidenceStatus.UNAVAILABLE`, never silently defaulted to clean/passed.
   - The fusion model must explicitly support missing signals without crashing or returning false confidence.
5. **Biometric Scope Discipline (Critique Finding 1):**
   - Biometrics verify facial consistency between document and selfie, and local device-unlock possession. They do not constitute legal proof of genuine identity and are never used as a single deterministic decision factor.
6. **Bounded Transient Ego-Networks (Critique Finding 2):**
   - Never load a global graph into process memory. Subgraph operations in `NetworkX` must load only bounded 2-hop ego-networks queried from indexed PostgreSQL `applicant_edges` rows, compute metrics, and release memory immediately.
7. **Zero Broker Dependency (Critique Finding 4):**
   - RabbitMQ and Kafka adapters are disabled. PostgreSQL `FOR UPDATE SKIP LOCKED` row locking is the sole, authoritative queue mechanism for all asynchronous jobs, preventing broker timeout cascades and deployment complexity.
8. **Dataset Provenance & Clean UI Standard:**
   - The customer-facing KYC onboarding console (`kycform`) and the internal compliance investigation console (`dashboard`) operate with clean production-grade contracts with zero "mock" or "simulated" disclaimers.
   - Reproducible adversarial evaluation scenarios (synthetic identity rings, AI-forged documents, and genuine statutory applicants) are generated via deterministic backend scenario seeders (`scripts/seed_demo_scenarios.py`) to feed live, real-time forensic detection and graph cluster analysis.

---

## 4. Decisions Log

### 2026-10-28 — Dual-Plane Modular Monolith Architecture
- **Decision:** Adopt a dual-plane architecture: Synchronous fast-path screening API for instant applicant feedback + Asynchronous worker pipeline for deep forensics and graph clustering, sharing a unified PostgreSQL database and domain model within a modular monolith.
- **Reasoning:** In automated KYC systems, applicants require immediate feedback, while fraud analysts require deep cross-applicant correlation and forensic verification.

### 2026-10-28 — Zero Broker Queue Architecture (PostgreSQL Only)
- **Decision:** Remove RabbitMQ and Kafka; execute 100% of background work via PostgreSQL `FOR UPDATE SKIP LOCKED` with per-claim lease tokens.
- **Reasoning:** Eliminates external broker container requirements, connection timeout cascades on API threads, and deployment failures during hackathon evaluation. PostgreSQL easily sustains hundreds of claims/sec.

### 2026-10-28 — Bounded Relational Graph vs Global In-Memory Graph
- **Decision:** Store typed identity edges in indexed PostgreSQL tables (`applicant_edges`). Load only bounded 2-hop ego-networks into transient `NetworkX` graphs on demand.
- **Reasoning:** Avoids memory bloat and GIL serialization under concurrent worker threads.

### 2026-10-28 — Handler Registry Pattern for Worker
- **Decision:** Replace the static class `CPUExecutionBackend` with a modular `HandlerRegistry` that allows modules to register bounded worker tasks (e.g. `kyc.document_forensics`, `graph.cluster_refresh`).
- **Reasoning:** Satisfies Open/Closed principle in `AGENTS.md`. New background tasks can be added without modifying the core worker engine.

### 2026-10-28 — KYC Domain Adaptation & Hard Override Fusion Architecture
- **Decision:** Decouple M3 Fusion from Kaggle e-commerce transaction schemas (`card1`, `TransactionAmt`). In our KYC domain, `m1_prob` is populated from applicant behavioral velocity and `m2_prob` is populated from the relational graph engine's ego-density and neighbor contagion risk. Enforce a two-tier gate:
  1. Deterministic Hard Overrides: If statutory checksum fails (Verhoeff $D_5$ / PAN format), C2PA marks media as AI-generated, or card is non-statutory $\implies$ immediate deterministic `REJECT`.
  2. Probabilistic Fusion: Valid inputs proceed to the calibrated `ArgusMLPFusion` neural network.
- **Reasoning:** Prevents ungrounded mock transaction values from injecting noise, and prevents neural network probability calibration from failing open on mathematically proven document forgery.

### 2026-10-28 — React KYC Frontend Integration & Multi-Source Evidence Contract
- **Decision:** Integrate the React + Vite frontend (`kycform`) with 100% visual and structural consistency. Expose unified backend routes conforming to the frontend's contract:
  1. `POST /api/kyc/liveness/session`: Returns signed/database-backed evidence session reference.
  2. `POST /api/kyc/liveness/verify`: Ingests multipart telemetry (`challengesCompleted`, `antiSpoof`, `facePhoto`, `videoEvidence`), stores binaries in `ArtifactStore`, and returns biometric verification verdict.
  3. `POST /api/kyc/applications`: Accepts complete KYC application, executes PII pseudonymization, populates relational graph `ApplicantNode` and `ApplicantEdge` (including `FACE_REUSE_DETECTED` and shared identifiers), and triggers multi-source verification.
  4. `GET /api/kyc/applications/{ref}/result`: Dynamically computes verification check items (`Document Verification`, `Extracted Field Consistency`, `Face Comparison`, `Liveness & Anti-Spoofing`, `Cross-Application Identity Correlation`, `Behavioural Analysis`), risk score (0–100), and recommended action.
  5. Configure Vite proxy for local development (`/api` $\to$ `http://localhost:8000`) and support FastAPI static mount for single-port production delivery.
- **Reasoning:** Maintains absolute UI fidelity while replacing client-side mock delays and simulated verdicts with genuine real-time backend forensics, biometric comparison, and graph correlation.

### 2026-10-29 — Admin Intelligence Dashboard & Multi-Role RBAC Architecture
- **Decision:** Integrate the VeriYID Admin Side Dashboard (`dashboard/`) as the authoritative investigation and compliance console for Project ARGUS. Backed by modular monolith endpoints:
  1. Multi-Role RBAC & Email Auth: Supported roles (`admin`, `senior_analyst`, `compliance_officer`, `auditor`). Email + Argon2id credentials with JWT token issuance, session persistence, and full user lifecycle management (`/api/v1/auth/users`).
  2. Dynamic Aggregation Engine (`/api/v1/dashboard/metrics`, `/api/v1/dashboard/analytics`): Aggregates live KPI numbers (Total Applications, Pending Reviews, Flagged Fraud Rings, Rejection Rate) directly from indexed `kyc_applications`, `applicant_nodes`, and `applicant_edges` tables.
  3. Case Management & Immutable Audit Trail (`/api/v1/dashboard/applications/{id}/decision`): Case adjudication (`verified`, `flagged`, `review_required`) appends immutable history events containing analyst actor identity, timestamp, action, and justification notes.
  4. Live Community & Ring Intelligence (`/api/v1/dashboard/clusters`): Executes `CommunityDetector` on graph edges to return live fraud rings (bipartite projections, cliques) and shared identifier clusters (phone, device, email, ArcFace face reuse).
- **Reasoning:** Replaces static client-side mock fixtures with live, explainable evidence aggregation while maintaining 100% visual fidelity to the dashboard UI design system.
### 2026-10-29 — LightGBM Calibrated M3 Fusion Engine & Model Observability Architecture
- **Decision:** Adopt the trained LightGBM `m3_fusion.joblib` booster with Isotonic Calibration as the statistical fusion engine behind deterministic statutory hard-overrides:
  1. Deterministic Statutory Overrides Execute First: Mathematical Verhoeff checksum failure on Aadhaar, PAN format mismatch, severe OCR contradiction ($\le 0.20$), or C2PA AI generation badges trigger an immediate hard `REJECT` (risk score `1.0`).
  2. Probabilistic Decisioning: Valid documents execute the calibrated LightGBM M3 fusion model over the 10-dimensional `M3FeatureVector`. Operational tiers:
     - `APPROVE`: Calibrated score $< 0.25$
     - `FLAG_REVIEW`: Calibrated score $0.25 \le \text{score} < 0.75$
     - `REJECT`: Calibrated score $\ge 0.75$
  3. Model Evals & Observability Endpoint: Expose `GET /api/v1/dashboard/benchmarks` serving the multi-seed evaluation metrics, ROC/PR curves, ablation lift (+0.077 graph lift, +0.137 fusion lift), feature gain importances, and adversarial attack matrix (Edge deletion, Camouflage, KYC evasion) from `benchmark_report.json`. Render an interactive "Model Evals & Benchmarks" page in the Admin Dashboard (`/benchmarks`) and a SHAP-style M3 attribution breakdown in the Application Forensic Dossier (`/applications/:id`).
- **Reasoning:** Replaces arbitrary linear point additions with empirical tree-based interactions while maintaining non-negotiable statutory compliance. Exposing real benchmark distributions directly in the UI establishes transparency and reproducibility for hackathon judges and compliance auditors.
