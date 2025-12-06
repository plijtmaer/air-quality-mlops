# =============================================================================
# Terraform Outputs
# =============================================================================

output "cluster_name" {
  description = "Nombre del cluster Kind"
  value       = kind_cluster.air_quality.name
}

output "kubeconfig_path" {
  description = "Ruta al archivo kubeconfig"
  value       = kind_cluster.air_quality.kubeconfig_path
}

output "api_url" {
  description = "URL para acceder a la API"
  value       = "http://localhost:${var.host_port}"
}

output "swagger_url" {
  description = "URL de Swagger UI"
  value       = "http://localhost:${var.host_port}/docs"
}

output "health_url" {
  description = "URL del health check"
  value       = "http://localhost:${var.host_port}/health"
}

output "namespace" {
  description = "Namespace de Kubernetes"
  value       = kubernetes_namespace.air_quality.metadata[0].name
}

output "deployment_name" {
  description = "Nombre del deployment"
  value       = kubernetes_deployment.api.metadata[0].name
}

output "service_name" {
  description = "Nombre del servicio"
  value       = kubernetes_service.api.metadata[0].name
}

output "kubectl_commands" {
  description = "Comandos útiles de kubectl"
  value = <<-EOT
    
    # Ver pods
    kubectl get pods -n ${var.namespace}
    
    # Ver logs
    kubectl logs -f deployment/air-quality-api -n ${var.namespace}
    
    # Describir deployment
    kubectl describe deployment air-quality-api -n ${var.namespace}
    
    # Port forward (alternativo)
    kubectl port-forward svc/air-quality-api 8080:80 -n ${var.namespace}
    
  EOT
}

