# Hammad Bootcamp - CI/CD Demo
This repository demonstrates two GitHub Actions workflows:
1. **Postman API Tests**: run an existing Postman Collection in CI.
2. **TechCorp API Ingestion**: export (or load) an OpenAPI spec, sync it to **Postman Spec Hub**, and trigger a generated baseline collection.

## Lab 3.3: Automated API Tests (Collection Run)
### Configure GitHub Secrets
Add these secrets under **Settings → Secrets and variables → Actions**:
- `POSTMAN_API_KEY`
- `POSTMAN_COLLECTION_ID`
- `POSTMAN_ENVIRONMENT_ID` (optional)

### Run
This workflow runs on:
- Push to `main`
- Pull requests to `main`
- Manual trigger (`workflow_dispatch`)

Workflow file: `.github/workflows/postman-tests.yml`

### Outputs
Test results are uploaded as artifacts and retained for 30 days.

## Lab 3.4: TechCorp API Ingestion (API Gateway → Spec Hub)
### What it does
- **Export the Spec from API Gateway** (AWS export mode)
- **Sync Spec → Spec Hub → Generated Collection** (baseline regen)
- **GitHub Actions Workflow** to run ingestion on push / manual dispatch / schedule

Workflow file: `.github/workflows/postman-ingestion.yml`

### Configure GitHub Secrets
AWS export is the **required** path for this lab.

Required:
- `POSTMAN_API_KEY`
- `POSTMAN_WORKSPACE_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `REST_API_ID`
- `STAGE_NAME`

Optional (fallback / local spec mode):
- Commit an `openapi.yaml` to the repo (or provide a different file via `--local-spec` when running locally)

### Ways to run
#### 1) GitHub Actions (recommended)
Triggers:
- Push to `main`
- Manual trigger (`workflow_dispatch`) with optional input `spec_name`
- Scheduled weekly run (Mondays at 06:00 UTC)

#### 2) Local run (AWS export mode)
```bash path=null start=null
export POSTMAN_API_KEY="PMAK-..."
python ingest_from_apigw.py \
  --workspace-id "<POSTMAN_WORKSPACE_ID>" \
  --region "<AWS_REGION>" \
  --rest-api-id "<REST_API_ID>" \
  --stage-name "<STAGE_NAME>" \
  --spec-name "TechCorp Payments API (Spec Hub)"
```

#### 3) Local run (committed spec fallback)
Commit an `openapi.yaml` to the repo, then run:
```bash path=null start=null
export POSTMAN_API_KEY="PMAK-..."
python ingest_from_apigw.py \
  --workspace-id "<POSTMAN_WORKSPACE_ID>" \
  --local-spec openapi.yaml \
  --spec-name "TechCorp Payments API (Spec Hub)"
```
