#!/bin/bash
# Test webhook endpoint - Send a simulated deployment_protection_rule event
# This helps verify that the webhook server is running and can process events

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5000/webhook}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            WEBHOOK_URL="$2"
            shift 2
            ;;
        --secret)
            WEBHOOK_SECRET="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--url URL] [--secret SECRET]"
            echo ""
            echo "Options:"
            echo "  --url URL       Webhook URL (default: http://localhost:5000/webhook)"
            echo "  --secret SECRET Webhook secret for signature generation"
            echo "  --help          Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  WEBHOOK_URL     Alternative to --url"
            echo "  WEBHOOK_SECRET  Alternative to --secret"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Webhook Endpoint Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if server is running
echo -e "${YELLOW}Checking if webhook server is running...${NC}"
if curl -s -f "${WEBHOOK_URL%/webhook}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is running!${NC}"
    echo ""
    health_response=$(curl -s "${WEBHOOK_URL%/webhook}/health")
    echo "Health check response:"
    echo "$health_response" | jq . 2>/dev/null || echo "$health_response"
    echo ""
else
    echo -e "${RED}✗ Server is not responding${NC}"
    echo "Make sure the webhook server is running:"
    echo "  docker-compose up -d"
    echo "  or"
    echo "  cd webhook-server && python app.py"
    exit 1
fi

# Sample payload - deployment_protection_rule event with schedule trigger
PAYLOAD=$(cat <<EOF
{
  "action": "requested",
  "environment": "production",
  "event": "schedule",
  "deployment_callback_url": "https://api.github.com/repos/test-owner/test-repo/actions/runs/12345/deployment_protection_rule",
  "deployment": {
    "id": 12345,
    "node_id": "DE_kwDOABCDEFGHI",
    "task": "deploy",
    "environment": "production",
    "description": "Test deployment"
  },
  "repository": {
    "id": 123456789,
    "name": "test-repo",
    "full_name": "test-owner/test-repo",
    "owner": {
      "login": "test-owner",
      "id": 111111
    },
    "private": false
  },
  "installation": {
    "id": 99999,
    "node_id": "MDIzOkludGVncmF0aW9uSW5zdGFsbGF0aW9uOTk5OTk="
  },
  "sender": {
    "login": "github-actions[bot]",
    "id": 41898282,
    "type": "Bot"
  }
}
EOF
)

echo -e "${YELLOW}Sending test webhook event...${NC}"
echo ""
echo "Webhook URL: $WEBHOOK_URL"
echo "Event Type: deployment_protection_rule"
echo "Trigger: schedule (should auto-approve)"
echo ""

# Generate signature if secret is provided
if [ -n "$WEBHOOK_SECRET" ]; then
    echo -e "${BLUE}Generating HMAC signature...${NC}"
    SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')
    echo -e "${GREEN}✓ Signature generated${NC}"
    echo ""
    
    SIGNATURE_HEADER="-H X-Hub-Signature-256:sha256=$SIGNATURE"
else
    echo -e "${YELLOW}⚠ No webhook secret provided${NC}"
    echo "Request will be sent without signature validation"
    echo "The server may reject it if signature validation is required"
    echo ""
    SIGNATURE_HEADER=""
fi

# Send request
echo -e "${BLUE}Sending POST request...${NC}"
echo ""

response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-GitHub-Event: deployment_protection_rule" \
    -H "X-GitHub-Delivery: $(uuidgen 2>/dev/null || echo 'test-delivery-id')" \
    $SIGNATURE_HEADER \
    -d "$PAYLOAD" \
    "$WEBHOOK_URL")

http_code=$(echo "$response" | tail -n 1)
response_body=$(echo "$response" | sed '$d')

echo "Response:"
echo "----------"
echo "HTTP Status: $http_code"
echo ""

if [ -n "$response_body" ]; then
    echo "Body:"
    echo "$response_body" | jq . 2>/dev/null || echo "$response_body"
fi

echo ""

# Check result
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Success! Webhook processed successfully${NC}"
    exit 0
elif [ "$http_code" = "401" ]; then
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "The webhook signature was invalid or missing"
    echo "Make sure to provide --secret with the correct webhook secret"
    exit 1
else
    echo -e "${RED}❌ Request failed with status $http_code${NC}"
    exit 1
fi
