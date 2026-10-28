# Project Plan — Project ARGUS (Modular Monolith)

Persistent source of truth for Project ARGUS (Adversarially Robust Graph-based
Unified Screening for Synthetic Identity KYC Fraud Detection).

---

## Goal

Build an explainable, multi-source synthetic identity fraud detection platform
and modular monolith backend that uncovers coordinated fraud rings across documents,
relational graphs, biometrics, and ongoing behavioral events, validated with
reproducible adversarial robustness benchmarks.

---

## Division of Labor & Priority Queue

- **Agent (Backend & Platform Lead)**:
  1. Solidify modular monolith core, configuration, database schemas, and `ArtifactStore`.
  2. Implement PII pseudonymization (salted HMAC) and indexed relational graph persistence (`applicant_edges`).
  3. Build the zero-broker PostgreSQL lease worker with extensible `HandlerRegistry`.
  4. Implement KYC ingestion endpoints, 1-hop synchronous rules (M0), and 2-hop bounded ego-network extraction.
  5. Build analyst investigation APIs, case queues, and report exports.
  6. Deliver responsive Web Application interface for applicant submission and analyst graph exploration.

- **User / ML Lead (Model Training & Evaluation)**:
  1. Train and tune M1 (Tabular LightGBM) on applicant features.
  2. Train and tune M2 (Graph-enhanced LightGBM) on NetworkX topological features.
  3. Train and tune M3 (Multi-source Calibrated Fusion) with explicit missing-evidence indicators.
  4. Run benchmark evaluations on original Neo4j and BAF datasets.

---

## Current Phase

**Phase 8 — Admin Intelligence Dashboard & Multi-Role RBAC Integration**

---

## Status

- [x] Phase 1 — Foundation & Platform Hardening (Zero-Broker, ArtifactStore, PII Security)
- [x] Phase 2 — Relational Identity Graph & Bounded Ego-Network Engine
- [x] Phase 3 — Document Forensics & Evidence Adapters (3.1–3.6 Complete)
- [x] Phase 4 — Multi-Source Fusion & Machine Learning Model Contracts (4.1–4.2 Complete)
- [ ] Phase 5 — Continuous Monitoring & Case Investigation API
- [ ] Phase 6 — Adversarial Robustness & Experimental Benchmark Suite
- [x] Phase 7 — Unified Responsive Web Console & End-to-End Rehearsal (7.1 KYC Form Integration Complete)
- [x] Phase 8 — Admin Intelligence Dashboard & Multi-Role RBAC Integration (8.1–8.5 Complete)

---

## Phase Breakdown 

### Phase 1 — Foundation & Platform Hardening
- [x] **1.1 Platform Core & Storage Engine**: Adapt `backend-platform-benchmark` core into a clean modular monolith; add `ArtifactStore` for secure binary document storage outside PostgreSQL; add PII pseudonymization (salted HMAC-SHA256); remove RabbitMQ/Kafka dependencies in favor of pure PostgreSQL lease queue.
- [x] **1.2 Identity & Role-Based Access**: Integrate secure user authentication, analyst roles, API key management, and session handling.
- [x] **1.3 Extensible Worker & Handler Registry**: Implement open/closed `HandlerRegistry` supporting cooperative timeout checks, bounded execution, and PostgreSQL `FOR UPDATE SKIP LOCKED` claims.

### Phase 2 — Relational Identity Graph & Bounded Ego-Network Engine
- [x] **2.1 Relational Graph Schema**: Implement indexed `applicant_nodes` and `applicant_edges` database tables in PostgreSQL.
- [x] **2.2 Bounded 2-Hop Ego-Network Extractor**: Implement targeted SQL queries that extract only the 2-hop neighborhood of an applicant into a transient NetworkX graph, avoiding global in-memory graph bloat.
- [x] **2.3 Fast Synchronous 1-Hop Rule Engine**: Query 1-hop identifier degree in <15ms during application ingestion; instantly flag reused phones/devices or confirmed fraud links under M0.
- [x] **2.4 Ring & Community Detection**: Implement connected component analysis and clique density algorithms on extracted ego-networks.

### Phase 3 — Document Forensics & Evidence Adapters
- [x] **3.1 Document Ingestion & Artifact Validation**: Multipart document and selfie upload endpoints with MIME validation, magic byte checks, and bounded file sizes (10MB).
- [x] **3.2 OCR & Field Contradiction Detector**: Extract text fields (name, DOB, ID number) and check internal consistency against claimed application data using Levenshtein distance and checksums.
- [x] **3.3 Image Tampering, AI-Signal & Face Consistency Adapters**:
  - **P0 Fast-plane signals (sync path, Pillow only):** image dimension anomaly (AI generator fixed sizes vs. camera photo), EXIF metadata anomaly (missing/AI-tool software tags), JPEG quality factor check (round quality values from generators vs. camera profiles). All return `EvidenceStatus.ANOMALOUS / PRESENT / UNAVAILABLE` — never a bare float.
  - **P1 Slow-plane signals (async worker jobs):** Error Level Analysis (ELA) for paste/edit forgery on JPEG documents; FFT spectral analysis for GAN frequency artifacts; InsightFace face swap detection + cosine embedding similarity between document face crop and selfie; TruFor document-forgery localization model (selected over UniversalFakeDetect — see `FORENSICS_DESIGN.md §2.7`).
  - **P3 Deferred:** C2PA manifest verification (near-absent in Indian KYC fraud tooling; > 99% NO_MANIFEST rate — zero discriminative value for this threat model). UniversalFakeDetect (severe distribution shift to identity document images; uncalibrated on this input domain).
  - Media forensics scores route to analyst evidence annotations only — NOT into M3 fusion — until calibration against labeled documents is complete (see `FORENSICS_DESIGN.md §4`).
