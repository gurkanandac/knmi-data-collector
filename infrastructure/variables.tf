variable "resource_group_location" {
  type        = string
  default     = "germanywestcentral"
  description = "Location of the resource group."
}

variable "resource_group_name" {
  type        = string
  default     = "knmi-rg"
  description = "Name of the Resource Group"
}

variable "key_vault_name" {
  type        = string
  default     = "germanywestcentral"
  description = "Name of the keyvault"
}

variable "storage_account_name" {
  type        = string
  default     = "weatherstroragegrk"
  description = "Name of the storage account"
}