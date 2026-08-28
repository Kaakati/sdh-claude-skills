---
name: std-python-ai-ml
description: AI/ML engineering conventions — notebooks vs modules, MLflow experiment tracking, reproducibility, FastAPI model serving, pgvector embeddings, LLM (Anthropic) integration, evals. Use when writing training pipelines, inference services, or LLM features.
paths:
  - "**/*.ipynb"
  - "**/ml/**/*.py"
  - "**/notebooks/**"
  - "**/training/**/*.py"
  - "**/inference/**/*.py"
  - "**/pipelines/**/*.py"
---

# AI/ML Engineering Conventions

Rules for training pipelines, inference services, and LLM features in the house Python
stack. Models are served through FastAPI services (framework conventions in the
`std-fastapi` skill); general Python layout, typing, and layering live in `std-python`.

## Stack

| Concern | Library |
|---------|---------|
| Dataframes | **polars** for new pipelines; pandas acceptable in existing code |
| Numerics | numpy |
| Classical ML | scikit-learn — **baseline first** (see below) |
| Deep learning | PyTorch |
| Pretrained models | transformers |
| Experiment tracking | MLflow — tracking AND the model registry |
| Dataframe contracts | pandera — validate at pipeline boundaries |
| Portable CPU inference | onnxruntime |
| Embeddings store | pgvector on the house PostgreSQL |
| LLM features | the `anthropic` SDK |

- **Ship a linear/tree baseline with a held-out eval before any deep learning** — the
  baseline tells you whether the problem needs a neural net at all, and the eval harness
  you build for it outlives the baseline: every later model is judged on the same held-out
  set.
- **Use pgvector before adding a dedicated vector database** — the ops burden of a new
  datastore needs a proven ceiling first. Move only when measured recall or latency on
  real corpus size demands it.
- Validate dataframes with pandera schemas at every pipeline boundary — a silent schema
  drift upstream becomes a silent quality drop downstream.

## Notebooks vs Modules

- `notebooks/` is for exploration only — plots, one-off analysis, scratch work.
- Promote production logic into `src/` modules and import it into the notebook —
  **never import from a notebook**: notebooks have no tests, no types, no review gate,
  and hidden execution-order state.
- Strip outputs before commit (`nbstripout` as a git filter) — outputs bloat diffs and
  leak data samples into the repo.

## Reproducibility

- The uv lockfile pins the environment — a training run is only reproducible if its
  dependencies are.
- Seed `random`, numpy, and torch in one `set_seed(seed)` helper called at process start —
  scattered seeding is unverifiable seeding.
- Training runs are config-driven via pydantic models (one `TrainingConfig`, loaded from a
  file or CLI) — no hand-edited hyperparameters buried in code; the config is logged with
  the run, so the run can be re-created from it.
- **Never train against a mutable "latest" table** — datasets are versioned snapshots
  (DVC, or versioned S3 parquet paths). A model trained on data nobody can reproduce is a
  model nobody can debug.

## Experiment Tracking (MLflow)

- Every training run logs params, metrics, and artifacts to MLflow — an unlogged run may
  as well not have happened.
- Promote models through registry aliases (`@staging` → `@production`), never by copying
  artifacts around by hand — the registry is the single source of "what is deployed".
- **No model ships without a recorded eval on a pinned dataset** — a metric on an
  unpinned dataset cannot be compared to the previous model's, so it cannot justify a
  promotion.

## Serving (FastAPI)

- **Load the model once in the FastAPI lifespan — never per-request**: model load is
  seconds and hundreds of MB; per-request loading turns every call into a cold start.
- Pin the model artifact version in config (a registry alias or explicit version) — a
  service that loads "latest" changes behavior without a deploy.
- The health endpoint reports the loaded model version — so an operator can see at a
  glance which model each instance is actually serving.
- Set request timeouts and a max payload size — inference endpoints are a
  denial-of-service magnet without both.
- Watch p95 inference latency — dashboards and alerting conventions are owned by
  `std-monitoring`.

## LLM Integration (anthropic SDK)

- Model choice: `claude-sonnet-5` by default for product features;
  `claude-haiku-4-5-20251001` for cheap high-volume classification; `claude-opus-5` when
  reasoning depth is the product. Pin the model id in config, not inline.
- Prompts are versioned code — files in the repo, reviewed in PRs — not database strings:
  a prompt change is a behavior change and gets the same diff, review, and rollback.
- Structured outputs come from tool use, not from parsing prose — a tool schema is a
  contract; a regex over prose is a hope.
- **A pinned eval set runs in CI before a prompt or model change ships** — LLM behavior
  shifts across prompts and model versions, and an eval is the only regression test that
  catches it.
- Retry transient API errors with exponential backoff and a capped attempt count (the
  SDK's built-in retries or `tenacity`).
- **Never log full prompts or completions containing user PII** — log request ids, token
  counts, latency, and model id instead; logging rules are owned by `std-monitoring`.
- Give every LLM feature a cost budget (per-request and monthly) and review it like a
  performance budget — token spend regresses as silently as latency does.

## Embeddings (pgvector)

- Pin the embedding model and its dimension together in config — vectors from different
  models share a column type but not a space; mixing them silently ruins retrieval.
- Index with HNSW by default — better recall/latency than IVFFlat at house corpus sizes.
- Changing the embedding model means re-embedding the entire corpus — plan it as a
  migration (dual-write or backfill, then cut over), not an in-place swap.

## Rollout

- New models ship behind a flag with shadow or canary traffic first — offline eval
  numbers do not guarantee online behavior.
- Monitor input drift and prediction distributions in production; alert on divergence
  from the training distribution — models fail silently by degrading, not by crashing.

Related, owned elsewhere — do not duplicate: the JSON error envelope and pagination
response format live in `std-api-design`; migration safety and indexing depth in
`std-database`; OWASP and secret management in `std-security`; structured logging and
PII-in-logs rules in `std-monitoring`; AAA and coverage targets in `std-testing`; general
Python layout, typing, and layering in `std-python`; ORM query performance in
`std-python-performance`; FastAPI framework specifics in `std-fastapi`.
