# Load Testing Dividend Payouts

## Recommended Tool: Locust (Python)

### Install
```bash
pip install locust
```

### Create `locustfile.py`

```python
from locust import HttpUser, task, between
import json

class DividendLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def trigger_dividend_payout(self):
        # Simulate triggering dividend processing for a property
        payload = {
            "property_id": 1
        }
        self.client.post("/properties/process_dividends/", 
                        json=payload,
                        headers={"Content-Type": "application/json"})
    
    @task(3)
    def view_portfolio(self):
        self.client.get("/investor/portfolio/")
```

### Run Load Test

```bash
locust -f locustfile.py --host=http://your-staging-server
```

### Target Metrics (Staging)

- **Throughput**: Handle 50–100 concurrent payout requests
- **Latency**: P95 under 2 seconds for dashboard pages
- **Celery**: Monitor queue depth during high load
- **Zcash RPC**: Ensure node can handle batch shielded transactions

### What to Monitor During Load Test

- Celery worker saturation
- Database connection pool
- Zcash node RPC response times
- Memory usage on web + worker containers
- Error rate on failed shielded transactions

**Recommendation**: Run load tests for at least 30–60 minutes with gradual ramp-up.
