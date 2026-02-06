variable "subscription_id" {
  type        = string
  description = "Azure subscription ID"
  default     = "26549550-336a-47c6-b1ae-e25f43e0ab71"
}

variable "tenant_id" {
  type        = string
  description = "Azure tenant ID"
  default     = "6f64af07-e6b4-4636-9906-401db8b0b542"
}

variable "location" {
  type        = string
  description = "Azure region"
  default     = "westus2"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for all resource names"
  default     = "emailcat"
}

variable "openai_sku" {
  type        = string
  description = "Azure OpenAI SKU"
  default     = "S0"
}

variable "openai_location" {
  type        = string
  description = "Azure OpenAI region (can differ from main region)"
  default     = "eastus2"
}

variable "enable_openai" {
  type        = bool
  description = "Whether to create Azure OpenAI resource and deployments"
  default     = true
}

variable "enable_openai_intent" {
  type        = bool
  description = "Whether to create the intent (chat) deployment"
  default     = true
}

variable "openai_embeddings_model" {
  type        = string
  description = "Embedding model name"
  default     = "text-embedding-3-large"
}

variable "openai_embeddings_version" {
  type        = string
  description = "Embedding model version"
  default     = "1"
}

variable "openai_intent_model" {
  type        = string
  description = "Chat model name for intent"
  default     = "gpt-4o-mini"
}

variable "openai_intent_version" {
  type        = string
  description = "Chat model version"
  default     = "2024-07-18"
}

variable "enable_app_service" {
  type        = bool
  description = "Whether to create App Service Plan and Web App"
  default     = false
}

variable "app_service_location" {
  type        = string
  description = "Region for App Service Plan/Web App (can differ from main region)"
  default     = "westus2"
}

variable "app_service_sku" {
  type        = string
  description = "SKU for App Service Plan"
  default     = "B1"
}
