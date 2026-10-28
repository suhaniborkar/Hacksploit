# Lessons

A distilled reasoning library, not a log. `PROJECT_PLAN.md`'s Log records
*what happened, in order* — this file records *what would help on a
different task*, retrievable by relevance instead of by reading
chronologically.

Inspired by the ReasoningBank pattern (Ouyang et al., "ReasoningBank:
Scaling Agent Self-Evolving with Reasoning Memory," arXiv:2509.25140) and
the post-run half of what runtime tools like ReasonBlocks do — extract a
reusable lesson after a task, retrieve the relevant one before the next.
This file replicates the distill-and-retrieve idea; it can't replicate
mid-run interception, which needs a runtime wrapper, not a markdown file.

## What belongs here

A lesson is **generalizable** — it should plausibly help on a task in a
*different* part of the codebase, or even a different project entirely.
If a note only makes sense re-reading this exact task's diff, it belongs
in `PROJECT_PLAN.md`'s Log, not here.

Good lesson: "HF's `Cache.update()` must return `(k, v)` for the current
layer only, not the accumulated cache — easy to get backwards."

Not a lesson (belongs in the Log instead): "Implemented `SimpleKVCache` in
`minigen/cache.py`."

## Format

Each entry: a short title, then 2-4 lines — what happened, what the
generalizable takeaway is, and where it applies. Keep entries short; a
lesson that takes a paragraph to state usually hasn't been distilled
enough yet.

Order: newest first, so skimming from the top surfaces recent lessons
first without needing to search.

Retrieval, per task: skim titles top-to-bottom, pull in anything genuinely
relevant to the current task's domain. Don't inject more than 1-2 lessons
into a task's context — per the ReasoningBank ablation this is based on,
retrieving more hurts more than it helps (relevance beats volume). If
nothing here is relevant to the current task, that's the normal case, not
a gap to fill.

---

## Normalizing float probabilities to integer risk scores requires explicit percentage scaling
- What happened: ML models in M0–M3 output calibrated risk probabilities in `[0.0, 1.0]`, while frontend dashboards display integer scores `0–100`. Rounding `raw_score` directly (`round(raw_score)`) collapsed all probabilities to 0 or 1, erroneously mapping a critical 0.88 fraud score to level 'low'.
- Takeaway: Always check scale bounds before rounding: `score_pct = raw_score * 100.0 if raw_score <= 1.0 else raw_score` before casting to integer percentiles.
- Applies to: API serializers, dashboard metric transforms, risk thresholding.

## JPEG quantization table scaling reveals exact original export quality without image decoding
- What happened: Evaluating JPEG compression artifacts required detecting whether an image came from standard AI generator pipelines (which export at round integer qualities like 90, 95, 100) versus authentic mobile camera optical sensors.
- Takeaway: Standard ITU-T T.81 luminance quantization tables scale linearly with quality ($S = 200 - 2Q$ for $Q \ge 50$). By computing the average ratio of an image's loaded quantization table against the baseline table, the exact software export quality can be reversed in < 1ms without decompressing pixel buffers.
- Applies to: Fast-plane image forensics, upload inspection, and generative AI detection.

## Offline Aadhaar Secure QR codes embed RSA-2048 signatures over 0xFF-delimited bytes
- What happened: Live UIDAI CIDR/DigiLocker APIs require complex regulatory accreditation, but Aadhaar Secure QR codes are 100% verifiable offline without network connectivity.
- Takeaway: Decompressing the QR byte stream yields `data_bytes` (text fields separated by byte `0xFF`) and an RSA-2048 digital signature in the final 256 bytes (`decompressed[-256:]`). Verifying against the UIDAI root public key via PKCS#1 v1.5 SHA-256 instantly detects tampered photos or names.
- Applies to: Identity document verification, offline e-KYC pipelines, and media forensics.

## Pydantic v2 ValidationError error dicts contain non-serializable exception objects
- What happened: Raising a domain exception with `details={"errors": pydantic_exc.errors()}` caused FastAPI JSON responses to fail with `TypeError: Object of type ValueError is not JSON serializable` because Pydantic v2 embeds the raw exception in `ctx["error"]`.
- Takeaway: Always project or sanitize `pydantic_exc.errors()` into primitive dicts (`{"field": ..., "message": ..., "type": ...}`) before embedding them in API error payload dictionaries.
- Applies to: FastAPI request handlers, error middleware, and domain validation services.

## Bipartite ego-network hops: distance 2 reaches connected entities, distance 3 reaches their peripheral attributes
- What happened: In bipartite identity graphs (Applicant <-> Identifier), depth 2 reaches other applicants via shared identifiers (App1 -> Ident1 -> App2). Reaching App2's other identifiers (e.g. their device or email) requires graph distance 3.
- Takeaway: For tabular topological feature calculation, distance 2 is strictly sufficient to calculate shared degrees. For visual cluster investigation and community subgraphs, use distance 3 to avoid clipping the peripheral identifiers of neighboring accounts.
- Applies to: Graph algorithms and ego-network extraction on bipartite/heterogeneous graphs.

## SQLite drops timezone offsets, causing naive vs aware comparison TypeErrors
- What happened: Loading `DateTime(timezone=True)` from SQLite returns offset-naive datetimes, raising `TypeError: can't compare offset-naive and offset-aware datetimes` when comparing with `datetime.now(timezone.utc)`.
- Takeaway: Use an `ensure_utc(dt)` helper that re-attaches `timezone.utc` if `dt.tzinfo is None` before comparing stored timestamps with aware clocks in multi-dialect codebases.
- Applies to: Any application using SQLite for tests or development alongside PostgreSQL.

## ROS 2 global pytest entrypoints clash with local virtual environments
- What happened: System ROS 2 packages injected `launch_testing_ros_pytest_entrypoint` into Python test discovery, causing `PluginValidationError: unknown hook` on normal test suites.
- Takeaway: Configure `pytest.ini` with `addopts = -p no:launch_testing_ros_pytest_entrypoint -p no:launch_testing -p no:launch_testing_ros` and run with clean `PYTHONPATH=.`.
- Applies to: Running `pytest` in Linux environments containing global ROS/robotics installations.


