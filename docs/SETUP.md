# Step-by-Step Setup Guide

This guide walks you through setting up the GitHub Custom Deployment Protection Rule demo from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Repository Setup](#repository-setup)
3. [GitHub App Creation](#github-app-creation)
4. [Environment Configuration](#environment-configuration)
5. [Webhook Server Deployment](#webhook-server-deployment)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **GitHub Account** with permissions to:
  - Create GitHub Apps
  - Create repositories
  - Manage repository settings and environments
  
- **Development Tools**:
  - Git
  - Docker and Docker Compose (for containerized deployment)
  - Python 3.9+ (for local development)
  - curl and jq (for testing)
  
- **Network Access**:
  - Publicly accessible URL for webhook endpoint (see [Webhook URL Options](#webhook-url-options))

---

## Repository Setup

### 1. Create a New Repository

```bash
# Clone this repository or create a new one
git clone <your-repo-url>
cd <your-repo-name>

# Or initialize a new repository
git init
git remote add origin <your-repo-url>
```

### 2. Verify Repository Structure

Your repository should have the following structure:

```
.
├── .github/
│   └── workflows/
│       └── deploy-with-protection.yml
├── webhook-server/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── scripts/
│   ├── setup-github-app.sh
│   ├── generate-jwt.py
│   └── test-webhook.sh
├── docker-compose.yml
├── .gitignore
└── README.md
```

### 3. Push to GitHub

```bash
git add .
git commit -m "Initial setup for deployment protection demo"
git push -u origin main
```

---

## GitHub App Creation

### Option A: Interactive Script (Recommended)

Use the provided setup script for guided creation:

```bash
./scripts/setup-github-app.sh
```

This script will:
- Guide you through each step
- Generate webhook secrets
- Create the `.env` file
- Provide helpful reminders

### Option B: Manual Creation

#### Step 1: Navigate to GitHub App Settings

Go to one of:
- **Organization**: `https://github.com/organizations/YOUR_ORG/settings/apps/new`
- **Personal**: `https://github.com/settings/apps/new`

#### Step 2: Basic Information

Fill in:
- **GitHub App Name**: e.g., "My Deployment Protection Rule"
- **Homepage URL**: Your repository URL
- **Description**: Brief description of the app's purpose

#### Step 3: Webhook Configuration

- ✅ Check **Active** under Webhook
- **Webhook URL**: `https://your-domain.com/webhook` (see [Webhook URL Options](#webhook-url-options))
- **Webhook Secret**: Generate a strong secret:
  ```bash
  openssl rand -hex 32
  ```
  Save this secret - you'll need it later!

#### Step 4: Permissions

Set the following repository permissions:

| Permission | Access Level | Required |
|------------|-------------|----------|
| Actions | Read and write | ✅ Yes |
| Deployments | Read and write | ✅ Yes |

#### Step 5: Subscribe to Events

Check the following events:
- ✅ **Deployment protection rule**

#### Step 6: Installation

- Choose "Only on this account" (recommended for testing)
- Click **Create GitHub App**

#### Step 7: Generate Private Key

After creation:
1. Scroll down to **Private keys**
2. Click **Generate a private key**
3. Save the downloaded `.pem` file

#### Step 8: Note Your App ID

At the top of the settings page, note your **App ID** (a number).

#### Step 9: Install the App

1. Click **Install App** in the left sidebar
2. Choose your account/organization
3. Select **Only select repositories**
4. Choose your demo repository
5. Click **Install**

---

## Environment Configuration

### 1. Set Up Webhook Server Environment

Create `webhook-server/.env` from the template:

```bash
cp webhook-server/.env.example webhook-server/.env
```

Edit `webhook-server/.env`:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456                                    # Your App ID from GitHub
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here         # Secret from webhook setup
GITHUB_APP_PRIVATE_KEY_PATH=/app/keys/private-key.pem  # Path inside container

# Server Configuration
PORT=5000
FLASK_ENV=production
```

### 2. Set Up Private Key

Create the keys directory and move your private key:

```bash
mkdir -p webhook-server/keys
mv ~/Downloads/your-app-name.*.private-key.pem webhook-server/keys/private-key.pem
chmod 600 webhook-server/keys/private-key.pem
```

### 3. Configure Repository Environment

In your GitHub repository:

1. Go to **Settings** → **Environments**
2. Create or edit the **production** environment
3. Add environment secret:
   - **Name**: `EXAMPLE_SEC`
   - **Value**: Any secret value (e.g., "Hello from production!")
4. Under **Deployment protection rules**:
   - Enable **Required reviewers** (add yourself or team members)
   - Enable your custom GitHub App

---

## Webhook Server Deployment

### Option A: Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify health
curl http://localhost:5000/health
```

### Option B: Docker Only

```bash
# Build image
docker build -t deployment-protection-webhook ./webhook-server

# Run container
docker run -d \
  --name deployment-protection-webhook \
  -p 5000:5000 \
  -v $(pwd)/webhook-server/keys:/app/keys:ro \
  --env-file webhook-server/.env \
  deployment-protection-webhook

# Check logs
docker logs -f deployment-protection-webhook
```

### Option C: Local Development

```bash
cd webhook-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Update .env for local paths
# Set: GITHUB_APP_PRIVATE_KEY_PATH=./keys/private-key.pem

# Run server
python app.py
```

---

## Webhook URL Options

Your webhook server needs to be publicly accessible. Here are your options:

### Production Deployments

- **Cloud Platforms**: Deploy to AWS, Azure, GCP, etc.
- **PaaS**: Use Heroku, Railway, Render, etc.
- **Kubernetes**: Deploy with the provided Kubernetes manifests

### Development/Testing

#### ngrok (Easiest for Local Testing)

```bash
# Install ngrok: https://ngrok.com/download

# Start your webhook server
docker-compose up -d

# Create tunnel
ngrok http 5000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update your GitHub App webhook URL to: https://abc123.ngrok.io/webhook
```

#### SSH Tunnel

If you have a server with a public IP:

```bash
ssh -R 5000:localhost:5000 user@your-server.com
```

#### Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:5000
```

---

## Testing

### 1. Test JWT Generation

Verify your credentials are correct:

```bash
# Test JWT generation and API access
python scripts/generate-jwt.py --test

# Should output:
# ✅ JWT Token is VALID!
# GitHub App Information: ...
```

### 2. Test Webhook Endpoint

Send a simulated webhook event:

```bash
# Start your webhook server first
docker-compose up -d

# Test with signature validation
./scripts/test-webhook.sh --secret "your_webhook_secret"

# Or test without signature (server may reject)
./scripts/test-webhook.sh
```

Expected output:
```
✅ Success! Webhook processed successfully
```

### 3. Test GitHub Actions Workflow

#### Manual Trigger (Requires Manual Approval)

1. Go to **Actions** → **Deploy with Protection**
2. Click **Run workflow**
3. Select environment (default: production)
4. Click **Run workflow**
5. The workflow will pause for approval
6. You'll need to manually approve it in the environment page

#### Scheduled Trigger (Auto-Approved)

The workflow is configured to run every 6 hours via cron:
```yaml
schedule:
  - cron: '0 */6 * * *'
```

When triggered by schedule:
- Webhook receives `event: "schedule"`
- Server automatically approves
- Workflow proceeds without manual intervention

#### Testing Schedule Without Waiting

To test the scheduled behavior immediately:

**Option 1**: Temporarily modify the cron schedule:
```yaml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes
```

**Option 2**: Use workflow_dispatch with condition check:
```yaml
# In the workflow file
jobs:
  deploy:
    steps:
      - name: Simulate schedule trigger
        run: echo "Testing auto-approval logic"
```

### 4. Monitor Logs

Watch the webhook server logs:

```bash
# Docker Compose
docker-compose logs -f

# Docker only
docker logs -f deployment-protection-webhook

# Local development
# Logs appear in terminal where you ran `python app.py`
```

Look for:
```
⏰ Scheduled deployment detected - AUTO-APPROVING
✅ Deployment approved successfully!
```

### 5. Verify EXAMPLE_SEC Secret

Check that the workflow can access the environment secret:

1. Go to workflow run in Actions tab
2. Expand the "Display Environment Secret" step
3. Verify the secret value is displayed

---

## Troubleshooting

### Webhook Server Issues

#### Server Not Starting

**Check logs:**
```bash
docker-compose logs webhook-server
```

**Common issues:**
- Missing environment variables
- Private key file not found
- Port already in use

**Solution:**
```bash
# Verify .env file
cat webhook-server/.env

# Verify private key exists
ls -lh webhook-server/keys/private-key.pem

# Check port availability
lsof -i :5000
```

#### Invalid JWT Token

**Error:** `JWT Token is INVALID!`

**Possible causes:**
- Wrong App ID
- Incorrect private key
- Private key doesn't match the App

**Solution:**
```bash
# Test JWT generation
python scripts/generate-jwt.py --test

# Verify App ID in .env matches GitHub App settings
# Re-download private key from GitHub App settings if needed
```

### GitHub Webhook Issues

#### Webhook Not Triggering

**Check webhook deliveries:**
1. Go to GitHub App settings
2. Click **Advanced** → **Recent Deliveries**
3. Check for failed deliveries

**Common issues:**
- Webhook URL not accessible
- Wrong webhook URL
- Firewall blocking requests

**Solution:**
```bash
# Test webhook accessibility from external source
curl https://your-domain.com/webhook

# For ngrok, ensure tunnel is running
ngrok http 5000
```

#### Invalid Signature

**Error:** `Invalid webhook signature`

**Solution:**
- Verify `GITHUB_WEBHOOK_SECRET` in `.env` matches GitHub App settings
- Regenerate webhook secret if needed:
  ```bash
  openssl rand -hex 32
  ```
  Update both GitHub App settings and `.env` file

### Deployment Protection Issues

#### Workflow Not Pausing for Approval

**Possible causes:**
- Custom protection rule not enabled on environment
- GitHub App not installed on repository
- Missing permissions

**Solution:**
1. Go to repository **Settings** → **Environments** → **production**
2. Under **Deployment protection rules**:
   - Ensure your GitHub App is checked
   - Verify "Required reviewers" is also enabled
3. Go to GitHub App settings
4. Verify **Deployments** permission is "Read and write"

#### Auto-Approval Not Working for Scheduled Runs

**Check:**
1. Webhook server logs for `event: "schedule"` detection
2. GitHub App has **Actions** permission (Read and write)
3. Webhook URL is correct and accessible

**Debug:**
```bash
# Check webhook deliveries in GitHub App settings
# Look for deployment_protection_rule events

# Verify server is processing schedules
docker-compose logs | grep "schedule"
```

### Environment Secret Issues

#### EXAMPLE_SEC Not Displaying

**Error:** Secret is empty or shows `***`

**Causes:**
- Secret not created in environment
- Wrong environment name
- Workflow using different environment

**Solution:**
1. Verify environment name in workflow matches configured environment
2. Check secret exists: **Settings** → **Environments** → **production** → **Secrets**
3. Ensure secret name is exactly `EXAMPLE_SEC`

---

## Next Steps

Once everything is working:

1. **Customize Auto-Approval Logic**:
   - Edit `webhook-server/app.py`
   - Add custom conditions for approval
   - Integrate with external systems

2. **Add More Environments**:
   - Create staging, development environments
   - Configure different protection rules
   - Test multi-environment deployments

3. **Enhance Security**:
   - Rotate webhook secrets regularly
   - Monitor webhook deliveries
   - Set up alerting for failed approvals

4. **Scale the Solution**:
   - Deploy to production infrastructure
   - Add redundancy and high availability
   - Implement comprehensive monitoring

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [Custom Deployment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#deployment-protection-rules)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Documentation](https://docs.docker.com/)

---

## Support

If you encounter issues not covered in this guide:

1. Check the [main README](README.md) for additional context
2. Review the [webhook server code](webhook-server/app.py) for implementation details
3. Consult [GitHub's documentation](https://docs.github.com) for platform-specific questions
4. Open an issue in this repository with:
   - Clear description of the problem
   - Steps to reproduce
   - Relevant logs and error messages
   - Environment details (OS, Docker version, etc.)
