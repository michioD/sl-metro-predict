# Development Log - SL Metro Delay Prediction

This log tracks the continuous progress, engineering decisions, and architectural milestones for the SL Metro Delay prediction MLOps pipeline. It includes explicit rationales and trade-off analyses intended for technical review.

## 2026-08-05: Infrastructure & Data Contracts

* **Architecture Definition (Medallion Pattern)**
  * **Action**: Finalized a Medallion architecture leveraging MinIO (Bronze) and PostgreSQL (Silver/Gold) orchestrated by Apache Airflow.
  * **Design Decision & Trade-offs**: 
    * *Why MinIO & Postgres?* While distributed data warehouses (Snowflake/BigQuery) are standard for massive scale, utilizing MinIO provides an S3-compatible API that allows a seamless "lift-and-shift" to AWS later, while keeping local development free and fast. PostgreSQL handles the Silver/Gold dimensional modeling capably until data volume necessitates a columnar store.
    * *Why Airflow?* Airflow introduces higher operational overhead compared to lightweight schedulers (like Cron or Prefect). However, it was chosen because its robust handling of idempotency and backfilling (via `catchup`).

* **Data Contracts (Great Expectations)**
  * **Action**: Implemented `src/data_quality/schema_validator.py` to enforce strict schema validation on the Trafiklab API endpoints.
  * **Design Decision & Trade-offs**: 
    * *Why strict contracts at ingestion?* Adding validation layers increases ingestion latency and pipeline complexity. If the API provider adds a harmless field, a strict contract might unnecessarily halt the pipeline. However, in MLOps, silent upstream schema mutations are the leading cause of downstream model degradation. Failing fast at the Bronze layer is infinitely preferable to serving garbage predictions in production.

* **GTFS API Ingestion**
  * **Action**: Wrote `src/ingestion/gtfs_realtime_ingest.py` to ingest live Protobuf data.

## 2026-08-14: The Functional Prototype & Containerization

* **GTFS Static Ingestion & ML Baseline**
  * **Action**: Developed `train_baseline.py` to join 17.8k live delay records against the massive 880MB static `.csv` timetables to create a serialized baseline heuristic.
  * **Design Decision & Trade-offs**:
    * *Why build a simple baseline first?* Training a complex model immediately tightly couples data infrastructure bugs with model convergence issues. By deploying a simple heuristic (historical mean) first, we validated the entire end-to-end plumbing (ingestion -> transformation -> serialization -> serving). Model R&D can now happen concurrently without blocking deployment.

* **FastAPI Inference Server & Containerization**
  * **Action**: Created a CORS-enabled FastAPI server (`main.py`) and a production-ready, multi-stage `Dockerfile`.
  * **Design Decision & Trade-offs**:
    * *Why FastAPI over Flask/Django?* FastAPI's native asynchronous support is crucial for high-throughput inference APIs, though careful handling of synchronous ML model `predict()` calls is required to avoid blocking the event loop.
    * *Why Containerize?* Docker introduces a slight performance overhead and larger deployment sizes. However, ML environments (especially involving PyTorch/CUDA) are notorious for "dependency hell." Containerization guarantees that the model runs identically on my local Mac as it does on a remote Oracle Cloud Infrastructure (OCI) server or my t480 homelab.

* **Frontend Integration**
  * **Action**: Replaced the initial manual input form with a sleek, auto-refreshing React dashboard mapping to common transit lines.
  * **Design Decision & Trade-offs**:
    * *Why hardcode common lines instead of arbitrary search?* Allowing arbitrary Route/Stop ID searches provides maximum flexibility, but users rarely know precise GTFS stop IDs (e.g., `9022001010000000`). Restricting the UI to a dashboard of major lines severely limits the query space but drastically improves UX by delivering immediate, zero-click value and eliminating bad-input errors.

## 2026-08-15: Inference Modeling Foundations

