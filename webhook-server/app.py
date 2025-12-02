"""
GitHub Custom Deployment Protection Rule Webhook Server

This Flask application serves as a webhook endpoint for GitHub's custom
deployment protection rules. It automatically approves deployments triggered
by scheduled events and requires manual review for other triggers.

Features:
- Webhook signature validation
- GitHub App authentication (JWT + Installation tokens)
- Auto-approval logic based on trigger type
- Comprehensive logging
- Health check endpoint

Author: Your Name
License: MIT
"""

import os
import hmac
import hashlib
import json
import time
import logging
from datetime import datetime, timedelta

import jwt
import requests
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration from environment variables
GITHUB_APP_ID = os.environ.get('GITHUB_APP_ID')
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET')
GITHUB_APP_PRIVATE_KEY_PATH = os.environ.get('GITHUB_APP_PRIVATE_KEY_PATH')
PORT = int(os.environ.get('PORT', 5000))

# Validate configuration
if not all([GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, GITHUB_APP_PRIVATE_KEY_PATH]):
    logger.error("Missing required environment variables!")
    logger.error("Required: GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, GITHUB_APP_PRIVATE_KEY_PATH")
    exit(1)

# Load private key
try:
    with open(GITHUB_APP_PRIVATE_KEY_PATH, 'r') as key_file:
        GITHUB_APP_PRIVATE_KEY = key_file.read()
    logger.info(f"Private key loaded successfully from {GITHUB_APP_PRIVATE_KEY_PATH}")
except FileNotFoundError:
    logger.error(f"Private key file not found: {GITHUB_APP_PRIVATE_KEY_PATH}")
    exit(1)


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook payload was sent by GitHub.
    
    Args:
        payload_body: Raw request body as bytes
        signature_header: Value of X-Hub-Signature-256 header
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("No signature header provided")
        return False
    
    # GitHub sends signature as "sha256=<signature>"
    hash_algorithm, signature = signature_header.split('=')
    
    if hash_algorithm != 'sha256':
        logger.warning(f"Unsupported hash algorithm: {hash_algorithm}")
        return False
    
    # Calculate expected signature
    mac = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = mac.hexdigest()
    
    # Compare signatures
    is_valid = hmac.compare_digest(signature, expected_signature)
    
    if not is_valid:
        logger.warning("Invalid webhook signature!")
    
    return is_valid


def generate_jwt() -> str:
    """
    Generate a JSON Web Token (JWT) for GitHub App authentication.
    
    Returns:
        JWT token as string
    """
    # Current time
    now = int(time.time())
    
    # JWT payload
    payload = {
        # Issued at time (60 seconds in the past to allow for clock drift)
        'iat': now - 60,
        # JWT expiration time (10 minutes maximum)
        'exp': now + (10 * 60),
        # GitHub App's identifier
        'iss': GITHUB_APP_ID
    }
    
    # Load private key
    private_key = serialization.load_pem_private_key(
        GITHUB_APP_PRIVATE_KEY.encode(),
        password=None,
        backend=default_backend()
    )
    
    # Create JWT
    token = jwt.encode(payload, private_key, algorithm='RS256')
    
    logger.debug("Generated new JWT token")
    return token


def get_installation_access_token(installation_id: int) -> str:
    """
    Exchange JWT for an installation access token.
    
    Args:
        installation_id: GitHub App installation ID
        
    Returns:
        Installation access token
    """
    jwt_token = generate_jwt()
    
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {jwt_token}',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    logger.info(f"Requesting installation access token for installation {installation_id}")
    
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    
    token_data = response.json()
    logger.info("Successfully obtained installation access token")
    
    return token_data['token']


def approve_deployment(
    owner: str,
    repo: str,
    run_id: int,
    installation_id: int,
    environment_name: str,
    comment: str = None
) -> dict:
    """
    Approve a deployment using the GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run ID
        installation_id: GitHub App installation ID
        environment_name: Environment name
        comment: Optional comment for the approval
        
    Returns:
        API response as dict
    """
    # Get installation access token
    access_token = get_installation_access_token(installation_id)
    
    # API endpoint
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/deployment_protection_rule"
    
    # Request headers
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {access_token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json'
    }
    
    # Request body
    data = {
        'environment_name': environment_name,
        'state': 'approved',
        'comment': comment or f'Auto-approved by custom protection rule at {datetime.utcnow().isoformat()}Z'
    }
    
    logger.info(f"Approving deployment for run {run_id} in environment {environment_name}")
    logger.debug(f"Approval data: {json.dumps(data, indent=2)}")
    
    # Make API request
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 204:
        logger.info("✅ Deployment approved successfully!")
        return {'status': 'approved', 'message': 'Deployment approved'}
    else:
        logger.error(f"Failed to approve deployment: {response.status_code}")
        logger.error(f"Response: {response.text}")
        response.raise_for_status()