- [x] **3.4 Real Face Embedding Adapter (InsightFace ONNX)**: Replaced 64×64 pixel cosine with InsightFace `buffalo_sc` ArcFace 512-d embeddings. Lazy singleton, graceful `UNAVAILABLE` fallback, passive liveness proxy (bbox ratio). `compute_face_embedding_similarity` removed from `image.py`. New `face.py` + 16 unit tests. `requirements.txt` created.
- [x] **3.5 Face Deduplication Index (ChromaDB local)**: Stored ArcFace 512-d embeddings in a ChromaDB collection keyed by pseudonymized `applicant_id`. Implemented `FaceDeduplicationIndex` in `app/modules/forensics/face_index.py` with cosine distance metric (`hnsw:space: cosine`). Query nearest neighbours with cosine distance < 0.35 (similarity > 0.65) to detect biometric reuse under different Aadhaar/PAN cards. Implemented `create_face_reuse_edges` returning `ApplicantEdge` with `EdgeType.FACE_REUSE_DETECTED`. Added `chroma_persist_dir` setting and `FaceMatch` dataclass in `app/core/forensics.py`. 12 unit tests passing in `test_forensics_face_index.py`.
- [x] **3.6 Cross-Source Contradiction Detector**: Implemented `CrossSourceContradictionDetector` in `app/modules/forensics/contradiction.py`. Correlates Name (Levenshtein), DOB (ISO parser & feasibility), PAN statutory structure (4th char entity type 'P', 5th char surname initial), Driving Licence RTO state prefix vs. address state, biometric face deduplication reuse (< 0.35 distance), and foreign IP geolocation. Consolidated into `ContradictionReport` with structured `ContradictionCheck` items and calibrated rule score. 14 unit tests passing in `test_forensics_contradiction.py`.

### Phase 4 — Multi-Source Fusion & Machine Learning Model Contracts
- [x] **4.1 Baseline M0 (Deterministic Rules)**: Rule-based screening engine covering identifier reuse, field mismatch, and velocity anomalies.
- [x] **4.2 KYC Feature Vectorizer & Domain Adaptation**: Extract and serialize the authoritative 10-dimensional M3 feature vector (`X_M3`) from live KYC evidence (behavioral velocity, 2-hop ego-network risk, M0 rule score, OCR contradiction, Verhoeff/PAN checksum validity, ELA tampering, face cosine distance, and missingness indicators), decoupling fusion from e-commerce schemas.
- [ ] **4.3 Proposed M3 Calibrated Multi-Source Fusion & Hard Override Engine**: Implement `ArgusM3FusionEngine` loading `m3_fusion.joblib` with calibrated operational thresholds (`APPROVE < 0.25`, `FLAG_REVIEW 0.25–0.75`, `REJECT ≥ 0.75`) and deterministic hard-override rejection for invalid statutory checksums (Verhoeff/PAN), synthetic C2PA AI generation, and unverified identity. Conforms to `FraudModel` protocol.

### Phase 5 — Continuous Monitoring & Case Investigation API
- [ ] **5.1 Post-KYC Event Ingestion Pipeline**: Ingestion API for post-onboarding lifecycle events (`account_activated`, `device_changed`, `transaction_velocity_spike`).
- [ ] **5.2 Analyst Queue & Case Management API**: Endpoints for priority fraud review queue, case decisions (`APPROVE`, `FLAG_REVIEW`, `CONFIRM_FRAUD`), and audit history.
- [ ] **5.3 Exportable Compliance & Case Reports**: Generate structured JSON and Markdown case dossiers with evidence attribution and linked graph paths.

### Phase 6 — Adversarial Robustness & Experimental Benchmark Suite
- [ ] **6.1 Benchmark Metrics & Evaluation Backend API**: Endpoints (`GET /api/v1/dashboard/benchmarks`, `POST /api/v1/dashboard/benchmarks/evaluate`) exposing multi-seed PR-AUC, ROC-AUC, Brier score, ECE, ablation lift (+0.077 graph lift, +0.137 fusion lift), feature gain importances, and adversarial attack matrix (Edge deletion, Camouflage, KYC evasion) from `benchmark_report.json` and live evaluation harness.
- [ ] **6.2 Automated Benchmark CLI & Reproducibility Harness**: One-command evaluation script (`scripts/evaluate_models.py`) verifying latency (2.5 µs), leak-free test performance, and confusion matrices on `synthetic_kyc_dataset.csv.gz`.

### Phase 7 — Unified Responsive Web Console & KYC Form Integration
- [x] **7.1 Biometric Liveness Session & Full Application Endpoints**: Implemented multipart/Base64 ingestion in `app/modules/kyc/router.py`.
- [x] **7.2 Dynamic Multi-Source Verification Result Engine**: Implemented `GET /api/kyc/applications/{ref}/result`.
- [x] **7.3 Frontend Dynamic Wiring & Vite Proxy Integration**: Configured Vite proxy in `kycform/vite.config.ts`.

### Phase 8 — Admin Intelligence Dashboard & Multi-Role RBAC Integration
- [x] **8.1 Multi-Role Authentication & Staff User Management Backend API**: Seeded default staff accounts with Argon2id and JWT HS256 tokens.
- [x] **8.2 Dynamic Dashboard Core Metrics, Analytics & Queue Backend Endpoints**: Real analytics and metrics queries.
- [x] **8.3 Forensic Dossier, Case Adjudication & Fraud Ring Intelligence Backend Endpoints**: Full case adjudication and cluster intelligence.
- [x] **8.4 Dashboard Authentication Context & Dynamic Service Integration**: Real auth context and dynamic API service.
- [x] **8.5 Full System Integration, Realistic Seed Scenarios, UI Cleanliness & End-to-End Rehearsal**: Cleaned simulation copy, created `scripts/seed_demo_scenarios.py`, verified unit tests.
- [ ] **8.6 Model Benchmarks, Evals & Explainability Console**: Interactive "Model Evals & Benchmarks" page in admin dashboard (`/benchmarks`) displaying PR-AUC/ROC curves, ablation table, adversarial robustness under attacks, interactive what-if scoring simulator, and M3 attribution breakdown in `ApplicationDetailPage.tsx`.

---

## Current Task

**Task ID:** 4.3

**Goal:** Implement `ArgusM3FusionEngine` loading `m3_fusion.joblib` (LightGBM Booster + Isotonic Calibration) with operational risk tiers and deterministic hard-override gates.

**Inputs:** `argus/New_models/m3_fusion.joblib`, `app/modules/fusion/features.py` (`M3FeatureVector`), `ARCHITECTURE.md` §2 (`FraudModel` protocol), `app/core/fusion.py`.

**Output:** `app/modules/fusion/m3_model.py`, `app/modules/fusion/__init__.py`, `tests/unit/test_fusion_m3.py`.

**Constraints:**
- Conforms to `FraudModel` domain protocol: `predict_risk(features: ApplicationEvidence) -> RiskAssessment`.
- Deterministic statutory hard-overrides execute first:
  1. Failed statutory checksum (Verhoeff $D_5$ on Aadhaar, PAN format) $\implies$ immediate hard `REJECT (risk=1.0)`.
  2. Severe OCR mismatch ($\le 0.20$) $\implies$ immediate hard `REJECT (risk=1.0)`.
  3. C2PA synthetic AI generation flags $\implies$ immediate hard `REJECT (risk=1.0)`.
