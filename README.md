# Hammad Bootcamp - CI/CD Demo

This repository demonstrates automated Postman API testing using GitHub Actions.

## Setup Instructions

### Step 1: Configure GitHub Secrets

Go to your repository's Settings → Secrets and variables → Actions, and add these secrets:

- `POSTMAN_API_KEY`: Your Postman API key
- `POSTMAN_COLLECTION_ID`: Your collection ID (format: 12345678-abcd-efgh-ijkl-123456789abc)
- `POSTMAN_ENVIRONMENT_ID`: Your environment ID (optional, for cloud publishing)

### Step 2: Run the Workflow

The workflow automatically runs on:
- Push to `main` branch
- Pull requests to `main` branch
- Manual trigger (workflow_dispatch)

You can also manually trigger the workflow from the Actions tab in GitHub.

## Test Results

Test results are uploaded as artifacts and retained for 30 days.
