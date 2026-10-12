# Cloud Resource and Job Scheduling System

A production-grade, web-based micro cloud orchestration environment built with **Python Flask**, **MySQL**, **Docker Engine (Python Docker SDK)**, and **Bootstrap 5**.

The system ingests compute workloads through an interactive console, calculates dynamic CPU and RAM requirements, atomically schedules jobs onto eligible computing nodes using transactional row locking, executes jobs inside isolated Docker containers, streams process telemetry (stdout/stderr/exit codes) to MySQL, and simulates classic operating system CPU scheduling algorithms (Round Robin, FCFS, SJF, Priority).

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Database Schema (Normalized MySQL)](#2-database-schema-normalized-mysql)
3. [Component Responsibilities](#3-component-responsibilities)
4. [Job Execution Lifecycle](#4-job-execution-lifecycle)
5. [Docker Workload Specifications](#5-docker-workload-specifications)
6. [Resource-Aware Scheduler & Concurrency Control](#6-resource-aware-scheduler--concurrency-control)
7. [OS CPU Scheduling Simulator vs. Docker Execution](#7-os-cpu-scheduling-simulator-vs-docker-execution)
8. [Security & Isolation Safeguards](#8-security--isolation-safeguards)
9. [Prerequisites & System Requirements](#9-prerequisites--system-requirements)
10. [Quickstart with Docker Compose](#10-quickstart-with-docker-compose)
11. [Local Development Setup (Without Docker Compose)](#11-local-development-setup-without-docker-compose)
12. [End-to-End Demonstration Walkthrough](#12-end-to-end-demonstration-walkthrough)
13. [Running the Test Suite](#13-running-the-test-suite)
14. [Troubleshooting & FAQ](#14-troubleshooting--faq)

---

## 1. System Architecture

```text
               +--------------------------------------------------+
               |             Web Browser / Client UI              |
               |       (Bootstrap 5 + Chart.js + Dark Theme)      |
               +------------------------+-------------------------+
                                        | HTTP / REST API
                                        v
               +--------------------------------------------------+
               |            Flask Web Application (web)           |
               |   - Authentication & User Sessions               |
               |   - REST APIs (/api/jobs, /nodes, /dashboard)    |
               |   - Dynamic Resource Estimation Engine           |
               |   - OS CPU Scheduling Simulator (RR, FCFS, SJF)  |
               +------------------------+-------------------------+
                                        | SQLAlchemy ORM
                                        v
               +--------------------------------------------------+
               |              MySQL 8.0 Database (db)             |
               |   - Users, Jobs, WorkloadTypes, ComputingNodes   |
               |   - JobAssignments, SchedulingConfigs & Results  |
               +------------------------+-------------------------+
                                        ^
                                        | SELECT ... FOR UPDATE
               +------------------------+-------------------------+
               |         Background Worker Service (worker)       |
               |   - Atomically claims queued jobs                |
               |   - Best-fit node capacity reservation           |
               |   - Enforces timeout, CPU shares, memory caps    |
               +------------------------+-------------------------+
                                        | /var/run/docker.sock
                                        v
               +--------------------------------------------------+
               |               Host Docker Engine                 |
               |   +------------------------------------------+   |
               |   |  Isolated Container: Image Processing    |   |
               |   +------------------------------------------+   |
               |   |  Isolated Container: Data Analysis       |   |
               |   +------------------------------------------+   |
               |   |  Isolated Container: File Processing     |   |
               |   +------------------------------------------+   |
               |   |  Isolated Container: Video Conversion    |   |
               |   +------------------------------------------+   |
               +--------------------------------------------------+
```

---

## 2. Database Schema (Normalized MySQL)

The system utilizes seven normalized tables with primary keys, foreign keys, indexes, and constraints to guarantee transactional consistency:

```text
users
  ├── id (PK, INT AUTO_INCREMENT)
  ├── username (VARCHAR 80, UNIQUE, INDEX)
  ├── email (VARCHAR 120, UNIQUE, INDEX)
  ├── password_hash (VARCHAR 256)
  ├── is_active_user (BOOLEAN)
  └── created_at (DATETIME)

workload_types
  ├── id (PK, INT AUTO_INCREMENT)
  ├── name (VARCHAR 100, UNIQUE)
  ├── docker_image (VARCHAR 255)
  ├── command_template (VARCHAR 500)
  ├── est_cpu_cores (INT)
  ├── est_memory_mb (INT)
  ├── est_time_seconds (INT)
  ├── cpu_scale_factor (FLOAT)
  ├── memory_scale_factor (FLOAT)
  └── time_scale_factor (FLOAT)

computing_nodes
  ├── id (PK, INT AUTO_INCREMENT)
  ├── name (VARCHAR 100, UNIQUE)
  ├── total_cpu_cores (INT)
  ├── total_memory_mb (INT)
  ├── allocated_cpu_cores (INT)
  ├── allocated_memory_mb (INT)
  ├── status (VARCHAR 20)          ['active', 'maintenance', 'offline']
  ├── is_simulated (BOOLEAN)
  └── last_heartbeat (DATETIME)

jobs
  ├── id (PK, INT AUTO_INCREMENT)
  ├── user_id (FK -> users.id, INDEX)
  ├── workload_type_id (FK -> workload_types.id)
  ├── status (VARCHAR 20, INDEX)   ['queued', 'assigned', 'running', 'completed', 'failed']
  ├── input_params (JSON)
  ├── est_cpu_cores (INT)
  ├── est_memory_mb (INT)
  ├── est_time_seconds (INT)
  ├── priority (INT)               [1=Highest, 10=Lowest]
  ├── created_at (DATETIME)
  └── updated_at (DATETIME)

job_assignments
  ├── id (PK, INT AUTO_INCREMENT)
  ├── job_id (FK -> jobs.id, UNIQUE, INDEX)
  ├── node_id (FK -> computing_nodes.id, INDEX)
  ├── container_id (VARCHAR 100)
  ├── assigned_at (DATETIME)
  ├── started_at (DATETIME)
  ├── completed_at (DATETIME)
  ├── exit_code (INT)
  ├── stdout (TEXT)
  ├── stderr (TEXT)
  ├── actual_cpu_used (INT)
  ├── actual_memory_used_mb (INT)
  └── actual_duration_seconds (FLOAT)

scheduling_configs
  ├── id (PK, INT AUTO_INCREMENT)
  ├── algorithm (VARCHAR 50)       ['FCFS', 'SJF', 'Priority', 'RoundRobin']
  ├── time_quantum_ms (INT)
  ├── is_active (BOOLEAN)
  └── created_at (DATETIME)

scheduling_results
  ├── id (PK, INT AUTO_INCREMENT)
  ├── scheduling_config_id (FK -> scheduling_configs.id)
  ├── job_ids (JSON)
  ├── execution_order (JSON)
  ├── metrics (JSON)
  └── created_at (DATETIME)
```

---

## 3. Component Responsibilities

| Service / Directory | Technology | Responsibility |
|---|---|---|
| `app/` | Flask 3.0, SQLAlchemy | Web app factory, blueprints, routing, session auth, Jinja2 templates, static assets. |
| `app/api/` | REST / JSON | Exposes endpoints for jobs CRUD, nodes telemetry, dashboard metrics, and scheduling simulator. |
| `app/scheduler/estimator.py` | Python | Calculates required CPU, memory, and duration from workload baseline & scaling factors. |
| `app/scheduler/node_selector.py` | SQLAlchemy | Best-fit node selector using `with_for_update()` to guarantee deadlock-free, over-allocation-free placement. |
| `app/scheduler/algorithms.py` | Python | Simulates OS scheduling (Round Robin with time quantum, FCFS, SJF, Priority). |
| `worker/worker.py` | Docker SDK, Python | Dedicated background service polling MySQL, executing Docker containers, capturing logs, releasing capacity. |
| `workloads/` | Python, Docker | Standalone containerized workloads (Image Processing, Data Analysis, File Processing, Video Conversion). |
| `init_db.py` | Python / SQLAlchemy | Idempotent database seeder creating initial nodes, workloads, algorithm configs, and admin account. |

---

## 4. Job Execution Lifecycle

Every job proceeds through a strictly tracked lifecycle:

1. **Submission:** User fills out the job submission wizard.
2. **Estimation:** `estimate_resources()` calculates CPU, RAM, and runtime from parameters using active database scaling factors. The job record is inserted with `status = 'queued'`.
3. **Claiming:** The background worker polls the database using `SELECT ... FOR UPDATE SKIP LOCKED` on the highest priority, oldest queued job to prevent multiple workers from claiming the same job.
4. **Node Selection:** The worker executes `select_node()` with row-level locks on `computing_nodes`. A node with sufficient free CPU cores and memory is chosen using best-fit allocation. Resources are reserved immediately in MySQL, and a `job_assignments` record is created.
5. **Docker Execution:** The worker invokes `docker_client.containers.run()`:
   - Sets CPU quota via `nano_cpus = cpu_cores * 1e9`.
   - Sets Memory limit via `mem_limit = f'{memory_mb}m'`.
   - Disables container networking (`network_disabled=True`).
   - Disables privileged mode (`privileged=False`).
   - Attaches labels (`job-id`, `node-id`).
   - Transitions job status to `'running'`.
6. **Telemetry Ingestion:** The worker calls `container.wait(timeout=300)` to capture:
   - Execution duration (seconds)
   - Exit code (0 for success, non-zero for failure)
   - Standard output (`stdout`) and standard error (`stderr`)
7. **Resource Release & Cleanup:** Node allocated CPU and memory are released back into the pool. Completed containers are removed according to cleanup policy (`container.remove(force=True)`).
8. **Dashboard Update:** The live monitoring dashboard polls `/api/dashboard` and updates charts, tables, and node status without requiring a page refresh.

---

## 5. Docker Workload Specifications

The system comes with 4 real, containerized workloads under `workloads/`:

### 1. Image Processing (`workloads/image_processing`)
- **Docker Image:** `cloud-workload-image`
- **Script:** `process.py`
- **Dependencies:** `Pillow`
- **Supported Operations:** `blur` (3-pass Gaussian), `sharpen`, `grayscale`, `resize` (dual-pass Lanczos), `edge_detect`.
- **Scaling Rule:** Memory and compute scale quadratically with resolution `(size / 512)^2`.

### 2. Data Analysis (`workloads/data_analysis`)
- **Docker Image:** `cloud-workload-data`
- **Script:** `analyze.py`
- **Dependencies:** Standard library only (`statistics`, `math`, `random`).
- **Functionality:** Generates synthetic multivariate datasets (revenue, cost, units, latency) and computes mean, median, stdev, IQR, and Pearson correlation matrices.
- **Scaling Rule:** Scales linearly with rows `(rows / 1000)`.

### 3. File Processing (`workloads/file_processing`)
- **Docker Image:** `cloud-workload-file`
- **Script:** `process.py`
- **Dependencies:** Standard library only.
- **Functionality:** Synthesizes structured documents and computes word counts, character frequencies, sentence statistics, and vocabulary densities.
- **Scaling Rule:** Scales linearly with text size in KB `(size_kb / 100)`.

### 4. Video Conversion (`workloads/video_conversion`)
- **Docker Image:** `cloud-workload-video`
- **Script:** `convert.py`
- **Dependencies:** Standard library only (`zlib`, `hashlib`, `struct`).
- **Functionality:** Synthesizes 24 fps uncompressed RGB frame buffers with moving color phases and encodes them via zlib compression streams.
- **Scaling Rule:** Scales linearly with video duration `(duration / 5)`.

---

## 6. Resource-Aware Scheduler & Concurrency Control

### Best-Fit Selection Algorithm
When allocating a node for $C$ required cores and $M$ required memory MB:
1. Filters active nodes satisfying:
   $$\text{available\_cpu} \ge C \quad \text{and} \quad \text{available\_mem} \ge M$$
2. Minimizes remaining unused capacity to reduce fragmentation:
   $$\min [(\text{available\_cpu} - C) + (\text{available\_mem} - M)]$$
3. Increments node allocations atomically.

### Concurrency Safeguards
- **Row Locking (`with_for_update()`):** Eliminates race conditions when concurrent requests attempt to claim the last available cores on a host.
- **Workload Recovery:** If the worker crashes or restarts, `_recover_stuck_jobs()` detects jobs stuck in `'assigned'` or `'running'`, releases their node reservations, and returns them to `'queued'`.

---

## 7. OS CPU Scheduling Simulator vs. Docker Execution

> **Important Distinction:** The OS CPU Scheduling Simulator is a discrete-event simulator that models theoretical operating system scheduling algorithms on jobs' estimated burst times and priorities. It does **not** schedule the actual Linux processes. Actual Docker container execution is scheduled by the Linux kernel's Completely Fair Scheduler (CFS) under cgroups constraints managed by the worker.

### Implemented Algorithms:
1. **First Come First Served (FCFS):** Non-preemptive, ordered strictly by arrival order.
2. **Shortest Job First (SJF):** Non-preemptive, greedy selection of the eligible process with the lowest burst time.
3. **Priority Scheduling:** Non-preemptive, ordered by priority rating ($1 = \text{highest}$).
4. **Round Robin (RR):** Preemptive scheduling using a configurable time quantum ($\delta$). Processes execute for at most $\delta$ time units before being preempted and placed at the tail of the ready queue.

### Deadlock and Starvation Discussion
- Round Robin mitigates CPU starvation by enforcing bounded waiting time.
- However, **Round Robin alone does not prevent deadlock**.
- Deadlock prevention in our cloud engine is enforced at the node reservation level by eliminating Coffman's *Hold and Wait* condition: node CPU and RAM are allocated atomically as a single unit or rejected entirely (jobs remain queued).

---

## 8. Security & Isolation Safeguards

1. **No Arbitrary Shell Execution:** The system never invokes `shell=True` or passes user strings directly to shell interpreters. All workload arguments are sanitized, type-cast, and parsed via `argparse`.
2. **Container Privilege Restriction:** Containers run with `privileged=False`, preventing container breakouts.
3. **Isolated Network:** Workload containers run with `network_disabled=True` to prevent outbound socket connections or unauthorized network probing.
4. **Resource Quotas:** Every container has strict cgroups limits for nano-CPUs and RAM.
5. **Execution Timeouts:** Worker monitors containers with a maximum timeout (default 300s) to prevent runaway infinite loops.
6. **Docker Socket Exposure:** `/var/run/docker.sock` is mounted **only** to the worker service container. The web-facing Flask container does not have access to the Docker socket.

---

## 9. Prerequisites & System Requirements

- **Docker Desktop** (or Docker Engine 24.0+ on Linux) with Docker Compose v2.
- **Python 3.10+** (if running locally outside Docker).
- **Git**
- Minimum 4 GB RAM available on your Docker host.

---

## 10. Quickstart with Docker Compose

### Step 1: Clone and Configure Environment

```bash
cd c:/Users/ashut/OneDrive/Desktop/pbl
copy .env.example .env
```

*(On Linux / macOS, use `cp .env.example .env`)*

### Step 2: Build Workload Docker Images

Before launching the scheduler, build the 4 workload images:

```bash
# Image Processing
docker build -t cloud-workload-image ./workloads/image_processing

# Data Analysis
docker build -t cloud-workload-data ./workloads/data_analysis

# File Processing
docker build -t cloud-workload-file ./workloads/file_processing

# Video Conversion
docker build -t cloud-workload-video ./workloads/video_conversion
```

### Step 3: Start Services

```bash
docker compose up --build -d
```

This starts:
- `cloud-scheduler-db` (MySQL 8.0 on port 3307)
- `cloud-scheduler-init` (Seeds database and exits with code 0)
- `cloud-scheduler-web` (Flask application on port 5000)
- `cloud-scheduler-worker` (Background job runner connected to Docker Engine)

### Step 4: Access Web Application

Open your browser and navigate to:
**`http://localhost:5000`**

- Default Admin Username: `admin`
- Default Admin Password: `admin123`

---

## 11. Local Development Setup (Without Docker Compose)

If you prefer to run Flask directly on your host machine:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start MySQL
You can start just the MySQL service via Docker:
```bash
docker compose up -d db
```

### 3. Initialize & Seed Database
```bash
python init_db.py
```

### 4. Run the Web Application
```bash
python run.py
```
App will be running at `http://127.0.0.1:5000`.

### 5. Run the Worker (Separate Terminal)
```bash
python -m worker.worker
```

---

## 12. End-to-End Demonstration Walkthrough

1. **Log in:** Visit `http://localhost:5000/auth/login`. Click **Quick Fill Admin** and submit.
2. **Cluster Topology:** Navigate to **Cluster Nodes** (`/nodes`). Verify that `node-alpha`, `node-beta`, and `node-gamma` are in `active` state with 0% initial utilization.
3. **Submit a Workload:**
   - Navigate to **Submit Job** (`/jobs/submit`).
   - Select **Image Processing**.
   - Pick the **Gaussian Blur** filter and set resolution to `1024 x 1024 px`.
   - Observe the **Dynamic Estimation Engine** card instantly update the estimated CPU (4 Cores), RAM (1536 MB), and runtime (~144s).
   - Set priority to `P2 (High)`.
   - Click **Submit Job to Cloud Queue**.
4. **Inspect Job Lifecycle:**
   - You are automatically redirected to `/jobs/<id>`.
   - Watch the live stepper transition: `Queued` $\rightarrow$ `Node Assigned` $\rightarrow$ `Container Run` $\rightarrow$ `Completed`.
   - Inspect the Docker container ID, exit code (`Exit 0`), and live standard output terminal viewer displaying Pillow's JSON output.
5. **Dashboard Monitoring:**
   - Go to **Dashboard** (`/dashboard`).
   - Observe the active job counters, node utilization bars, and status distribution donut chart.
6. **OS Scheduling Simulator:**
   - Navigate to **OS Scheduling Simulator** (`/scheduling`).
   - Set Round Robin Time Quantum to `50 ms`.
   - Click **Run Simulation**.
   - Inspect the Gantt execution timeline comparing Round Robin preemption time-slicing against FCFS, SJF, and Priority.

---

## 13. Running the Test Suite

Run the full pytest unit and integration test suite:

```bash
python -m pytest tests/ -v
```

The test suite tests:
- User password hashing and authentication models
- Node capacity calculations, available memory/cores, and utilization percentages
- Resource estimation multipliers across all 4 workload types
- FCFS, SJF, Priority, and Round Robin scheduling algorithms
- Best-fit node selection with row-level reservation and resource release
- Flask REST APIs (CRUD, input parameter validators, simulation endpoints)

---

## 14. Troubleshooting & FAQ

### Issue: "Docker client not available" or permission denied on docker.sock
- **Cause:** Docker Desktop is not running or the worker container cannot access the Docker pipe.
- **Fix (Windows):** Ensure Docker Desktop is running and that "Expose daemon on tcp://localhost:2375 without TLS" or named pipes are enabled if using WSL2 backend.
- **Fix (Linux):** Add your user to the docker group: `sudo usermod -aG docker $USER`.

### Issue: MySQL connection refused during startup
- **Cause:** The database container is still initializing.
- **Fix:** Docker Compose includes health checks (`mysqladmin ping`). The `web` and `worker` services wait for `condition: service_healthy` before starting. Allow 20–30 seconds for first-time database initialization.

### Issue: Port 5000 or 3307 already in use
- **Fix:** Modify the port mapping in `docker-compose.yml` (e.g. change `"5000:5000"` to `"5050:5000"`).