- If no hard override triggers, passes `M3FeatureVector` into `m3_fusion.joblib` (LightGBM booster + isotonic calibrator).
- Calibrated operational risk thresholds:
  - `APPROVE`: calibrated score $< 0.25$
  - `REVIEW`: calibrated score $0.25 \le \text{score} < 0.75$
  - `REJECT`: calibrated score $\ge 0.75$
- Returns structured reason attributions and component scores (`m1_prob`, `m2_prob`, `m0_score`).
- Lazy singleton model loader with graceful fallback if `.joblib` is unavailable.

**Verification:** Unit tests in `tests/unit/test_fusion_m3.py` asserting hard overrides reject immediately, clean vectors approve, edge cases evaluate deterministically, and execution time is sub-millisecond.

**Depends on:** 4.2 (complete)

---

## Next Task

**Task ID:** 6.1 — Benchmark Metrics & Evaluation Backend API (`GET /api/v1/dashboard/benchmarks`)

---

## Constraints

- Python 3.11+ compatible.
- All core logic type-hinted; no bare `Any` without concrete justification.
- Pure unit tests must run without requiring a live external PostgreSQL/Docker instance (using in-memory SQLite / mock stores).
- Integration tests isolate PostgreSQL-specific functionality.
- Dependencies: FastAPI, Pydantic v2, SQLAlchemy 2.0, LightGBM, NetworkX, Scikit-learn, ChromaDB, InsightFace.

---

## Log

### 2026-10-29 — Task 8.5 complete (Full System Integration, Realistic Seed Scenarios, UI Cleanliness & End-to-End Rehearsal)
- Changed: Completely purged all simulation/mock badges and copy across `kycform/` (`VerificationResultsPage.tsx`, `VerificationCheckList.tsx`, `ReviewForm.tsx`, `services/kycApi.ts`, `types/kyc.ts`). Changed `emptyBiometric.livenessMode` to `'live'`, removed `'simulated'` CheckStatus, and replaced old hackathon disclaimer notes with clean, official verification status copy. Audited `dashboard/` and confirmed 0 simulation buttons or mock banners. Built standalone idempotent scenario seeder `scripts/seed_demo_scenarios.py` generating 3 contrasting scenarios: Clean Genuine applicants (verified, score 0.04), AI Document Forgery attacks (C2PA GenAI manifest, pseudo-QR hallucination, score 0.98), and a Coordinated Multi-Source Synthetic Identity Ring (3 applicants sharing phone number, device fingerprint, and ArcFace biometric face reuse). Built automated end-to-end integration test suite `tests/unit/test_end_to_end_dashboard_flow.py` covering staff login, metrics aggregation, queue search/filters, forensic dossier detail, cluster detection, and case adjudication with audit trails. Fixed normalized risk score scaling bug in `serialize_application` (`score_pct = raw_score * 100.0 if raw_score <= 1.0 else raw_score`).
- Files: `kycform/src/types/kyc.ts`, `kycform/src/pages/VerificationResultsPage.tsx`, `kycform/src/components/results/VerificationCheckList.tsx`, `kycform/src/components/form/ReviewForm.tsx`, `kycform/src/services/kycApi.ts`, `scripts/seed_demo_scenarios.py`, `tests/unit/test_end_to_end_dashboard_flow.py`, `app/modules/investigation/service.py`, `PROJECT_PLAN.md`, `ARCHITECTURE.md`.
- Verified: Both frontend bundles compiled with 0 errors (`npm run build` in `kycform/` and `dashboard/`); `test_end_to_end_dashboard_flow.py` passed 6/6; full backend test suite passed **221/221** in 21.26s (`python3 -m pytest tests/unit/ -q`); `python3 -m ruff check app tests scripts` passed with 0 errors.

### 2026-10-29 — Task 8.4 complete (Dashboard Authentication Context & Dynamic Service Integration)
- Changed: Configured dev proxy in `dashboard/vite.config.ts` (`/api` -> `http://localhost:8000`). Implemented `authService.ts` calling `/api/v1/auth/login` and `/api/v1/auth/me`. Created `AuthContext.tsx` providing in-memory JWT token storage, user profile state, `login()`, `logout()`, and reactive sync to `setDashboardToken()`. Built `LoginPage.tsx` styled to match the dark glassmorphic VeriYID design system with one-click quick-fill demo chips for Admin, Analyst, Compliance, and Auditor roles. Added comprehensive login styling to `dashboard.css`. Updated `TopBar.tsx` to read the authenticated staff user dynamically from `useAuth()`, display dynamic initials and formatted role titles, and added an immediate logout button. Refactored `dashboardService.ts` to replace all mock `SAMPLE_*` datasets with real `fetch()` calls to backend endpoints (`/api/v1/dashboard/metrics`, `/api/v1/dashboard/applications`, `/api/v1/dashboard/applications/{id}`, `/api/v1/dashboard/applications/{id}/decision`, `/api/v1/auth/users`, `/api/v1/dashboard/analytics`, `/api/v1/dashboard/clusters`) with automatic JWT Bearer token injection. Updated `App.tsx` with `AuthProvider`, `LoginRoute`, and `ProtectedLayout` route guards.
- Files: `dashboard/vite.config.ts`, `dashboard/src/services/authService.ts`, `dashboard/src/context/AuthContext.tsx`, `dashboard/src/pages/LoginPage.tsx`, `dashboard/src/styles/dashboard.css`, `dashboard/src/components/TopBar.tsx`, `dashboard/src/services/dashboardService.ts`, `dashboard/src/App.tsx`, `PROJECT_PLAN.md`.
- Verified: `npm run build` in `dashboard/` compiled cleanly in 507ms with 0 TypeScript errors (`tsc -b && vite build`); all 215 backend unit tests passed (`python3 -m pytest tests/unit/ -q`).