* **Model Implementations**
  * **Action**: Built foundation for three predictive models:
    1. **Spatio-Temporal Graph Convolutional Network (STGCN)** using PyTorch.
    2. **Bayesian Structural Time Series (State Space)** using `statsmodels`.
    3. **Cox Proportional Hazards (Survival Analysis)** using `lifelines`.
  * **Design Decision & Trade-offs**:
    * *Why these specific paradigms?* Standard regression (OLS, Random Forests) treats stations as independent features, ignoring the physical reality of a transit network.
      * **STGCN** explicitly models how delays physically propagate down the tracks (spatial graph) over time (temporal sequence). *Trade-off*: Highly complex, black-box, and requires heavy compute.
      * **State Space** formally isolates baseline congestion from daily cyclical rush-hour patterns. *Trade-off*: Computationally expensive for large dimensions, but highly interpretable.
      * **Survival Analysis** naturally models the "time until arrival" handling right-censored data (trains that haven't arrived yet). *Trade-off*: Requires reframing the target variable away from absolute delay seconds.

## 2026-08-26: CI/CD Containerization & Zero Trust Networking

* **GitHub Actions CI/CD (Container Replacement)**
  * **Action**: Refactored the `deploy.yml` workflow to build the FastAPI Docker image on GitHub's servers, push it to GitHub Container Registry (`ghcr.io`), and then SSH into the T480 (via an OCI proxy jump host) to pull the immutable image and restart the container.
  * **Design Decision & Trade-offs**: 
    * *Why pull images instead of syncing code?* Previously, deployment relied on syncing raw files via SCP or `git pull` and building on the edge node. Building directly on GitHub Runners and pulling the compiled image ensures total environment parity, reduces compute overhead on the T480, and eliminates dependency compilation issues on the edge node.

* **Cloudflare Zero Trust Reverse Tunnel**
  * **Action**: Installed the `cloudflared` daemon natively on the T480 as a `systemd` service. Configured a `config.yml` reverse proxy to route traffic from a public custom subdomain (`metro.michiod.site`) directly into the `localhost:8000` Docker container port.
  * **Design Decision & Trade-offs**: 
    * *Why Cloudflare Tunnels instead of Nginx/Let's Encrypt?* The T480 sits behind a residential ISP connection with dynamic IP and NAT restrictions. A Cloudflare tunnel establishes a secure, outbound-only connection to Cloudflare's edge network, completely bypassing the need for port-forwarding on the router. It automatically handles HTTPS/SSL certificate generation, resolving the Mixed Content errors that occurred when the secure React dashboard attempted to fetch from a raw HTTP IP address.
    * *Implementation Note (Headless Auth)*: Authenticating `cloudflared` on a headless Linux box requires generating the `cert.pem` on a local machine (Mac) via `cloudflared tunnel login` and securely `scp`ing it to the T480, as the browser callback to `localhost` fails without a GUI.

* **DNS Management Migration**
  * **Action**: Migrated authoritative DNS servers from Namecheap's BasicDNS to Cloudflare (`renan.ns.cloudflare.com`, `ziggy.ns.cloudflare.com`) to allow the `cloudflared` daemon to automatically manage CNAME routing.

* **T480 Homelab Operations & Uptime**
  * **Action**: Configured the T480 to run continuously as a headless edge node. The `cloudflared` daemon is managed via `systemd` (`sudo systemctl enable cloudflared`), ensuring the reverse tunnel automatically re-establishes connectivity on system reboot or power failure. Docker daemon is similarly configured to restart containers automatically, ensuring high availability of the inference API without manual intervention.

* **Debugging: Docker Volume Shadowing**
  * **Action**: Resolved a critical "Model not loaded" API failure post-migration to GHCR.
  * **Design Decision & Trade-offs**: 
    * *The Bug:* The deployment script included a volume mount (`-v ~/sl-metro-predict/models:/app/models`). Because we stopped syncing raw code files to the T480 (favoring immutable images), the host directory was empty. Docker mounted this empty host directory over the container's internal `/app/models` directory, completely shadowing the `baseline_delay_model.pkl` that was successfully baked into the image during CI/CD. 
    * *The Fix:* Removed the volume mount. Relying strictly on the immutable Docker image ensures that the exact model weights compiled in CI/CD are exactly what is served in production, completely eliminating host-state dependencies.

## Discussion: Design Tradeoffs and Architecture Evaluation

This section evaluates the overarching architectural decisions made throughout the project, explicitly detailing the strengths, weaknesses, and alternatives considered for each component.

### 1. Model Weights Storage (Pickle vs. MLflow)
*   **Current State**: Model weights are serialized to a local `.pkl` file by the training script and loaded directly from disk by the FastAPI server.
*   **Strengths**: Extremely fast iteration speed during prototyping. Requires zero additional infrastructure overhead.
*   **Weaknesses**: This is a recognized MLOps anti-pattern. Pickles lack metadata (hyperparameters, training data lineage), are insecure against arbitrary code execution, and tightly couple the training compute node to the inference server.
*   **Evaluation**: Acceptable for the MVP baseline heuristic, but fundamentally incompatible with a distributed production environment. Moving forward, **MLflow Model Registry** must be implemented to store artifacts securely in MinIO, decoupling training from serving and ensuring strict lineage tracking.

### 2. Infrastructure & Orchestration (Airflow vs. Lightweight Schedulers)
*   **Decision**: Orchestrating the Medallion architecture with Apache Airflow rather than Cron or Prefect.
*   **Strengths**: Industry-standard robust handling of idempotency, backfilling (via `catchup`), and strict dependency management across heterogeneous tasks (e.g., waiting for dbt transformations before triggering PyTorch training).
*   **Weaknesses**: High operational overhead and steep learning curve. Requires significant RAM, making it impossible to run on micro-instances (e.g., a 1GB OCI server).
*   **Evaluation**: The choice is justified for a portfolio project signaling senior-level MLOps capabilities, despite the overhead forcing the deployment to heavier on-premise edge compute (T480 homelab).

### 3. Deployment Strategy (Hybrid Edge-Cloud vs. Pure Cloud)
*   **Decision**: Deploying the heavy data-crunching and inference pipeline (Airflow, MinIO, Postgres, PyTorch, FastAPI) natively on an on-premise T480 homelab, while hosting the lightweight React frontend on a 1GB Oracle Cloud (OCI) server.
*   **Strengths**: Maximizes cost-efficiency. The T480 provides sufficient CPU/RAM for heavy data engineering without incurring high cloud compute costs, while the OCI server ensures high availability for the user-facing static website.
*   **Weaknesses**: Requires complex networking configurations (e.g., Cloudflare Tunnels or Reverse Proxies with Let's Encrypt SSL) to securely bridge the HTTPS cloud frontend with the local homelab backend without violating mixed-content browser policies.
*   **Evaluation**: A highly practical and impressive architecture that demonstrates a deep understanding of resource constraints, distributed systems, and secure network tunneling.

### 4. Data Contracts (Great Expectations vs. Raw Ingestion)
*   **Decision**: Implementing strict Great Expectations schema validation at the Bronze ingestion layer.
*   **Strengths**: Prevents silent upstream schema mutations from corrupting downstream dimensional models or subtly degrading ML inference accuracy. Fails fast and alerts immediately.
*   **Weaknesses**: Increases pipeline latency. Can cause false-positive pipeline halts if the external API adds harmless fields.
*   **Evaluation**: The trade-off leans heavily toward strict contracts. In production MLOps, protecting the integrity of the feature store is paramount; serving no prediction is preferable to serving a silently corrupted one.

### 5. Frontend UX (Automated Dashboard vs. Arbitrary Input)
*   **Decision**: Hardcoding the React frontend to display an automated, real-time grid of common transit lines rather than allowing users to input arbitrary GTFS Route and Stop IDs.
*   **Strengths**: Delivers immediate, zero-click value to the user. Entirely eliminates the possibility of "Prediction unavailable" errors caused by users inputting invalid or non-existent GTFS IDs.
*   **Weaknesses**: Severely limits the query space and user freedom.
*   **Evaluation**: A strong product-minded decision. Since typical users lack knowledge of raw GTFS Stop IDs (e.g., `9022001001011001`), restricting the UI ensures a flawless, polished demonstration of the underlying API's capabilities.
