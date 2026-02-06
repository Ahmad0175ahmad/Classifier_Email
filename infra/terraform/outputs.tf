output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "storage_account" {
  value = azurerm_storage_account.main.name
}

output "input_container" {
  value = azurerm_storage_container.input.name
}

output "output_container" {
  value = azurerm_storage_container.output.name
}

output "processing_queue" {
  value = azurerm_storage_queue.processing.name
}

output "web_app_name" {
  value = var.enable_app_service ? azurerm_linux_web_app.main[0].name : ""
}

output "openai_endpoint" {
  value = var.enable_openai ? azurerm_cognitive_account.openai[0].endpoint : ""
}
