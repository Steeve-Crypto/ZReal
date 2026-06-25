# Load Testing

The current app should be load-tested around real implemented flows:

- property map
- signup/login
- issuer dashboard
- property create/edit
- document upload
- tokenization attempt submission

Dividend payout load testing is not applicable yet because payout execution is not implemented.

Example Locust targets:

```python
from locust import HttpUser, task, between


class ZRealUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def map(self):
        self.client.get("/properties/map/")

    @task(2)
    def issuer_dashboard(self):
        self.client.get("/issuer/dashboard/")
```

Run:

```bash
locust -f locustfile.py --host=http://127.0.0.1:8000
```
