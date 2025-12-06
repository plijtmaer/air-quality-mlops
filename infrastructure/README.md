# 🏗️ Infrastructure - Air Quality MLOps

Infraestructura como código para el proyecto de MLOps.

## 📋 Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) - Kubernetes in Docker
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.0.0
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

### Instalación en Windows (PowerShell)

```powershell
# Kind
choco install kind
# o con winget
winget install Kubernetes.kind

# Terraform
choco install terraform
# o con winget
winget install HashiCorp.Terraform

# kubectl
choco install kubernetes-cli
# o con winget
winget install Kubernetes.kubectl
```

## 🚀 Despliegue con Terraform

### 1. Inicializar Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 2. Ver plan de ejecución

```bash
terraform plan
```

### 3. Aplicar infraestructura

```bash
terraform apply
```

Esto creará:
- ✅ Cluster Kind con 1 control-plane + 1 worker
- ✅ Namespace `air-quality`
- ✅ ConfigMap con configuración
- ✅ Deployment con 2 réplicas
- ✅ Service NodePort

### 4. Verificar despliegue

```bash
# Ver pods
kubectl get pods -n air-quality

# Ver servicios
kubectl get svc -n air-quality

# Ver logs
kubectl logs -f deployment/air-quality-api -n air-quality
```

### 5. Acceder a la API

- **API**: http://localhost:8080
- **Swagger UI**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

### 6. Destruir infraestructura

```bash
terraform destroy
```

## 📁 Estructura

```
infrastructure/
├── terraform/
│   ├── main.tf          # Recursos principales
│   ├── variables.tf     # Variables configurables
│   ├── outputs.tf       # Outputs del despliegue
│   └── providers.tf     # Proveedores (Kind, Kubernetes)
│
└── k8s/
    ├── kind-config.yaml  # Config alternativa para Kind CLI
    ├── namespace.yaml    # Namespace
    ├── configmap.yaml    # ConfigMap
    ├── deployment.yaml   # Deployment
    ├── service.yaml      # Service
    └── hpa.yaml          # Horizontal Pod Autoscaler
```

## 🔧 Despliegue Manual (sin Terraform)

Si prefieres usar `kind` y `kubectl` directamente:

```bash
# 1. Crear cluster
kind create cluster --config infrastructure/k8s/kind-config.yaml

# 2. Cargar imagen Docker
kind load docker-image air-quality-api:latest --name air-quality-mlops

# 3. Aplicar manifiestos
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/deployment.yaml
kubectl apply -f infrastructure/k8s/service.yaml

# 4. Verificar
kubectl get pods -n air-quality

# 5. Destruir
kind delete cluster --name air-quality-mlops
```

## 📊 Monitoreo

### Ver estado de pods

```bash
kubectl get pods -n air-quality -w
```

### Ver logs en tiempo real

```bash
kubectl logs -f deployment/air-quality-api -n air-quality
```

### Escalar manualmente

```bash
kubectl scale deployment air-quality-api --replicas=3 -n air-quality
```

### Aplicar HPA (auto-scaling)

```bash
kubectl apply -f infrastructure/k8s/hpa.yaml
kubectl get hpa -n air-quality
```

## 🔍 Troubleshooting

### La API no responde

```bash
# Verificar pods
kubectl get pods -n air-quality

# Ver eventos
kubectl get events -n air-quality --sort-by='.lastTimestamp'

# Describir pod
kubectl describe pod -l app=air-quality-api -n air-quality
```

### Imagen no encontrada

```bash
# Asegurarse de que la imagen existe localmente
docker images | grep air-quality-api

# Recargar imagen en Kind
kind load docker-image air-quality-api:latest --name air-quality-mlops
```

### Reiniciar deployment

```bash
kubectl rollout restart deployment/air-quality-api -n air-quality
```