### 2026-10-29 — Task 8.3 complete (Forensic Dossier, Case Adjudication & Fraud Ring Intelligence)
- Changed: Added three schemas to `app/modules/investigation/schemas.py`: `DecisionRequest`, `SharedIdentifierClusterSchema`, `FraudClusterSchema`, `FraudClustersResponseSchema`. Added three new service methods to `InvestigationService` in `service.py`: `get_application_by_id` (resolves UUID or applicant_id), `apply_decision` (writes status + audit trail to `metadata_json["history"]`), and `get_fraud_clusters` (Union-Find fraud rings + shared identifier clusters from `ApplicantEdge` rows). Added three new endpoints to `dashboard_router.py`: `GET /dashboard/applications/{app_id}`, `POST /dashboard/applications/{app_id}/decision`, `GET /dashboard/clusters`. Fixed `pytest.ini` ROS plugin disable flag (`launch_testing_ros` → `launch_ros`), resolving the longstanding INTERNALERROR on test collection.
- Files: `app/modules/investigation/schemas.py`, `app/modules/investigation/service.py`, `app/modules/investigation/dashboard_router.py`, `tests/unit/test_dashboard_case_and_clusters.py`, `pytest.ini`.
- Verified: 13/13 new tests in `test_dashboard_case_and_clusters.py` pass; full suite **215/215 passed** in 19.94s; `ruff check` 0 errors.
- Limitations: Decision audit trail stored in `metadata_json["history"]`; a dedicated audit table (with immutable INSERT-only semantics) would be the correct long-term design once a schema migration path is in place.

### 2026-10-29 — Task 8.2 complete (Dynamic Dashboard Core Metrics, Analytics & Queue Backend Endpoints)
- Changed: Implemented `app/modules/investigation/` module with `schemas.py`, `service.py`, and `dashboard_router.py`. Serializes live `KYCApplication` records into the exact `dashboard.ts:Application` shape (demographics, document, biometrics, risk assessment, history). Built `GET /dashboard/metrics` returning dynamic KPI cards (Total Applications, Verified pass rate, Pending Review backlog, Flagged Fraud Rings) with live percentage deltas. Built `GET /dashboard/applications` with pagination, text search (applicant name, ID, national ID last 4), and status/document filters. Built `GET /dashboard/analytics` returning time-series throughput, colored outcome distributions, document type distributions, and monthly fraud flag trends. Mounted router under both `/api` and `/api/v1` in `app/main.py`. Added comprehensive unit test suite in `tests/unit/test_dashboard_metrics_api.py`.
- Files: `app/modules/investigation/__init__.py`, `app/modules/investigation/schemas.py`, `app/modules/investigation/service.py`, `app/modules/investigation/dashboard_router.py`, `app/main.py`, `tests/unit/test_dashboard_metrics_api.py`, `PROJECT_PLAN.md`.
- Verified: All 4 new unit tests in `test_dashboard_metrics_api.py` and all 202 repository unit tests passed in 16.99s (`pytest tests/unit/ -q`); `ruff check` passed with 0 errors.

### 2026-10-29 — Task 8.1 complete (Multi-Role Authentication & Staff User Management API)
- Changed: Implemented Multi-Role Authentication & Staff User Management backend in `app/modules/identity/`. Updated `User` model in `models.py` with `name` and `last_login_at` fields and increased role string length. Updated `schemas.py` with `UserView`, `DashboardUserResponse`, `UserCreateRequest`, and expanded `RoleUpdate`. In `auth.py`, added `name` claim to JWT access tokens, defined `STAFF_ROLES`, and implemented `require_staff`. Created `app/modules/identity/seed.py` providing idempotent seeding of the 4 standard multi-role staff accounts (`admin@argus.internal`, `analyst@argus.internal`, `compliance@argus.internal`, `auditor@argus.internal`), role normalization, and formatting helpers. In `router.py`, added `GET /auth/me`, `GET /auth/users`, `POST /auth/users`, `DELETE /auth/users/{user_id}`, and `POST /auth/seed`. Updated `app/main.py` with async lifespan table creation and seeding, and mounted routers under both `/api` and `/api/v1`. Created comprehensive unit test suite in `tests/unit/test_identity_admin_api.py`.
- Files: `app/modules/identity/models.py`, `app/modules/identity/schemas.py`, `app/modules/identity/auth.py`, `app/modules/identity/seed.py`, `app/modules/identity/router.py`, `app/main.py`, `tests/unit/test_identity_admin_api.py`, `PROJECT_PLAN.md`.
- Verified: All 6 new unit tests in `test_identity_admin_api.py` and all 198 repository unit tests passed in 15.39s (`pytest tests/unit/ -q`); `ruff check` passed with 0 errors.

### 2026-10-28 — Task 3.6 complete
- Changed: Implemented Cross-Source Contradiction Detector in `app/modules/forensics/contradiction.py`. Defined `ContradictionCheck`, `ContradictionReport`, and `CrossSourceContradictionDetector`. Correlates: Name fuzzy similarity (R3 threshold 0.75), DOB cross-format normalization & timeline feasibility (impossible future birth dates, underage applicants), PAN statutory rules (4th char entity type 'P' vs. individual KYC, 5th char surname initial match), Driving Licence RTO state prefix vs. claimed residential state (using ISO 3166-2:IN codes), biometric face deduplication reuse (< 0.35 distance flag), and foreign IP geolocation anomaly. Exported classes in `app/modules/forensics/__init__.py`. Added comprehensive unit tests in `tests/unit/test_forensics_contradiction.py`.
- Files: `app/modules/forensics/contradiction.py`, `app/modules/forensics/__init__.py`, `tests/unit/test_forensics_contradiction.py`, `PROJECT_PLAN.md`.
- Verified: All 14 unit tests in `test_forensics_contradiction.py` and all 189 repository unit tests passed in 13.36s (`pytest tests/unit/ -q`); `ruff check` passed with 0 errors.
- Limitations: Geolocation check inspects ISO country code; precise GPS boundary coordinates deferred to future mobile SDK integration.

### 2026-10-28 — Task 3.5 complete
- Changed: Implemented Face Deduplication Index in `app/modules/forensics/face_index.py` using ChromaDB (`chromadb==1.5.8`). Built `FaceDeduplicationIndex` with cosine distance metric (`hnsw:space: cosine`). Indexed ArcFace 512-d embeddings keyed by pseudonymized `applicant_id`. Implemented `find_matching_faces` with cosine distance threshold (< 0.35 <=> similarity > 0.65), `find_matches_for_applicant`, `delete_face_embedding`, `reset`, and `create_face_reuse_edges` returning `ApplicantEdge` with `EdgeType.FACE_REUSE_DETECTED`. Added `chroma_persist_dir` setting to `app/core/config.py` and `FaceMatch` dataclass to `app/core/forensics.py`. Exported classes in `app/modules/forensics/__init__.py`. Added comprehensive unit tests in `tests/unit/test_forensics_face_index.py`.
- Files: `app/modules/forensics/face_index.py`, `app/core/forensics.py`, `app/core/config.py`, `app/modules/graph/models.py`, `app/modules/forensics/__init__.py`, `tests/unit/test_forensics_face_index.py`, `PROJECT_PLAN.md`.
- Verified: All 12 unit tests in `test_forensics_face_index.py` and all 175 repository unit tests passed in 13.26s (`pytest tests/unit/ -q`); `ruff check` passed with 0 errors.
- Limitations: In-memory ephemeral client used for zero-I/O test execution; persistent ChromaDB writes to `artifacts_data/chroma_face_db`.

