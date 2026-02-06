provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  prefix = "${var.name_prefix}-${random_string.suffix.result}"
}

resource "azurerm_resource_group" "main" {
  name     = "${local.prefix}-rg"
  location = var.location
}

resource "azurerm_storage_account" "main" {
  name                     = replace("${local.prefix}sa", "-", "")
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "input" {
  name                  = "input-email"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "output" {
  name                  = "output-email"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_queue" "processing" {
  name                 = "processing-queue"
  storage_account_id   = azurerm_storage_account.main.id
}

resource "azurerm_eventgrid_system_topic" "blob_topic" {
  name                = "${local.prefix}-blob-topic"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  source_arm_resource_id = azurerm_storage_account.main.id
  topic_type          = "Microsoft.Storage.StorageAccounts"
}

resource "azurerm_eventgrid_system_topic_event_subscription" "blob_created_to_queue" {
  name  = "${local.prefix}-blobcreated-sub"
  resource_group_name = azurerm_resource_group.main.name
  system_topic        = azurerm_eventgrid_system_topic.blob_topic.name

  included_event_types = ["Microsoft.Storage.BlobCreated"]

  subject_filter {
    subject_begins_with = "/blobServices/default/containers/${azurerm_storage_container.input.name}/"
  }

  storage_queue_endpoint {
    storage_account_id = azurerm_storage_account.main.id
    queue_name         = azurerm_storage_queue.processing.name
  }
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.prefix}-law"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "main" {
  name                = "${local.prefix}-appi"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_key_vault" "main" {
  name                        = "${local.prefix}-kv"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = var.tenant_id
  sku_name                    = "standard"
  purge_protection_enabled    = false
  soft_delete_retention_days  = 7
}

resource "azurerm_service_plan" "main" {
  count               = var.enable_app_service ? 1 : 0
  name                = "${local.prefix}-plan"
  location            = var.app_service_location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku
}

resource "azurerm_linux_web_app" "main" {
  count               = var.enable_app_service ? 1 : 0
  name                = "${local.prefix}-app"
  location            = var.app_service_location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main[0].id

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "AZURE_OPENAI_ENDPOINT"              = var.enable_openai ? azurerm_cognitive_account.openai[0].endpoint : ""
    "AZURE_OPENAI_API_VERSION"           = "2024-02-15-preview"
    "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT" = var.enable_openai ? azurerm_cognitive_deployment.embeddings[0].name : ""
    "AZURE_OPENAI_INTENT_DEPLOYMENT"     = var.enable_openai && var.enable_openai_intent ? azurerm_cognitive_deployment.intent[0].name : ""
    "STORAGE_ACCOUNT_NAME"               = azurerm_storage_account.main.name
    "INPUT_CONTAINER"                    = azurerm_storage_container.input.name
    "OUTPUT_CONTAINER"                   = azurerm_storage_container.output.name
    "PROCESSING_QUEUE"                   = azurerm_storage_queue.processing.name
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
  }

  site_config {
    always_on = true
    application_stack {
      python_version = "3.10"
    }
    app_command_line = "python -m email_system.worker"
  }
}

resource "azurerm_role_assignment" "app_storage_blob" {
  count               = var.enable_app_service ? 1 : 0
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_web_app.main[0].identity[0].principal_id
}

resource "azurerm_role_assignment" "app_storage_queue" {
  count               = var.enable_app_service ? 1 : 0
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_linux_web_app.main[0].identity[0].principal_id
}

resource "azurerm_key_vault_access_policy" "app_kv_policy" {
  count       = var.enable_app_service ? 1 : 0
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = var.tenant_id
  object_id    = azurerm_linux_web_app.main[0].identity[0].principal_id

  secret_permissions = ["Get", "List"]
}

resource "azurerm_cognitive_account" "openai" {
  count               = var.enable_openai ? 1 : 0
  name                = "${local.prefix}-aoai"
  location            = var.openai_location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = var.openai_sku
}

resource "azurerm_cognitive_deployment" "embeddings" {
  count                = var.enable_openai ? 1 : 0
  name                 = "embeddings"
  cognitive_account_id = azurerm_cognitive_account.openai[0].id

  model {
    format  = "OpenAI"
    name    = var.openai_embeddings_model
    version = var.openai_embeddings_version
  }

  sku {
    name     = "Standard"
    capacity = 1
  }
}

resource "azurerm_cognitive_deployment" "intent" {
  count                = var.enable_openai && var.enable_openai_intent ? 1 : 0
  name                 = "intent"
  cognitive_account_id = azurerm_cognitive_account.openai[0].id

  model {
    format  = "OpenAI"
    name    = var.openai_intent_model
    version = var.openai_intent_version
  }

  sku {
    name     = "Standard"
    capacity = 1
  }
}
