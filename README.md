## Automatic Email Categorization (LLM/ML)

This project implements an email categorization pipeline with:
- JSON email ingestion and thread assembly
- Deterministic cleaning and spam filtering
- Azure OpenAI embeddings for clustering (HDBSCAN)
- Hybrid intent detection (rules + optional LLM)
- Multi-level taxonomy labels per conversation

### Quick start

```powershell
uv venv
uv pip install -e .
email-system run .\sample-emails.json .\output.json
```

### Input JSON expectations

Each email should include fields similar to:
- `id` or `messageId`
- `conversationId` or `threadId`
- `subject`
- `body`
- `from`
- `sentDateTime` or `receivedDateTime`
- `attachments` (list of objects with `name`)

### Azure OpenAI configuration

Set these environment variables to use Azure OpenAI:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT`
- `AZURE_OPENAI_INTENT_DEPLOYMENT` (optional, for intent LLM)
- `AZURE_OPENAI_API_VERSION` (optional)

If these are not set, the pipeline falls back to a deterministic mock embedder and rule-based intent detection.

## Terraform (Azure Infrastructure)

Terraform files are in `infra/terraform`.

### Auth (local dev)

```powershell
az login
az account set --subscription "26549550-336a-47c6-b1ae-e25f43e0ab71"
$env:ARM_USE_AZURECLI_AUTH = "true"
```

### Deploy

```powershell
cd infra/terraform
terraform init
terraform apply
```

### Notes
- Default region is `eastus2`. If Azure OpenAI quota is not available there, set `-var "location=<region>"`.
- Azure OpenAI model names and versions are defaults in `infra/terraform/variables.tf`.
- App Service creation is disabled by default due to quota restrictions on many subscriptions.
  To enable it after your quota is approved:

```powershell
terraform apply -var "enable_app_service=true"
```

If App Service creation fails with quota errors, request App Service quota for the region/SKU in Azure Portal, then re-run.

### Azure OpenAI in a Different Region
You can place Azure OpenAI in a different region from the rest of the stack:

```powershell
terraform apply -var "enable_openai=true" -var "openai_location=<region>"
```

If OpenAI creation fails with a quota/feature error, choose another supported region where your subscription has Azure OpenAI access.

If you have embeddings quota but no chat quota, you can disable the intent deployment:

```powershell
terraform apply -var "enable_openai=true" -var "openai_location=<region>" -var "enable_openai_intent=false"
```

When the intent deployment is disabled, the pipeline falls back to an embeddings-based intent matcher plus rule-based scoring (no chat quota required).

### App Service in a Different Region/SKU

```powershell
terraform apply -var "enable_app_service=true" -var "app_service_location=<region>" -var "app_service_sku=P0v4"
```

### Worker Runtime
The App Service runs a background worker using:

```
python -m email_system.worker
```

It reads messages from `processing-queue`, downloads JSON blobs from `input-email`, runs the pipeline, and writes results to `output-email`.

### GitHub Actions Deployment (to avoid zip timeout)
Workflow file: `.github/workflows/deploy-appservice.yml`.

Setup steps:
1. In Azure Portal, download the App Service publish profile.
2. In GitHub repo → Settings → Secrets and variables → Actions:
   - Add secret `AZUREAPPSERVICE_PUBLISHPROFILE` (paste full publish profile XML).
3. Ensure your default branch is `main` (or update the workflow).
4. Push to `main` or run the workflow manually.