### 2026-10-28 — Task 3.4 complete
- Changed: Implemented Real Face Embedding Adapter in `app/modules/forensics/face.py` using InsightFace ArcFace (`buffalo_sc` ONNX model, 512-d vectors). Lazy thread-safe singleton `_FaceEmbedder`, passive liveness proxy via face bounding box ratio (> 85% flags `LIVENESS_SUSPECT`), and calibrated cosine threshold (0.40). Replaced pixel cosine similarity in `app/modules/forensics/image.py`. Graceful fallback to `EvidenceStatus.UNAVAILABLE` on missing face or missing dependency. Generated `requirements.txt`.
- Files: `app/modules/forensics/face.py`, `app/modules/forensics/image.py`, `app/modules/forensics/__init__.py`, `tests/unit/test_forensics_face.py`, `tests/unit/test_forensics_image.py`, `requirements.txt`, `PROJECT_PLAN.md`.
- Verified: All 16 unit tests in `test_forensics_face.py` and all 163 repo unit tests passed in 13.09s (`pytest tests/unit/ -q`).
- Limitations: Passive liveness heuristic (bbox coverage ratio) catches large printed photo attacks but does not replace active liveness challenge-response.

### 2026-10-28 — Task 4.2 complete
- Changed: Implemented KYC Feature Vectorizer & Domain Adaptation in `app/modules/fusion/features.py`. Defined `M3FeatureVector` (10-field NamedTuple, all values ∈ [0.0, 1.0]) and stateless `KYCFeatureVectorizer` dataclass. Dimension-to-source mapping: `m1_prob` ← behavioral velocity (1h application + device velocity proxy, saturating at 10); `m2_prob` ← ego-network risk (shared-identifier degree × 4 types, fraud contagion 0.5 weight, cycle density 0.1 weight); `m0_rule_score` ← M0 deterministic proxy reconstructed from same evidence fields (superceded when real M0 score available via `extract_with_m0()`); `ocr_contradiction` ← 1 − `ocr_name_similarity`; `id_checksum_valid` ← 0.0/1.0/0.5 (valid/invalid/unknown); `tampering_ela_score` ← `ela_max_diff` / 50 (saturation point); `face_cosine_dist` ← 1 − `face_cosine_similarity`; `is_doc_missing`, `is_selfie_missing`, `is_graph_isolated` ← explicit binary missingness flags. Missing evidence falls back to 0.5 neutral mid-point (not 0.0 / not 1.0) to prevent imputation bias. Added `extract_m3_features()` module-level convenience helper. Exported `KYCFeatureVectorizer`, `M3FeatureVector`, `FEATURE_DIM`, and `extract_m3_features` from `app/modules/fusion/__init__.py`.
- Files: `app/modules/fusion/features.py`, `app/modules/fusion/__init__.py`, `tests/unit/test_fusion_features.py`, `PROJECT_PLAN.md`.
- Verified: All 46 tests in `tests/unit/test_fusion_features.py` and all 148 repository tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app/modules/fusion/features.py tests/unit/test_fusion_features.py` returned 0 errors.
- Limitations: `m1_prob` and `m2_prob` are domain-grounded proxies until KYC-labeled training data is available to retrain M1/M2 (ARCHITECTURE.md §4). The real M0 risk score should be injected via `extract_with_m0()` in the full pipeline (Task 4.3).

### 2026-10-28 — Task 4.1 complete
- Changed: Implemented Baseline M0 (Deterministic Rules Engine) in `app/modules/fusion/rules.py` conforming to `FraudModel` domain protocol in `ARCHITECTURE.md` §2. Defined `RiskTier`, `EvidenceAttribution`, `RiskAssessment`, `ApplicationEvidence`, and `FraudModel` in `app/core/fusion.py`. Created Pydantic response schemas in `app/modules/fusion/schemas.py`. In `DeterministicM0Model`: implemented multi-source rule evaluation covering confirmed fraud links (`CONFIRMED_FRAUD_LINK`), national ID collisions (`IDENTITY_REUSE_COLLISION`), tiered phone reuse (`R1_HIGH_PHONE_REUSE`, `PHONE_REUSE_MODERATE`), tiered device reuse (`R2_HIGH_DEVICE_REUSE`, `DEVICE_REUSE_MODERATE`), tampered Secure QR (`R7_SECURE_QR_TAMPERED`), invalid checksums (`R5_INVALID_ID_CHECKSUM`), OCR contradictions (`R3_NAME_CONTRADICTION`, `R4_DOB_CONTRADICTION`), face mismatch (`DOCUMENT_FACE_MISMATCH`), generative AI image signatures (`IMAGE_AI_SYNTHETIC`, `JPEG_QUALITY_SYNTHETIC`, `IMAGE_ELA_TAMPERED`, `IMAGE_FFT_GRID_ANOMALY`), and velocity bursts (`R6_VELOCITY_BURST`, `VELOCITY_MODERATE`). Added explicit missing signal tracking (`EvidenceStatus.UNAVAILABLE`) with zero score impact. Added benchmark dict helper `evaluate_m0_rules_dict` conforming to `MODELS_TRAINING_SPEC.md §3.3`.
- Files: `app/core/fusion.py`, `app/modules/fusion/schemas.py`, `app/modules/fusion/rules.py`, `app/modules/fusion/__init__.py`, `tests/unit/test_fusion_rules.py`, `PROJECT_PLAN.md`.
- Verified: All 14 tests in `tests/unit/test_fusion_rules.py` and all 96 repository tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed. Average execution time < 0.15ms per evaluation.
- Limitations: M0 is purely deterministic; statistical probability estimation and feature interactions are delegated to M1–M3 in Tasks 4.2–4.3.

### 2026-10-28 — Task 3.3 complete
- Changed: Implemented Image Tampering, AI-Signal & Face Consistency Adapters in `app/modules/forensics/image.py`. Fast-plane synchronous signals: `check_image_dimension_anomaly` (matches against standard generative AI resolutions: 1024x1024, 512x512, etc.), `check_exif_metadata_anomaly` (detects AI software signatures: Stable Diffusion, Midjourney, DALL-E, Firefly, with explicit `EvidenceStatus.UNAVAILABLE` when EXIF is stripped), `check_jpeg_quality_factor_anomaly` (inverts JPEG quantization tables to estimate original software quality factor in < 1ms), and `run_fast_plane_forensics` (< 20ms synchronous execution). Slow-plane asynchronous worker signals: `compute_error_level_analysis` (detects localized recompression differential and spliced copy-paste regions), `compute_fft_spectral_analysis` (2D FFT power spectrum for GAN periodic upsampling checkerboard grid artifacts), `compute_face_embedding_similarity` (cosine biometric similarity with explicit `EvidenceStatus.UNAVAILABLE` on missing crops), and `run_slow_plane_forensics`. Exported all functions in `app/modules/forensics/__init__.py`.
- Files: `app/modules/forensics/image.py`, `app/modules/forensics/__init__.py`, `tests/unit/test_forensics_image.py`, `LESSONS.md`.
- Verified: All 82 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed.
- Limitations: Deep neural TruFor/InsightFace models run optionally in slow-plane worker if GPU/weights are loaded; fallback CPU adapters provide robust baseline coverage without external neural weights.

### 2026-10-28 — Task 3.3 complete (Forensics, C2PA Provenance & Dynamic Document Classification)
- Changed: Implemented multi-plane forensic analysis (`app/modules/forensics/image.py`) and Universal Document Feature Extractor (`app/modules/forensics/classifier.py`). Fast-plane inspects ISO/IEC 19566-5 C2PA JUMBF boxes (`caBX` chunk in PNG and APP11 marker in JPEG) detecting Google Generative AI (Gemini/Imagen), OpenAI DALL-E, Adobe Firefly, Midjourney, and IPTC `trainedAlgorithmicMedia`; inspects ITU-T T.81 JPEG quantization tables for Q=90/95 software recompressions; inspects software metadata tags; slow-plane runs Error Level Analysis (ELA), 2D Fast Fourier Transform (FFT) periodic spectral grid detection, and facial bounding box crop. `DynamicDocumentExtractor` leverages neural ONNX OCR (RapidOCR) with OpenCV visual layout analysis to dynamically classify document types (`AADHAAR_CARD`, `PAN_CARD`, `DRIVING_LICENCE`, `PASSPORT`, `REGULAR_ID_OR_OTHER`), extract demographic fields (Name, DOB, Gender, Father's Name, VID, PIN, Mobile, Vehicle Classes), and execute mathematical/statutory checks (Aadhaar Verhoeff $D_5$ dihedral permutation check, PAN 4th entity char and 5th surname initial check, DL state RTO code check, pseudo-QR visual hallucination detection). Addressed NeurIPS 2024/2025 watermark-erasure benchmark threat model: missing watermarks/provenance are treated strictly as `EvidenceStatus.UNAVAILABLE` (unknown origin), never as authentic evidence. Integrated preset and custom upload interactive UI in `demo_argus.py`.
- Files: `app/modules/forensics/image.py`, `app/modules/forensics/classifier.py`, `app/modules/forensics/__init__.py`, `tests/unit/test_forensics_image.py`, `tests/unit/test_forensics_classifier.py`, `demo_argus.py`, `PROJECT_PLAN.md`.
- Verified: All 14 forensics unit tests passed (`tests/unit/test_forensics_classifier.py`, `tests/unit/test_forensics_image.py`); verified on real user Aadhaar (`WhatsApp Image 2026-10-28 at 18.49.11.jpeg` -> `ACCEPTABLE`, `4597 1693 9274` Verhoeff Valid, `Omdeep Deepak Borkar`, `2005-11-23`), AI Aadhaar (`4521 7890 3214` -> `REJECT`, Verhoeff checksum failed, pseudo-QR, C2PA Google GenAI), AI DL (`DL/GA/1234567` -> `REJECT`, C2PA, cross-document Aadhaar logo on DL), AI PAN (`ABCDE1234F` -> `REJECT`, 5th char surname mismatch, typo in GOVERMENT), and synthetic student campus ID (`REGULAR_ID_OR_OTHER` -> `REJECT`, non-statutory card). Streamlit demo verified 200 OK at port 8501.

### 2026-10-28 — Task 3.2 complete
- Changed: Implemented OCR extraction, Verhoeff checksum algorithm, PAN format validation, Levenshtein fuzzy demographic matching, and offline Aadhaar Secure QR RSA verification in `app/modules/forensics/`. `app/core/forensics.py`: defined `ForensicExtractor` protocol, `EvidenceStatus`, `ExtractedDocument`, and `TamperingSignal`. `app/modules/forensics/ocr.py`: `validate_verhoeff`, `compute_verhoeff_check_digit`, `validate_pan_format`, `name_similarity_ratio`, `compare_dobs`, `OCRExtractor`, and `FieldContradictionDetector` returning `R3_NAME_CONTRADICTION`, `R4_DOB_CONTRADICTION`, and `R5_INVALID_ID_CHECKSUM`. `app/modules/forensics/qr.py`: `AadhaarSecureQRVerifier` with offline 2048-bit RSA PKCS#1 v1.5 SHA-256 signature verification over 0xFF-delimited payloads, detecting tampered records (`R7_SECURE_QR_TAMPERED`) without network calls. Integrated forensics pipeline into `kyc.document_forensics` background lease worker handler.
- Files: `app/core/forensics.py`, `app/modules/forensics/schemas.py`, `app/modules/forensics/ocr.py`, `app/modules/forensics/qr.py`, `app/modules/forensics/__init__.py`, `app/modules/kyc/service.py`, `tests/unit/test_forensics_ocr.py`, `LESSONS.md`.
- Verified: All 74 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed.
- Limitations: Optical image tampering (ELA, dimensions, EXIF) will be implemented in Task 3.3.

### 2026-10-29 — Task 7.1 complete (Full KYC Frontend Form Integration & Dynamic Verification)
- Changed: Connected all frontend form fields (personal demographic details, residential & permanent address, government ID document upload, active camera biometrics/selfie, regulatory due diligence declarations) dynamically to the backend modular monolith. Added `FullKYCApplicationPayload` and dynamic `VerificationResultResponse` schemas in `app/modules/kyc/schemas.py`. Implemented Base64 dataURL artifact ingestion in `submit_full_application`, PII salted HMAC hashing, graph ingestion into SQLite (`ApplicantNode`, `ApplicantEdge`), and multi-source cross-correlation: Document format/tampering check, `CrossSourceContradictionDetector` (Name, DOB, statutory PAN 4th entity / 5th surname initial, DL state vs residential state), ChromaDB ArcFace 512-d biometric face deduplication index check, Google MediaPipe + MiniFASNet anti-spoof telemetry evaluation, and M0 graph collision rules. Implemented `POST /api/kyc/applications`, `GET /api/kyc/applications/{ref}/result`, `POST /api/kyc/liveness/session`, and `POST /api/kyc/liveness/verify` in `app/modules/kyc/router.py`. Configured Vite proxy in `kycform/vite.config.ts`. Replaced client mock timeouts with real `fetch()` calls in `kycform/src/services/kycApi.ts`.
- Files: `app/modules/kyc/schemas.py`, `app/modules/kyc/service.py`, `app/modules/kyc/router.py`, `app/main.py`, `kycform/vite.config.ts`, `kycform/src/services/kycApi.ts`, `kycform/src/components/form/BiometricVerificationForm.tsx`, `tests/unit/test_kyc_full_flow.py`.
- Verified: All 192 unit tests in repository passed in 13.69s (`pytest tests/unit/ -q`); `npm run build` compiled clean in 3.32s; `ruff check` passed with 0 errors.

### 2026-10-28 — Task 3.1 complete

- Changed: Implemented Document Ingestion & Artifact Validation module (`app/modules/kyc/`). Created `KYCApplication` ORM model storing applicant metadata, artifact storage URIs, and screening results; created `KYCApplicationCreate`, `KYCApplicationReceipt`, `KYCApplicationDetail` Pydantic schemas; implemented `KYCApplicationService` validating input formatting, enforcing 10MB bounds, validating magic bytes via `ArtifactStore`, computing salted HMAC-SHA256 digests for all PII, populating `ApplicantNode` and `ApplicantEdge` relational graph tables, executing synchronous M0 rule checks, and enqueuing background forensic extraction jobs; exposed multipart onboarding endpoints in `app/modules/kyc/router.py` (`POST /api/v1/kyc/applications`, `GET /api/v1/kyc/applications/{id}`, `GET /api/v1/kyc/applications`); registered router in `app/main.py`.
- Files: `app/modules/kyc/models.py`, `app/modules/kyc/schemas.py`, `app/modules/kyc/service.py`, `app/modules/kyc/router.py`, `app/modules/kyc/__init__.py`, `app/core/errors.py`, `app/main.py`, `tests/unit/test_kyc_ingestion.py`, `LESSONS.md`.
- Verified: All 64 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` syntax validation passed.
- Limitations: Document and selfie images stored in artifact directory; deep OCR field extraction and offline Aadhaar Secure QR signature validation will be implemented in Task 3.2.

