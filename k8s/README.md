# ZReal Kubernetes Deployment

This directory contains Kubernetes manifests for the Django backend services.

## Files

- `namespace.yaml`: namespace
- `deployment.yaml`: web deployment and media PVC
- `service.yaml`: web service
- `ingress.yaml`: ingress
- `configmap.yaml`: non-sensitive runtime configuration
- `SECRET_REQUIREMENTS.md`: required Secret keys without values
- `hpa.yaml`: horizontal pod autoscaler
- `celery-worker.yaml`: Celery worker and beat manifests
- `redis.yaml`: Redis

## Required Secret

Create the `zreal-secrets` Secret before applying deployments:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic zreal-secrets --namespace zreal ...
```

Use `SECRET_REQUIREMENTS.md` for the exact key list. Do not commit a Secret manifest containing credentials or placeholder values.

## Apply

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/celery-worker.yaml
```

## Image

CI publishes backend images to:

```text
ghcr.io/steeve-crypto/zreal
```

Use immutable commit SHA tags for production deploys.
