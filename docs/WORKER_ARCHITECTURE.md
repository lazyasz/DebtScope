# DebtScope Background Worker Architecture & Roadmap

## 1. Current Architecture: In-Process Orchestration

DebtScope currently coordinates repository ingestion, multi-language AST complexity analysis, git history mining, and priority scoring through an asynchronous service worker layer (`backend/services/analysis_worker.py`) executed via FastAPI's background tasks.

### 1.1 Concurrency Caps & Tenant Boundaries
To prevent denial of service and ensure fair resource sharing across tenants:
- **Global Concurrency Cap**: `WORKER_MAX_GLOBAL_CONCURRENT_JOBS = 2` (configurable). Rejects excessive scan requests with `HTTP 429 Too Many Requests`.
- **Per-Workspace Concurrency Limit**: `WORKER_MAX_WORKSPACE_CONCURRENT_JOBS = 1` (configurable). Prevents duplicate concurrent runs within the same tenant with `HTTP 409 Conflict`.
- **Per-Job Execution Timeout**: `WORKER_JOB_TIMEOUT_SECONDS = 600` (10 minutes). Preemptively halts runaway repository clones or infinite AST recursions.

### 1.2 Heartbeat & Fault-Tolerant Startup Recovery
- **Milestone Heartbeats**: The worker emits timestamped heartbeats (`job.last_heartbeat = utc_now()`) as it transitions through stages: `CLONING` $\rightarrow$ `ANALYZING` $\rightarrow$ `MINING` $\rightarrow$ `PERSISTING` $\rightarrow$ `COMPLETED`.
- **Graceful Recovery**: Upon server restart, `recover_stale_jobs()` computes elapsed time since each in-flight job's last heartbeat:
  - If $\Delta t > \text{WORKER\_HEARTBEAT\_STALE\_SECONDS}$ (120s), the job is declared dead and transitioned to `FAILED` with a diagnostic restart reason.
  - If $\Delta t \le \text{WORKER\_HEARTBEAT\_STALE\_SECONDS}$, active jobs are left running without destructive cancellation.

---

## 2. Next Architecture Step: Dedicated Worker Process Separation

While in-process background execution provides zero-infrastructure development simplicity, scaling to enterprise production workloads requires a physically separated worker fleet.

```
┌────────────────────────────────┐
│   FastAPI Web Services (API)   │
│   - SSRF URL Validation        │
│   - JWT / OAuth Authentication │
│   - Job Enqueueing & Polling   │
└───────────────┬────────────────┘
                │ Task Dispatch
                ▼
┌────────────────────────────────┐
│  Message Broker (Redis/Rabbit) │
│  - FIFO Task Queue             │
│  - Job Dead-Letter Exchange    │
└───────────────┬────────────────┘
                │ Async Consume
                ▼
┌────────────────────────────────┐
│  Dedicated Worker Pods / Nodes │
│  - Sandboxed Git Cloning       │
│  - Lizard AST Multi-Language   │
│  - SZZ Commit Mining           │
│  - DB Metric Persistence       │
└────────────────────────────────┘
```

### 2.1 Proposed Implementation: Celery + Redis
1. **Message Broker**: Introduce a Redis or RabbitMQ container in `docker-compose.yml`.
2. **Task Definition**: Refactor `run_analysis_pipeline` into a Celery task (`@celery_app.task(bind=True, time_limit=600)`).
3. **Dedicated Container**: Add `worker` service to `docker-compose.yml`:
   ```yaml
   worker:
     build:
       context: .
       dockerfile: Dockerfile.backend
     command: celery -A backend.services.celery_worker worker --loglevel=info -c 4
     depends_on:
       - redis
       - postgres
   ```
4. **Benefits**:
   - Web API memory remains untouched by multi-hundred-megabyte git clones.
   - Independent horizontal autoscaling of worker nodes based on queue depth.
   - Persistent retry queues and distributed task monitoring via Flower.