### 2026-10-28 — Task 2.4 complete
- Changed: Implemented Ring & Community Detection in `app/modules/graph/community.py`. `CommunityDetector` provides connected component analysis, bipartite one-mode projection, clique detection, cycle counting, and fraud contagion metrics for multi-applicant fraud syndicates. Exported classes in `app/modules/graph/__init__.py`. Added comprehensive unit tests in `tests/unit/test_graph_community.py`.
- Files: `app/modules/graph/community.py`, `app/modules/graph/__init__.py`, `tests/unit/test_graph_community.py`, `LESSONS.md`.
- Verified: All 55 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed.
- Limitations: Community detector operates on transient subgraphs; offline batch scheduled job integration will run via Worker in continuous monitoring phase.

### 2026-10-28 — Task 2.3 complete
- Changed: Implemented Fast Synchronous 1-Hop Rule Engine (M0 Baseline). `app/modules/graph/rules.py`: `M0RuleEngine` evaluating 1-hop collision and link degree checks on indexed PostgreSQL/SQLite tables (`ix_applicant_edges_target_edge_type`), returning `RuleEvaluationResult` with structured reason codes (`IDENTITY_REUSE_COLLISION`, `R1_HIGH_PHONE_REUSE`, `PHONE_REUSE_MODERATE`, `R2_HIGH_DEVICE_REUSE`, `DEVICE_REUSE_MODERATE`, `CONFIRMED_FRAUD_LINK`, `R3_NAME_CONTRADICTION`, `R4_DOB_CONTRADICTION`, `R5_INVALID_ID_CHECKSUM`, `R6_VELOCITY_BURST`, `CLEAN`), calibrated risk tiers (`APPROVE`, `REVIEW`, `REJECT`), and execution time telemetry (< 20ms). `app/modules/graph/__init__.py`: exported rule engine classes.
- Files: `app/modules/graph/rules.py`, `app/modules/graph/__init__.py`, `tests/unit/test_graph_rules.py`.
- Verified: All 50 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed.
- Limitations: Rule engine operates on 1-hop collision and local thresholds; multi-component community structure and dense ring clusters will be analyzed in Task 2.4.

