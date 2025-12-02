# Architecture

This document provides a detailed technical overview of the GitHub Custom Deployment Protection Rule implementation.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Authentication Flow](#authentication-flow)
5. [Deployment Lifecycle](#deployment-lifecycle)
6. [Security Considerations](#security-considerations)
7. [Scalability and Reliability](#scalability-and-reliability)

---

## System Overview

The GitHub Custom Deployment Protection Rule system enables automated approval/rejection of deployments based on custom business logic. This implementation specifically auto-approves deployments triggered by schedules while requiring manual review for other trigger types.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Platform                         │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │   GitHub     │    │   GitHub     │    │  Custom GitHub  │  │
│  │   Actions    │───▶│ Environments │◀───│      App        │  │
│  │  (Workflow)  │    │ (Protection) │    │  (Integration)  │  │
│  └──────────────┘    └──────────────┘    └─────────────────┘  │
│         │                    │                      │          │
└─────────┼────────────────────┼──────────────────────┼──────────┘
          │                    │                      │
          │ ①Deployment        │ ③Webhook             │
          │  Request           │  Event               │
          │                    │                      │
          ▼                    ▼                      │
    ┌─────────────────────────────────────────┐      │
    │        Webhook Server                   │      │
    │                                         │      │
    │  ┌─────────────────────────────────┐   │      │
    │  │   Flask Application             │   │      │
    │  │                                 │   │      │
    │  │  • Signature Validation         │   │      │
    │  │  • Event Processing             │   │      │
    │  │  • Decision Logic               │   │      │
    │  └─────────────────────────────────┘   │      │
    │                │                        │      │
    │  ┌─────────────▼────────────────────┐  │      │
    │  │   Authentication Module          │  │      │
    │  │                                  │  │      │
    │  │  • JWT Generation (RS256)        │  │      │
    │  │  • Installation Token Exchange   │  │      │
    │  └──────────────────────────────────┘  │      │
    │                │                        │      │
    └────────────────┼─────────────────────────┘      │
                     │                                │
                     │ ④API Call                      │
                     │  (Approve/Reject)              │
                     └────────────────────────────────┘
```

### Key Components

1. **GitHub Actions Workflow** (`deploy-with-protection.yml`)
   - Defines deployment jobs
   - Specifies target environment
   - Triggers deployment protection check

2. **GitHub Environment** (production)
   - Stores secrets (EXAMPLE_SEC)
   - Enforces protection rules
   - Manages reviewers

3. **GitHub App** (Custom Integration)
   - Receives webhook events
   - Has necessary permissions
   - Authenticates API calls

4. **Webhook Server** (Python Flask)
   - Processes webhook events
   - Implements decision logic
   - Approves/rejects deployments

---

## Component Architecture

### GitHub Actions Workflow

**File**: `.github/workflows/deploy-with-protection.yml`

**Purpose**: Orchestrate deployment process with protection checks

**Key Features**:
```yaml
# Multiple trigger types
on:
  schedule:              # Auto-approved
  workflow_dispatch:     # Manual review
  push:                  # Manual review

# Environment protection
jobs:
  deploy:
    environment: 
      name: production
      url: https://example.com
    
    steps:
      - name: Wait for Approval
        run: echo "Waiting..."  # Pauses here
      
      - name: Display Secret
        run: echo "${{ secrets.EXAMPLE_SEC }}"
```

**Concurrency Control**:
```yaml
concurrency:
  group: production-deployment
  cancel-in-progress: false  # Don't cancel running deployments
```

### Webhook Server Architecture

**File**: `webhook-server/app.py`

**Layers**:

```
┌───────────────────────────────────────────┐
│         HTTP Interface (Flask)            │
│  • /webhook (POST) - Main endpoint        │
│  • /health (GET) - Health check           │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│       Request Validation Layer            │
│  • Signature verification (HMAC SHA-256)  │
│  • Event type validation                  │
│  • Payload parsing                        │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│         Business Logic Layer              │
│  • Extract event metadata                 │
│  • Apply decision rules                   │
│  • Determine action (approve/reject)      │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│      Authentication Layer                 │
│  • JWT generation                         │
│  • Installation token exchange            │
│  • Token caching (future enhancement)     │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│        GitHub API Client                  │
│  • POST deployment_protection_rule        │
│  • Error handling and retry logic         │
│  • Response processing                    │
└───────────────────────────────────────────┘
```

**Key Modules**:

1. **Signature Verification**
   ```python
   def verify_webhook_signature(payload_body, signature_header):
       mac = hmac.new(secret, payload_body, hashlib.sha256)
       return hmac.compare_digest(signature, mac.hexdigest())
   ```

2. **JWT Generation**
   ```python
   def generate_jwt():
       payload = {
           'iat': now - 60,
           'exp': now + (10 * 60),
           'iss': app_id
       }
       return jwt.encode(payload, private_key, algorithm='RS256')
   ```

3. **Decision Engine**
   ```python
   if event == 'schedule':
       approve_deployment(...)
   else:
       # Require manual review
       return {'message': 'Requires manual review'}
   ```

---

## Data Flow

### Complete Request Flow

```
1. Workflow Triggers
   ├─ Schedule: Cron timer fires
   ├─ Manual: User clicks "Run workflow"
   └─ Push: Code pushed to main branch
          │
          ▼
2. Workflow Executes
   ├─ Checks out code
   ├─ Runs initial steps
   └─ Reaches environment protection
          │
          ▼
3. Environment Protection Engaged
   ├─ Required reviewers check
   └─ Custom protection rule check ◀─── Our implementation
          │
          ▼
4. GitHub Sends Webhook
   POST https://webhook-server.com/webhook
   Headers:
     X-Hub-Signature-256: sha256=abc123...
     X-GitHub-Event: deployment_protection_rule
     X-GitHub-Delivery: uuid
   Body:
     {
       "action": "requested",
       "environment": "production",
       "event": "schedule|workflow_dispatch|push",
       ...
     }
          │
          ▼
5. Webhook Server Receives Request
   ├─ Validates signature
   ├─ Parses payload
   └─ Extracts metadata
          │
          ▼
6. Decision Logic Executes
   if event == "schedule":
     ├─ Generate JWT token
     ├─ Get installation token
     ├─ Call GitHub API to approve
     └─ Return success
   else:
     └─ Return "manual review required"
          │
          ▼
7. GitHub Processes Response
   if approved:
     ├─ Resume workflow execution
     ├─ Run remaining steps
     └─ Mark deployment as successful
   else:
     └─ Keep workflow paused
          │
          ▼
8. Deployment Completes
   ├─ Notify step runs
   └─ Workflow finishes
```

### Webhook Payload Structure

**deployment_protection_rule Event**:

```json
{
  "action": "requested",
  "environment": "production",
  "event": "schedule",  // ← Key field for decision
  "deployment_callback_url": "https://api.github.com/...",
  "deployment": {
    "id": 12345,
    "environment": "production",
    "task": "deploy"
  },
  "repository": {
    "name": "my-repo",
    "owner": {"login": "my-org"}
  },
  "installation": {
    "id": 99999  // ← Used for authentication
  }
}
```

### API Request/Response

**Approval Request**:

```http
POST /repos/{owner}/{repo}/actions/runs/{run_id}/deployment_protection_rule
Authorization: Bearer <installation_token>
Content-Type: application/json

{
  "environment_name": "production",
  "state": "approved",
  "comment": "Auto-approved: Scheduled deployment"
}
```

**Response**:

```http
HTTP/1.1 204 No Content
```

---

## Authentication Flow

### GitHub App Authentication Process

```
1. Server Needs to Make API Call
          │
          ▼
2. Generate JWT Token
   ┌─────────────────────────────────────┐
   │ Algorithm: RS256                    │
   │ Private Key: From .pem file         │
   │ Payload:                            │
   │   {                                 │
   │     "iat": now - 60,               │
   │     "exp": now + 600,              │
   │     "iss": "123456"  // App ID     │
   │   }                                 │
   └──────────────┬──────────────────────┘
                  │ Valid for 10 minutes
                  ▼
3. Exchange JWT for Installation Token
   POST /app/installations/{id}/access_tokens
   Authorization: Bearer <jwt>
          │
          ▼ Response
   {
     "token": "ghs_...",       // Installation token
     "expires_at": "2024-...", // 1 hour expiry
     "permissions": {
       "actions": "write",
       "deployments": "write"
     }
   }
          │
          ▼
4. Use Installation Token for API Calls
   POST /repos/{owner}/{repo}/actions/runs/{id}/deployment_protection_rule
   Authorization: Bearer <installation_token>
          │
          ▼
5. Token Expiry and Renewal
   ├─ JWT: Max 10 minutes (regenerate as needed)
   └─ Installation Token: 1 hour (cache and refresh)
```

### Security Token Hierarchy

```
┌─────────────────────────────────────────────┐
│ Private Key (.pem file)                     │
│ • Generated once during app creation        │
│ • Stored securely, never exposed            │
│ • Used to sign JWT tokens                   │
└──────────────┬──────────────────────────────┘
               │ Signs
               ▼
┌─────────────────────────────────────────────┐
│ JWT Token                                   │
│ • Short-lived (max 10 minutes)              │
│ • Used to authenticate as the GitHub App    │
│ • Proves app identity                       │
└──────────────┬──────────────────────────────┘
               │ Exchanges for
               ▼
┌─────────────────────────────────────────────┐
│ Installation Token                          │
│ • Valid for 1 hour                          │
│ • Scoped to specific installation           │
│ • Has specific permissions                  │
│ • Used for actual API calls                 │
└─────────────────────────────────────────────┘
```

---

## Deployment Lifecycle

### Complete Deployment State Machine

```
┌──────────────┐
│   PENDING    │  Workflow waiting to run
└──────┬───────┘
       │ Triggered
       ▼
┌──────────────┐
│   QUEUED     │  Waiting for runner availability
└──────┬───────┘
       │ Runner assigned
       ▼
┌──────────────┐
│  IN_PROGRESS │  Workflow executing steps
└──────┬───────┘
       │ Reaches environment protection
       ▼
┌──────────────┐
│   WAITING    │◀─── deployment_protection_rule webhook sent
└──────┬───────┘
       │ Custom protection rule decision
       ├─────────────────┬─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   APPROVED   │  │   WAITING    │  │   REJECTED   │
│  (automated) │  │  (for human) │  │  (webhook)   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │ Manual         │
       │                 │ approval       │
       │                 ▼                │
       │          ┌──────────────┐        │
       │          │   APPROVED   │        │
       │          │   (manual)   │        │
       │          └──────┬───────┘        │
       │                 │                │
       ├─────────────────┘                │
       │                                  │
       ▼                                  ▼
┌──────────────┐                   ┌──────────────┐
│ IN_PROGRESS  │                   │   FAILURE    │
│ (continues)  │                   └──────────────┘
└──────┬───────┘
       │ Deployment steps complete
       ▼
┌──────────────┐
│   SUCCESS    │
└──────────────┘
```

### Auto-Approval vs Manual Review

**Auto-Approval Path** (Schedule Trigger):
```
Workflow triggered by schedule
    ↓
deployment_protection_rule event sent
    ↓ event: "schedule"
Webhook server receives request
    ↓
Decision: Auto-approve
    ↓
Generate JWT → Get installation token
    ↓
POST to GitHub API with state: "approved"
    ↓
Workflow resumes immediately
    ↓
Deployment completes
```

**Manual Review Path** (Manual/Push Trigger):
```
Workflow triggered by manual or push
    ↓
deployment_protection_rule event sent
    ↓ event: "workflow_dispatch" or "push"
Webhook server receives request
    ↓
Decision: Require manual review
    ↓
Webhook responds with "manual review required"
    ↓
Workflow remains paused
    ↓
Human reviewer visits environment page
    ↓
Reviewer clicks "Approve deployment"
    ↓
Workflow resumes
    ↓
Deployment completes
```

---

## Security Considerations

### Webhook Signature Verification

**Why It's Critical**:
- Prevents unauthorized API calls to your server
- Ensures webhooks are genuinely from GitHub
- Protects against replay attacks

**Implementation**:
```python
# GitHub sends: X-Hub-Signature-256: sha256=<signature>
expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
received = signature_header.split('=')[1]

if not hmac.compare_digest(expected, received):
    return 401  # Reject
```

**Best Practices**:
- Use `hmac.compare_digest()` to prevent timing attacks
- Generate strong webhook secrets (32+ bytes)
- Rotate secrets periodically
- Never log webhook secrets

### Private Key Security

**Storage**:
- ✅ Store in secure location with restricted permissions
- ✅ Use environment variables for paths
- ✅ Mount as read-only in containers
- ❌ Never commit to version control
- ❌ Never expose in logs or error messages

**Access Control**:
```bash
# Set restrictive permissions
chmod 600 webhook-server/keys/private-key.pem

# Docker: mount read-only
volumes:
  - ./keys/private-key.pem:/app/keys/private-key.pem:ro
```

### Token Management

**JWT Tokens**:
- Short-lived (max 10 minutes)
- Generated on-demand
- Not cached (in current implementation)
- Signed with RS256 algorithm

**Installation Tokens**:
- Valid for 1 hour
- Scoped to specific installation
- Should be cached (future enhancement)
- Never exposed to clients

**Recommended Caching Strategy**:
```python
# Cache installation tokens
token_cache = {}

def get_installation_token(installation_id):
    cached = token_cache.get(installation_id)
    if cached and cached['expires_at'] > now + 5*60:
        return cached['token']
    
    # Generate new token
    new_token = exchange_jwt_for_token(installation_id)
    token_cache[installation_id] = new_token
    return new_token['token']
```

### Network Security

**HTTPS Everywhere**:
- Webhook URL must use HTTPS (GitHub requirement)
- API calls to GitHub use HTTPS
- TLS 1.2 or higher

**Firewall Rules**:
- Allow inbound HTTPS (443) from GitHub IPs
- Restrict outbound to necessary destinations
- Consider using GitHub's published IP ranges

**Rate Limiting**:
```python
# Future enhancement: Add rate limiting
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/webhook')
@limiter.limit("100 per minute")
def handle_webhook():
    ...
```

---

## Scalability and Reliability

### Current Architecture Limitations

**Single Instance**:
- No horizontal scaling
- Single point of failure
- Limited throughput

**Stateless Design** (Good):
- No session storage
- No database required
- Easy to replicate

### Scaling Strategies

#### Horizontal Scaling

```
                  ┌─────────────────┐
                  │  Load Balancer  │
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Webhook  │     │ Webhook  │     │ Webhook  │
    │ Server 1 │     │ Server 2 │     │ Server 3 │
    └──────────┘     └──────────┘     └──────────┘
```

**Configuration**:
```yaml
# docker-compose-scaled.yml
version: '3.8'
services:
  webhook-server:
    build: ./webhook-server
    deploy:
      replicas: 3
      
  nginx:
    image: nginx
    ports:
      - "443:443"
    depends_on:
      - webhook-server
```

#### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webhook-server
  template:
    spec:
      containers:
      - name: webhook-server
        image: deployment-protection-webhook:latest
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: webhook-service
spec:
  type: LoadBalancer
  ports:
  - port: 443
    targetPort: 5000
  selector:
    app: webhook-server
```

### High Availability

**Health Checks**:
```yaml
# Current implementation
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 5s
```

**Monitoring and Alerts**:
```python
# Future enhancement: Add metrics
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)

@metrics.counter('webhook_requests_total', 'Total webhook requests')
@metrics.histogram('webhook_request_duration_seconds', 'Request duration')
def handle_webhook():
    ...
```

### Error Handling and Retry Logic

**Current Implementation**:
- Basic error logging
- No automatic retries
- Fails fast on errors

**Recommended Enhancements**:
```python
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    retry=tenacity.retry_if_exception_type(requests.exceptions.RequestException)
)
def approve_deployment(...):
    # API call with automatic retry
    response = requests.post(url, ...)
    response.raise_for_status()
```

### Performance Optimization

**Current Performance**:
- Single request: ~200-500ms
- JWT generation: ~50ms
- Token exchange: ~100-200ms
- API call: ~100-200ms

**Optimization Opportunities**:

1. **Token Caching**: Cache installation tokens (saves ~200ms per request)
2. **Connection Pooling**: Reuse HTTP connections
3. **Async Processing**: Use async/await for non-blocking I/O

```python
# Example: Async implementation
from aiohttp import ClientSession
import asyncio

async def approve_deployment_async(...):
    async with ClientSession() as session:
        async with session.post(url, json=data) as response:
            return await response.json()
```

### Disaster Recovery

**Backup and Restore**:
```bash
# Backup private key
tar -czf backup-$(date +%Y%m%d).tar.gz \
    webhook-server/keys/ \
    webhook-server/.env

# Restore
tar -xzf backup-20240101.tar.gz
```

**Failover Strategy**:
1. Deploy to multiple regions
2. Use DNS failover (Route 53, Cloudflare)
3. Implement health-check based routing
4. Maintain standby instances

---

## Future Enhancements

### Planned Improvements

1. **Token Caching**: Cache installation tokens to reduce API calls
2. **Database Integration**: Store deployment history and audit logs
3. **Advanced Decision Logic**: Support complex approval rules
4. **Metrics and Monitoring**: Prometheus/Grafana integration
5. **Rate Limiting**: Protect against abuse
6. **Async Processing**: Improve throughput with async/await
7. **Multi-Environment Support**: Handle multiple environments dynamically
8. **Rollback Capabilities**: Automatic rollback on failures

### Extension Points

The architecture is designed to be extended:

- **Custom Decision Logic**: Modify `handle_webhook()` function
- **External Integrations**: Add calls to external APIs (e.g., ServiceNow, Jira)
- **Notification System**: Send alerts via Slack, email, etc.
- **Audit Logging**: Track all approval decisions
- **Policy Engine**: Implement rule-based decision making

---

## Conclusion

This architecture provides a solid foundation for custom deployment protection rules with:
- ✅ Security through signature verification and token management
- ✅ Scalability through stateless design
- ✅ Reliability through error handling and health checks
- ✅ Extensibility through modular design

For questions or suggestions, please refer to the main [README](../README.md) or open an issue.
