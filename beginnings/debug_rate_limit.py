#!/usr/bin/env python3
"""Debug script to understand rate limiting behavior."""

import tempfile
import yaml
from pathlib import Path
from fastapi.testclient import TestClient
from beginnings import App

# Create test config
config = {
    "app": {"name": "debug_test", "version": "1.0.0"},
    "routes": {
        "/api/limited": {
            "rate_limit": 2,  # Allow 2 requests
            "logging_enabled": True
        }
    },
    "extensions": {
        "tests.test_e2e_requests:RateLimitExtension": {"enabled": True}
    }
}

temp_dir = tempfile.mkdtemp()
config_file = Path(temp_dir) / "app.yaml"
with open(config_file, "w") as f:
    yaml.safe_dump(config, f)

# Create app
app = App(config_dir=temp_dir, environment="development")
api_router = app.create_api_router()

@api_router.get("/api/limited")
def limited_endpoint():
    return {"message": "rate limited endpoint", "success": True}

app.include_router(api_router)
client = TestClient(app)

# Test requests
print("Testing rate limiting with limit=2...")
for i in range(5):
    response = client.get("/api/limited")
    print(f"Request {i+1}: Status {response.status_code} - {response.json() if response.status_code == 200 else response.text}")

print("Done.")