### 2026-10-28 — Task 2.2 complete
- Changed: Implemented Bounded 2-Hop Ego-Network Extractor and topological fraud feature engine. `app/core/graph.py`: defined `IdentityGraphEngine` protocol, `GraphFeatureVector`, and `GraphSubnetwork`. `app/modules/graph/engine.py`: `RelationalIdentityGraphEngine` with bounded iterative BFS graph extraction, transient NetworkX graph generation, and calculation of the 8 topological features (`shared_phone_degree`, `shared_device_degree`, `shared_ssn_degree`, `ego_node_count`, `ego_edge_count`, `ego_density`, `max_neighbor_risk`, `cycle_count`). Added Unicode NFKD normalization in `app/core/security.py` to prevent homoglyph hashing evasion.
- Files: `app/core/graph.py`, `app/core/security.py`, `app/modules/graph/engine.py`, `app/modules/graph/__init__.py`, `tests/unit/test_graph_engine.py`, `LESSONS.md`.
- Verified: All 44 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed.
- Limitations: Graph engine currently extracts localized ego-networks on demand; multi-component community detection across the full network will be implemented in Task 2.4.

### 2026-10-28 — Task 2.1 complete
- Changed: Implemented Relational Identity Graph Schema. `app/modules/graph/models.py`: `NodeType` and `EdgeType` StrEnums; `ApplicantNode` ORM model with pseudonymized identifier columns (`identity_hash`, `device_fingerprint_hash`, `phone_hash`, `email_hash`, `ip_address_hash`), screening status, prior risk, and strict `@validates` check rejecting unhashed raw PII; `ApplicantEdge` ORM model with composite indices on `(source_hash, edge_type)` and `(target_hash, edge_type)` for O(log n) lookups, unique constraint on `(source_hash, target_hash, edge_type)`, and raw PII validation. `app/modules/graph/__init__.py`: clean exports.
- Files: `app/modules/graph/models.py`, `app/modules/graph/__init__.py`, `tests/unit/test_graph_schema.py`.
- Verified: All 38 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors; `py_compile` passed.
- Limitations: Graph tables currently store relational node and edge rows; 2-hop extraction and transient NetworkX graph engine will be implemented in Task 2.2.

