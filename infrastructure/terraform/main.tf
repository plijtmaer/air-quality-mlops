# =============================================================================
# Terraform Main - Air Quality MLOps Infrastructure
# =============================================================================
#
# Este archivo define la infraestructura completa:
# - Cluster Kind (Kubernetes local)
# - Namespace
# - ConfigMap
# - Deployment
# - Service
#
# Uso:
#   cd infrastructure/terraform
#   terraform init
#   terraform plan
#   terraform apply
#
# =============================================================================

# -----------------------------------------------------------------------------
# Kind Cluster
# -----------------------------------------------------------------------------
resource "kind_cluster" "air_quality" {
  name           = var.cluster_name
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      kubeadm_config_patches = [
        <<-EOT
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
        EOT
      ]

      extra_port_mappings {
        container_port = var.node_port
        host_port      = var.host_port
        protocol       = "TCP"
      }

      extra_port_mappings {
        container_port = 80
        host_port      = 80
        protocol       = "TCP"
      }

      extra_port_mappings {
        container_port = 443
        host_port      = 443
        protocol       = "TCP"
      }
    }

    node {
      role = "worker"
    }
  }
}

# -----------------------------------------------------------------------------
# Cargar imagen Docker en Kind
# -----------------------------------------------------------------------------
resource "null_resource" "load_docker_image" {
  depends_on = [kind_cluster.air_quality]

  provisioner "local-exec" {
    command = "kind load docker-image ${var.api_image} --name ${var.cluster_name}"
  }

  triggers = {
    cluster_id = kind_cluster.air_quality.id
    image      = var.api_image
  }
}

# -----------------------------------------------------------------------------
# Namespace
# -----------------------------------------------------------------------------
resource "kubernetes_namespace" "air_quality" {
  depends_on = [kind_cluster.air_quality]

  metadata {
    name = var.namespace

    labels = {
      app         = "air-quality-mlops"
      environment = "development"
      managed-by  = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# ConfigMap
# -----------------------------------------------------------------------------
resource "kubernetes_config_map" "api_config" {
  depends_on = [kubernetes_namespace.air_quality]

  metadata {
    name      = "air-quality-config"
    namespace = var.namespace

    labels = {
      app = "air-quality-api"
    }
  }

  data = {
    LOG_LEVEL           = "info"
    PYTHONPATH          = "/app"
    MLFLOW_TRACKING_URI = "https://dagshub.com/plijtmaer/air-quality-mlops.mlflow"
  }
}

# -----------------------------------------------------------------------------
# Deployment
# -----------------------------------------------------------------------------
resource "kubernetes_deployment" "api" {
  depends_on = [
    kubernetes_namespace.air_quality,
    kubernetes_config_map.api_config,
    null_resource.load_docker_image
  ]

  metadata {
    name      = "air-quality-api"
    namespace = var.namespace

    labels = {
      app     = "air-quality-api"
      version = "v1"
    }
  }

  spec {
    replicas = var.api_replicas

    selector {
      match_labels = {
        app = "air-quality-api"
      }
    }

    template {
      metadata {
        labels = {
          app     = "air-quality-api"
          version = "v1"
        }
      }

      spec {
        container {
          name              = "api"
          image             = var.api_image
          image_pull_policy = "Never"  # Usar imagen local

          port {
            container_port = 8000
            name           = "http"
            protocol       = "TCP"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.api_config.metadata[0].name
            }
          }

          resources {
            requests = {
              memory = "512Mi"
              cpu    = "250m"
            }
            limits = {
              memory = "2Gi"
              cpu    = "1000m"
            }
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 60
            period_seconds        = 30
            timeout_seconds       = 10
            failure_threshold     = 3
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          volume_mount {
            name       = "reports-volume"
            mount_path = "/app/reports"
          }
        }

        volume {
          name = "reports-volume"
          empty_dir {}
        }
      }
    }

    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = "1"
        max_unavailable = "0"
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Service
# -----------------------------------------------------------------------------
resource "kubernetes_service" "api" {
  depends_on = [kubernetes_deployment.api]

  metadata {
    name      = "air-quality-api"
    namespace = var.namespace

    labels = {
      app = "air-quality-api"
    }
  }

  spec {
    type = "NodePort"

    selector = {
      app = "air-quality-api"
    }

    port {
      name        = "http"
      port        = 80
      target_port = 8000
      node_port   = var.node_port
      protocol    = "TCP"
    }
  }
}