def reject_deployment(
    owner: str,
    repo: str,
    run_id: int,
    installation_id: int,
    environment_name: str,
    comment: str = None
) -> dict:
    """
    Reject a deployment (for demonstration purposes).
    
    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run ID
        installation_id: GitHub App installation ID
        environment_name: Environment name
        comment: Optional comment for the rejection
        
    Returns:
        API response as dict
    """
    access_token = get_installation_access_token(installation_id)
    
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/deployment_protection_rule"
    
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {access_token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json'
    }
    
    data = {
        'environment_name': environment_name,
        'state': 'rejected',
        'comment': comment or f'Rejected by custom protection rule at {datetime.utcnow().isoformat()}Z'
    }
    
    logger.info(f"Rejecting deployment for run {run_id} in environment {environment_name}")
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 204:
        logger.info("❌ Deployment rejected")
        return {'status': 'rejected', 'message': 'Deployment rejected'}
    else:
        logger.error(f"Failed to reject deployment: {response.status_code}")
        response.raise_for_status()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'deployment-protection-webhook',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Main webhook endpoint for handling deployment_protection_rule events.
    """
    logger.info("=" * 80)
    logger.info("Received webhook request")
    
    # Get request data
    payload_body = request.data
    signature = request.headers.get('X-Hub-Signature-256')
    event_type = request.headers.get('X-GitHub-Event')
    delivery_id = request.headers.get('X-GitHub-Delivery')
    
    logger.info(f"Event Type: {event_type}")
    logger.info(f"Delivery ID: {delivery_id}")
    
    # Verify webhook signature
    if not verify_webhook_signature(payload_body, signature):
        logger.error("Invalid webhook signature - rejecting request")
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse payload
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Log payload for debugging
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Handle only deployment_protection_rule events
    if event_type != 'deployment_protection_rule':
        logger.info(f"Ignoring event type: {event_type}")
        return jsonify({'message': 'Event type not supported'}), 200
    
    # Extract important information
    action = payload.get('action')
    environment = payload.get('environment')
    event = payload.get('event')  # This tells us what triggered the workflow
    deployment = payload.get('deployment', {})
    repository = payload.get('repository', {})
    installation = payload.get('installation', {})
    
    owner = repository.get('owner', {}).get('login')
    repo = repository.get('name')
    installation_id = installation.get('id')
    
    # Extract workflow run ID from deployment
    workflow_run_id = deployment.get('id')
    
    logger.info(f"Action: {action}")
    logger.info(f"Environment: {environment}")
    logger.info(f"Trigger Event: {event}")
    logger.info(f"Repository: {owner}/{repo}")
    logger.info(f"Workflow Run ID: {workflow_run_id}")
    logger.info(f"Installation ID: {installation_id}")
    
    # Decision logic: Auto-approve scheduled events
    if action == 'requested':
        if event == 'schedule':
            # Auto-approve scheduled deployments
            logger.info("⏰ Scheduled deployment detected - AUTO-APPROVING")
            
            try:
                result = approve_deployment(
                    owner=owner,
                    repo=repo,
                    run_id=workflow_run_id,
                    installation_id=installation_id,
                    environment_name=environment,
                    comment='✅ Auto-approved: Scheduled deployment'
                )
                
                logger.info("Successfully processed auto-approval")
                return jsonify(result), 200
                
            except Exception as e:
                logger.error(f"Error approving deployment: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        else:
            # For other events, we'll just log and let manual review happen
            logger.info(f"👆 Manual trigger detected (event: {event}) - REQUIRES MANUAL REVIEW")
            logger.info("The deployment will wait for a human reviewer to approve it")
            
            # Optionally, you could add custom logic here:
            # - Check if certain conditions are met
            # - Query external systems
            # - Apply business rules
            # - etc.
            
            return jsonify({
                'message': 'Deployment requires manual review',
                'trigger': event
            }), 200
    
    else:
        logger.info(f"Action '{action}' does not require processing")
        return jsonify({'message': 'Action not handled'}), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Starting GitHub Deployment Protection Webhook Server")
    logger.info(f"GitHub App ID: {GITHUB_APP_ID}")
    logger.info(f"Port: {PORT}")
    logger.info("=" * 80)
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=os.environ.get('FLASK_ENV') != 'production'
    )