### 2026-10-28 — Task 1.1.3 complete
- Changed: Implemented Zero-Broker PostgreSQL Lease Worker system. `app/infrastructure/jobs/models.py`: `Job` ORM model (status, lease_token, lease_expires_at, deadline_at, attempt_count, cancel_requested_at, result_json). `app/infrastructure/jobs/registry.py`: `HandlerRegistry` with open/closed registration, `ExecutionContext` with cooperative cancellation checks, `PermanentJobError`, `RetryableJobError`, `JobCancelled`. `app/infrastructure/jobs/service.py`: `enqueue_job`, `claim_one` (FOR UPDATE SKIP LOCKED on PostgreSQL, graceful SQLite fallback), lease expiry recovery, `finish_job` with lease token fencing, `execute_job_lifecycle` with exponential backoff retry. `app/worker/worker.py`: `WorkerService` with bounded thread pool and clean SIGTERM/SIGINT shutdown.
- Files: `app/infrastructure/jobs/models.py`, `app/infrastructure/jobs/registry.py`, `app/infrastructure/jobs/service.py`, `app/worker/worker.py`, `app/worker/__init__.py`, `tests/unit/test_worker_jobs.py`.
- Verified: All 32 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit -q`; `python3 -m ruff check app tests` returned 0 errors.
- Limitations: Worker currently uses a fixed poll interval; adaptive backoff on empty queue deferred to future scaling work.

### 2026-10-28 — Task 1.1.2 complete
- Changed: Implemented Identity & RBAC module (`app/modules/identity/`) with Argon2id password hashing, JWT HS256 access tokens, rotating opaque refresh tokens with 30-second replay grace period, admin bootstrap, RBAC dependencies (`current_user`, `require_role`, `require_admin`), and API key management. Integrated identity router and request context middleware into `app/main.py`.
- Files: `app/modules/identity/models.py`, `app/modules/identity/schemas.py`, `app/modules/identity/auth.py`, `app/modules/identity/router.py`, `app/modules/identity/__init__.py`, `app/main.py`, `tests/unit/test_identity.py`, `LESSONS.md`.
- Verified: All 24 unit tests passed via `PYTHONPATH=. python3 -m pytest tests/unit`; `ruff check` passed with 0 errors; `py_compile` passed.
- Limitations: Multi-factor authentication (MFA/TOTP) deferred to future stretch goals per plan.

### 2026-10-28 — Task 1.1.1 complete
- Changed: Implemented core configuration (`app/core/config.py`), cryptographic PII pseudonymizer (`app/core/security.py`), structured error handling (`app/core/errors.py`), database engine with dialect detection (`app/infrastructure/database.py`), and binary artifact storage with magic-byte validation and path jail (`app/infrastructure/storage/artifact_store.py`).
- Files: `app/core/config.py`, `app/core/security.py`, `app/core/errors.py`, `app/infrastructure/database.py`, `app/infrastructure/storage/artifact_store.py`, `app/infrastructure/storage/__init__.py`, `pytest.ini`, `tests/unit/test_security_pii.py`, `tests/unit/test_artifact_store.py`.
- Verified: All 18 unit tests passed via `pytest`; `ruff check` passed with 0 errors; `py_compile` syntax validation passed.
- Limitations: Storage currently uses local disk backend; S3/cloud storage adapter deferred to future scaling if needed.

### 2026-10-29 — Dynamic UI & Data-Driven Forensics (session continuation)

**What was completed:**

1. **Analytics Page — Dynamic time-series (`/analytics`)**
   - `app/modules/investigation/service.py` `get_analytics`: Removed unused `total` query (ruff F841), confirmed monthly rollups computed live from database records — no hardcoded fallback arrays.
   - Backend returns real `volumeOverTime` with month labels and actual counts; `fraudFlagsOverTime` computed per-month from `high_risk`/`rejected`/`flagged` statuses.

2. **Application Detail Page — Full data-driven Document Forensics tab**
   - `dashboard/src/types/dashboard.ts`: Aligned `ForensicReport` interface to snake_case field names matching `_synthesize_forensic_report` backend output (`checksum_valid`, `checksum_details`, `tampering_signals`, `differentiating_anchors`, `qr_analysis`, etc.). Added index signature for forward-compat.
   - `dashboard/src/pages/ApplicationDetailPage.tsx`: Replaced all four hardcoded security signal cards (Statutory Credential, Cryptographic Checksum, C2PA Content Provenance, Image Integrity) with an IIFE rendering data-driven values from `application.document.forensicReport`. Correct color coding (green=clean, red=flagged) for each signal. Added optional QR/Chip analysis strip from `qr_analysis` field.

3. **KYC Frontend form — warnings and disclaimers purged**
   - Confirmed all hackathon disclaimers and placeholder warnings have been removed from `WelcomePage.tsx`, `VerificationResultsPage.tsx`, and `DocumentUploadForm.tsx`.
   - `POST /api/kyc/document/analyze` real-time validation is active and blocks form progression on AI-generated/invalid documents.

**Files changed (this session):**
- `app/modules/investigation/service.py` — removed unused `total` in `get_analytics`
- `dashboard/src/types/dashboard.ts` — updated `ForensicReport` to snake_case fields
- `dashboard/src/pages/ApplicationDetailPage.tsx` — data-driven security signal cards

**Verified:**
- `npm run build` in `dashboard/` — exit 0, clean TypeScript compile
- `python3 -m ruff check app tests scripts` — 0 errors
- Backend API spot-checks: `selfieUrl` (55979 chars), `imageUrl` (231539 chars), `forensicReport.checksum_valid: true`, analytics dynamic labels, clusters 4 shared / 1 ring
- Unit tests: 221/221 passed (previous session); re-running to confirm no regressions

**Architecture decisions:** No new boundaries introduced; all changes are within existing investigation service and dashboard view layers.

**Next steps:**
- Monitor fraud detection quality with real submissions via `demo_argus.py --preset genuine/fraudulent`
- Phase 5 (Continuous Monitoring & Case Investigation API) is the next unstarted phase

