# =============================================================================
# Terraform Variables
# =============================================================================

variable "cluster_name" {
  description = "Nombre del cluster Kind"
  type        = string
  default     = "air-quality-mlops"
}

variable "kubernetes_version" {
  description = "Versión de Kubernetes para el cluster"
  type        = string
  default     = "v1.29.2"  # Versión estable reciente
}

variable "api_image" {
  description = "Imagen Docker de la API"
  type        = string
  default     = "air-quality-api:latest"
}

variable "api_replicas" {
  description = "Número de réplicas de la API"
  type        = number
  default     = 2
}

variable "namespace" {
  description = "Namespace de Kubernetes"
  type        = string
  default     = "air-quality"
}

variable "host_port" {
  description = "Puerto del host para acceder a la API"
  type        = number
  default     = 8080
}

variable "node_port" {
  description = "NodePort para el servicio"
  type        = number
  default     = 30000
}

