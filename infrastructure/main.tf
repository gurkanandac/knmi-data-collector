data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.resource_group_location
}

resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  depends_on = [azurerm_resource_group.rg]
}


resource "azurerm_service_plan" "func_plan" {
  name                = "weather-func-plan"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
  depends_on = [azurerm_resource_group.rg]
}

resource "azurerm_linux_function_app" "scheduled_func" {
  name                       = "weather-scheduled-func"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  service_plan_id            = azurerm_service_plan.func_plan.id
  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key
  site_config {
    application_stack {
      python_version = "3.11"
    }
  }
    identity {
      type = "SystemAssigned"
    }
  depends_on = [azurerm_service_plan.func_plan, azurerm_storage_account.storage]
}

  resource "azurerm_key_vault" "kv" {
    name                        = "weather-keyvault-grk"
    location                    = azurerm_resource_group.rg.location
    resource_group_name         = azurerm_resource_group.rg.name
    tenant_id                   = data.azurerm_client_config.current.tenant_id
    sku_name                    = "standard"

    access_policy {
      tenant_id = data.azurerm_client_config.current.tenant_id
      object_id = data.azurerm_client_config.current.object_id

      key_permissions         = ["Get", "List"]
      secret_permissions      = ["Get", "List", "Set", "Delete"]
      certificate_permissions = ["Get", "List"]
  }
  
    access_policy {
      tenant_id = data.azurerm_client_config.current.tenant_id
      object_id = azurerm_linux_function_app.scheduled_func.identity[0].principal_id
      key_permissions        = ["Get", "List"]
      secret_permissions     = ["Get", "List"]
      certificate_permissions = ["Get", "List"]
    }

    depends_on = [azurerm_resource_group.rg, azurerm_linux_function_app.scheduled_func]
  }