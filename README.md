# Custom Deployment Protection Rules - Complete Demo

This repository provides a **complete, working example** of GitHub's Custom Deployment Protection Rules feature. It demonstrates how to:

- Set up a GitHub App as a custom deployment protection rule
- Create workflows that are subject to deployment review
- Auto-approve deployments based on custom logic (e.g., scheduled runs)
- Build a webhook server that handles `deployment_protection_rule` events

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Repository Structure](#repository-structure)
- [Detailed Setup Guide](#detailed-setup-guide)
- [How It Works](#how-it-works)
- [Testing the Demo](#testing-the-demo)
- [Deployment Options](#deployment-options)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## 🎯 Overview

Custom Deployment Protection Rules allow you to integrate third-party systems or custom logic into GitHub's deployment workflow. When a workflow attempts to deploy to a protected environment, GitHub sends a webhook to your custom protection rule app, which can then approve or reject the deployment.

This demo includes:
- A sample workflow that deploys to a `production` environment
- A Python-based webhook server that auto-approves deployments from scheduled events
- Complete Docker setup for easy deployment
- All necessary documentation and helper scripts

## ✨ Features

- **✅ GitHub App Authentication**: Proper JWT and installation token generation
- **✅ Webhook Signature Validation**: Secure webhook payload verification
- **✅ Auto-Approval Logic**: Automatically approve scheduled deployments
- **✅ Manual Review**: Require manual approval for other deployment triggers
- **✅ Docker Support**: Easy deployment with Docker Compose
- **✅ Comprehensive Logging**: Detailed logs for debugging
- **✅ Environment Secrets**: Demonstrates accessing environment-specific secrets

## 📦 Prerequisites

Before you begin, ensure you have:

- A GitHub account (organization recommended for full features)
- Docker and Docker Compose installed (for running the webhook server)
- Python 3.9+ (if running without Docker)
- A publicly accessible URL for the webhook server (you can use ngrok for testing)

## 🚀 Quick Start

### 1. Clone this Repository

```bash
git clone <your-repo-url>
cd piaskownica2
```

### 2. Create a GitHub App

Follow the [Detailed Setup Guide](#detailed-setup-guide) section to create and configure your GitHub App.

### 3. Configure the Webhook Server

```bash
cp webhook-server/.env.example webhook-server/.env
# Edit webhook-server/.env with your GitHub App credentials
```

### 4. Deploy the Webhook Server

```bash
cd webhook-server
docker-compose up -d
```

### 5. Configure Repository Settings

1. Install the GitHub App on your repository
2. Go to repository Settings → Environments → Create `production` environment
3. Add `EXAMPLE_SEC` secret to the environment
4. Enable your custom protection rule for the environment

### 6. Test the Workflow

Trigger the workflow manually or via schedule to see the custom protection rule in action!

## 📁 Repository Structure

```
.
├── README.md                          # This file
├── SETUP.md                           # Detailed setup instructions
├── .github/
│   └── workflows/
│       └── deploy-with-protection.yml # Example workflow with deployment protection
├── webhook-server/                    # Python webhook server
│   ├── app.py                        # Flask application
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile                    # Docker image definition
│   ├── docker-compose.yml            # Docker Compose setup
│   ├── .env.example                  # Environment variables template
│   └── README.md                     # Webhook server documentation
├── scripts/                           # Helper scripts
│   ├── setup-github-app.sh           # Script to help create GitHub App
│   ├── generate-jwt.py               # JWT generation utility
│   └── test-webhook.sh               # Test webhook endpoint
└── docs/                              # Additional documentation
    ├── ARCHITECTURE.md               # System architecture
    ├── API-REFERENCE.md              # API endpoints reference
    └── TROUBLESHOOTING.md            # Common issues and solutions
```

## 📖 Detailed Setup Guide

### Step 1: Create a GitHub App

1. **Navigate to GitHub App Settings**
   - Personal account: Settings → Developer settings → GitHub Apps → New GitHub App
   - Organization: Settings → Developer settings → GitHub Apps → New GitHub App

2. **Configure the GitHub App**
   
   | Setting | Value |
   |---------|-------|
   | GitHub App name | `deployment-protector-demo` (or your choice) |
   | Homepage URL | `https://github.com/<your-username>/<your-repo>` |
   | Webhook URL | `https://<your-server>/webhook` (use ngrok for testing) |
   | Webhook secret | Generate a strong secret and save it |
   | Repository permissions → Actions | **Read-only** |
   | Repository permissions → Deployments | **Read and write** |
   | Subscribe to events | ✅ Deployment protection rule |

3. **Generate a Private Key**
   - After creating the app, scroll down and click "Generate a private key"
   - Download the `.pem` file and keep it secure

4. **Note Your App ID and Client ID**
   - Found on the app's settings page

### Step 2: Install the GitHub App

1. Navigate to your GitHub App's page
2. Click "Install App"
3. Select the repository where you want to use it
4. Grant the requested permissions

### Step 3: Set Up the Webhook Server

1. **Copy Environment Variables**
   ```bash
   cd webhook-server
   cp .env.example .env
   ```

2. **Edit `.env` File**
   ```env
   GITHUB_APP_ID=123456
   GITHUB_APP_PRIVATE_KEY_PATH=/app/private-key.pem
   GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
   FLASK_ENV=production
   PORT=5000
   ```

3. **Copy Your Private Key**
   ```bash
   cp ~/Downloads/your-app.*.private-key.pem webhook-server/private-key.pem
   ```

### Step 4: Deploy the Webhook Server

**Using Docker (Recommended):**
```bash
cd webhook-server
docker-compose up -d
```

**Using Python:**
```bash
cd webhook-server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Step 5: Expose Your Server (For Testing)

If testing locally, use ngrok:
```bash
ngrok http 5000
```

Update your GitHub App's webhook URL with the ngrok URL.

### Step 6: Configure Repository Environment

1. Go to repository Settings → Environments
2. Click "New environment" and name it `production`
3. Under "Environment protection rules":
   - Add required reviewers (optional)
   - Enable "Wait timer" (optional)
   - **Add your custom deployment protection rule**
4. Under "Environment secrets":
   - Add secret `EXAMPLE_SEC` with value `My Super Secret Value!`

### Step 7: Test the Setup

1. **Trigger via Schedule**: Wait for the scheduled run, or:
2. **Trigger via Manual Dispatch**: Go to Actions → Select workflow → Run workflow
3. **Check the Workflow Run**: You should see it waiting for deployment review
4. **Check Webhook Server Logs**: 
   ```bash
   docker-compose logs -f
   ```
5. **Verify Auto-Approval**: Scheduled runs should auto-approve

## 🔧 How It Works

### Architecture Flow

```
┌─────────────────┐
│  GitHub Actions │
│    Workflow     │
└────────┬────────┘
         │
         │ (1) Deployment to 'production' environment
         ▼
┌─────────────────────────────────┐
│   Deployment Protection Rule    │
│   (GitHub waits for approval)   │
└────────┬────────────────────────┘
         │
         │ (2) Sends webhook with deployment_protection_rule event
         ▼
┌──────────────────────────────────┐
│    Your Webhook Server           │
│  ┌─────────────────────────────┐ │
│  │ Validates webhook signature │ │
│  └─────────────┬───────────────┘ │
│                │                  │
│  ┌─────────────▼───────────────┐ │
│  │ Checks trigger event        │ │
│  │ - schedule? → Auto-approve  │ │
│  │ - other? → Require review   │ │
│  └─────────────┬───────────────┘ │
│                │                  │
│  ┌─────────────▼───────────────┐ │
│  │ Generates GitHub App JWT    │ │
│  └─────────────┬───────────────┘ │
│                │                  │
│  ┌─────────────▼───────────────┐ │
│  │ Gets installation token     │ │
│  └─────────────┬───────────────┘ │
│                │                  │
│  ┌─────────────▼───────────────┐ │
│  │ Calls GitHub API to         │ │
│  │ approve/reject deployment   │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
         │
         │ (3) Deployment approved/rejected
         ▼
┌─────────────────┐
│  GitHub Actions │
│ Continues or    │
│ waits for review│
└─────────────────┘
```

### Webhook Payload Example

When a deployment protection rule is triggered, GitHub sends:

```json
{
  "action": "requested",
  "environment": "production",
  "event": "schedule",
  "deployment_callback_url": "https://api.github.com/repos/...",
  "deployment": {
    "url": "https://api.github.com/repos/.../deployments/123",
    "id": 123,
    "sha": "abc123...",
    "ref": "main",
    "task": "deploy",
    "environment": "production",
    "created_at": "2025-12-02T10:00:00Z",
    "updated_at": "2025-12-02T10:00:00Z"
  },
  "repository": {
    "id": 456,
    "name": "piaskownica2",
    "full_name": "czoczo/piaskownica2"
  },
  "installation": {
    "id": 789
  }
}
```

### Authentication Flow

1. **Webhook Validation**: Server validates the `X-Hub-Signature-256` header
2. **JWT Generation**: Creates a JWT signed with the app's private key
3. **Installation Token**: Exchanges JWT for an installation access token
4. **API Call**: Uses the installation token to call the deployment review API

## 🧪 Testing the Demo

### Test 1: Scheduled Deployment (Auto-Approved)

1. Wait for the scheduled run (every 6 hours by default)
2. Or modify the schedule to trigger sooner
3. Watch the workflow run - it should auto-approve

### Test 2: Manual Deployment (Requires Review)

1. Go to Actions → Deploy with Protection → Run workflow
2. The workflow will wait for review
3. Check webhook server logs to see it detected manual trigger
4. Manually approve in GitHub UI

### Test 3: Webhook Endpoint Health

```bash
curl http://localhost:5000/health
# Should return: {"status": "healthy"}
```

### Test 4: Webhook Signature Validation

```bash
./scripts/test-webhook.sh
```

## 🚢 Deployment Options

### Option 1: Docker Compose (Recommended for Testing)

```bash
cd webhook-server
docker-compose up -d
```

### Option 2: Kubernetes

See `webhook-server/k8s/` for Kubernetes manifests.

### Option 3: Cloud Platforms

- **Azure App Service**: Deploy container directly
- **AWS ECS**: Use the provided Dockerfile
- **Google Cloud Run**: Serverless container deployment
- **Heroku**: Use container registry

### Option 4: Serverless

For serverless deployment, see `webhook-server/serverless/` for AWS Lambda/Azure Functions examples.

## 🔍 Troubleshooting

### Webhook Not Receiving Events

1. Check GitHub App webhook URL is correct and accessible
2. Verify webhook secret matches between GitHub App and `.env`
3. Check firewall/network settings
4. Review GitHub App → Advanced → Recent Deliveries

### Authentication Errors

1. Verify `GITHUB_APP_ID` is correct
2. Ensure private key path is correct and file is readable
3. Check installation ID (visible in webhook payload)
4. Regenerate installation token if expired

### Deployment Not Auto-Approving

1. Check webhook server logs: `docker-compose logs -f`
2. Verify the `event` field in the payload
3. Ensure deployment environment matches (`production`)
4. Check GitHub API rate limits

For more issues, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## 📚 References

### Official Documentation

- [Custom Deployment Protection Rules](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/create-custom-protection-rules)
- [GitHub Apps Authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app)
- [Webhook Events and Payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment_protection_rule)
- [Workflow Runs API](https://docs.github.com/en/rest/actions/workflow-runs#review-custom-deployment-protection-rules-for-a-workflow-run)

### Community Resources

- [GitHub Community Discussions](https://github.com/orgs/community/discussions)
- [GitHub Actions Examples](https://github.com/actions)

## 📝 License

MIT License - feel free to use this as a template for your own projects!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Note**: This is a demo project for educational purposes. For production use, implement additional security measures, error handling, and monitoring.
