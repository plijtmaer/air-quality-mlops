# =============================================================================
# Terraform Providers
# =============================================================================
#
# Proveedores necesarios para gestionar Kind y Kubernetes.
#
# =============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    # Provider para crear clusters Kind
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.6.0"
    }

    # Provider para gestionar recursos Kubernetes
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25.0"
    }

    # Provider para ejecutar comandos locales
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
  }
}

# Configurar el provider de Kind
provider "kind" {}

# Configurar el provider de Kubernetes
# Se conecta al cluster Kind creado
# Nota: El cluster debe existir primero, usamos alias para recursos que dependen del cluster
provider "kubernetes" {
  # Usar configuración por defecto de kubectl
  # El contexto se crea automáticamente cuando Kind crea el cluster
  config_path = "~/.kube/config"
}

