# ZReal Kubernetes Deployment

This folder contains Kubernetes manifests for deploying ZReal to production.

## Structure

- `namespace.yaml`           → Namespace
- `deployment.yaml`          → Web deployment + PVC for media
- `service.yaml`             → ClusterIP Service
- `ingress.yaml`             → Ingress (Nginx + TLS)
- `configmap.yaml`           → Non-sensitive configuration
- `secrets.yaml`             → Sensitive values (DO NOT COMMIT REAL SECRETS)
- `hpa.yaml`                 → Horizontal Pod Autoscaler
- `celery-worker.yaml`       → Celery worker + beat
- `redis.yaml`               → Redis for Celery

## Quick Deployment

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml          # Edit first!
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/celery-worker.yaml
```

## Recommendations for Production

- Use **managed databases** (Cloud SQL, RDS, AlloyDB) instead of in-cluster PostgreSQL
- Use **object storage** (S3, GCS, Azure Blob) instead of PersistentVolume for media
- Store secrets in **External Secrets Operator** or cloud secret managers
- Use **cert-manager** for automatic TLS certificates
- Consider using **Helm** for better management at scale

## Image Tagging

Update the image in `deployment.yaml` and `celery-worker.yaml`:
```yaml
image: your-registry/zreal:<commit-sha>
```

## CI/CD Integration

See `.github/workflows/` for GitHub Actions example.
