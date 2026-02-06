## Automatic Email Categorization (LLM/ML)

This project implements an email categorization pipeline with:
- JSON email ingestion and thread assembly
- Deterministic cleaning and spam filtering
- Azure OpenAI embeddings for clustering (HDBSCAN)
- Hybrid intent detection (rules + optional LLM)
- Multi-level taxonomy labels per conversation

## How It Works (End-to-End)

Local:
1. Load JSON emails and normalize fields.
2. Filter/clean, deduplicate, and build conversations (threads).
3. Generate embeddings (Azure OpenAI or mock fallback).
4. Cluster conversations (HDBSCAN).
5. Assign taxonomy labels and intent.
6. Output a JSON summary + conversation-level labels.

Cloud:
1. Upload a JSON blob to `input-email` container.
2. Event Grid fires `BlobCreated` event.
3. Event Grid writes a message to `processing-queue`.
4. App Service worker reads the queue message.
5. Worker downloads the blob, runs pipeline, writes `*.classified.json` to `output-email`.

## Quick Start (Local)

### Prerequisites
- Python 3.10
- `uv` installed

### Create Environment
```powershell
uv venv
uv pip install -e .
```

### Run Pipeline Locally
```powershell
email-system run .\sample-emails.json .\output.json
```

### Run Tests
```powershell
pytest
```

## Input JSON Expectations

Each email should include fields similar to:
- `id` or `messageId`
- `conversationId` or `threadId`
- `subject`
- `body`
- `from`
- `sentDateTime` or `receivedDateTime`
- `attachments` (list of objects with `name`)

## Azure OpenAI Configuration

Set these environment variables to use Azure OpenAI:
- `AZURE_OPENAI_ENDPOINT` (e.g. `https://eastus.api.cognitive.microsoft.com/`)
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` (e.g. `embeddings`)
- `AZURE_OPENAI_INTENT_DEPLOYMENT` (optional, for intent LLM)
- `AZURE_OPENAI_API_VERSION` (optional)

If these are not set, the pipeline falls back to a deterministic mock embedder and rule-based intent detection.

## Terraform (Azure Infrastructure)

Terraform files are in `infra/terraform`.

### Auth (local dev)
```powershell
az login
az account set --subscription "<your-subscription-id>"
$env:ARM_USE_AZURECLI_AUTH = "true"
```

### Deploy
```powershell
cd infra/terraform
terraform init
terraform apply
```

### Notes
- Default region is `westus2`. If Azure OpenAI quota is not available there, set `-var "openai_location=<region>"`.
- Azure OpenAI model names and versions are defaults in `infra/terraform/variables.tf`.
- App Service creation is disabled by default in Terraform.

Enable App Service after quota is approved:
```powershell
terraform apply -var "enable_app_service=true"
```

### Azure OpenAI in a Different Region
```powershell
terraform apply -var "enable_openai=true" -var "openai_location=<region>"
```

If you have embeddings quota but no chat quota:
```powershell
terraform apply -var "enable_openai=true" -var "openai_location=<region>" -var "enable_openai_intent=false"
```

### App Service in a Different Region/SKU
```powershell
terraform apply -var "enable_app_service=true" -var "app_service_location=<region>" -var "app_service_sku=B1"
```

## Worker Runtime (Cloud)

The App Service runs a background worker with a health endpoint:
```
python -m email_system.webapp
```

This starts:
- a minimal HTTP server (returns `ok` at `/`)
- a worker thread that processes queue messages

## GitHub Actions Deployment (Recommended)

Workflow file: `.github/workflows/deploy-appservice.yml`

Setup steps:
1. In Azure Portal, download the App Service publish profile.
2. In GitHub repo -> Settings -> Secrets and variables -> Actions:
   - Add secret `AZUREAPPSERVICE_PUBLISHPROFILE` (paste full publish profile XML).
3. Ensure your default branch is `main`.
4. Push to `main` or run the workflow manually.

## Cloud Runbook (Test End-to-End)

### Upload Input Blob
```powershell
$env:AZURE_CONFIG_DIR = "$env:TEMP\azcfg-new"
$SA_KEY = az storage account keys list -g <rg> -n <storage> --query "[0].value" -o tsv
$blobName = "email-" + (Get-Date -Format "HHmmss") + ".json"

az storage blob upload `
  --account-name <storage> `
  --account-key $SA_KEY `
  --container-name input-email `
  --name $blobName `
  --file D:\path\to\your\file.json `
  --overwrite
```

### Check Output Blob
```powershell
az storage blob list `
  --account-name <storage> `
  --account-key $SA_KEY `
  --container-name output-email `
  -o table
```

## Troubleshooting

- `BlobNotFound` in logs:
  Old queue messages are referencing blobs that no longer exist. Clear queue:
  ```powershell
  az storage message clear --account-name <storage> --account-key $SA_KEY --queue-name processing-queue
  ```

- `Unexpected UTF-8 BOM`:
  Your JSON file was saved with BOM. The worker now handles BOM safely.

- Azure OpenAI `401`:
  Confirm `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` are correct.

- App Service 409 during deploy:
  Do not restart the app during deployment; retry after a few minutes.

## Security Notes

- Do not commit `publishProfile.xml` or any secrets.
- Rotate publish profile and Azure OpenAI keys if you shared them anywhere.









use env in local file 

Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $name, $value = $_ -split '=', 2
  if ($name -and $value) {
    $env:$name = $value.Trim().Trim('"')
  }
}




Example .env:

AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=embeddings
AZURE_OPENAI_API_VERSION=2024-02-15-preview
