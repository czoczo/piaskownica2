#!/bin/bash
# Setup GitHub App - Interactive script to guide users through GitHub App creation
# This script provides step-by-step instructions for creating and configuring a GitHub App

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GitHub App Setup for Custom Deployment Protection Rules${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}This script will guide you through creating a GitHub App.${NC}"
echo ""
echo "Prerequisites:"
echo "  ✓ GitHub account with organization or personal repository access"
echo "  ✓ Admin permissions to create GitHub Apps"
echo ""
read -p "Press Enter to continue..."
echo ""

echo -e "${GREEN}Step 1: Navigate to GitHub App Creation${NC}"
echo "---------------------------------------"
echo "Open your browser and go to one of:"
echo "  • For Organization: https://github.com/organizations/YOUR_ORG/settings/apps/new"
echo "  • For Personal: https://github.com/settings/apps/new"
echo ""
read -p "Press Enter when you've opened the page..."
echo ""

echo -e "${GREEN}Step 2: Basic Information${NC}"
echo "-------------------------"
echo "Fill in the following fields:"
echo ""
echo "  GitHub App Name:"
echo "    Example: 'My Deployment Protection Rule'"
echo ""
echo "  Homepage URL:"
echo "    Example: 'https://github.com/YOUR_USERNAME/deployment-protection-demo'"
echo ""
echo "  Description (optional):"
echo "    Example: 'Custom deployment protection rule for auto-approving scheduled deployments'"
echo ""
read -p "Press Enter when done..."
echo ""

echo -e "${GREEN}Step 3: Webhook Configuration${NC}"
echo "------------------------------"
echo "Configure the webhook settings:"
echo ""
echo "  ✓ Check 'Active' under Webhook"
echo ""
echo "  Webhook URL:"
echo "    Enter your webhook endpoint URL"
echo "    Example: https://your-domain.com/webhook"
echo ""
echo "  Webhook Secret:"
echo "    Generate a strong secret:"
read -p "    Generate one now? (y/n): " generate_secret

if [[ $generate_secret == "y" ]]; then
    secret=$(openssl rand -hex 32)
    echo ""
    echo -e "    ${YELLOW}Your webhook secret:${NC}"
    echo -e "    ${GREEN}${secret}${NC}"
    echo ""
    echo "    Copy this secret and paste it into GitHub App settings"
    echo "    Also save it for later - you'll need it in your .env file"
    echo ""
    read -p "    Press Enter after you've copied the secret..."
fi
echo ""

echo -e "${GREEN}Step 4: Repository Permissions${NC}"
echo "-------------------------------"
echo "Scroll down to 'Repository permissions' and set:"
echo ""
echo -e "  ${YELLOW}Actions: Read and write${NC}"
echo "    This is REQUIRED for deployment protection rules"
echo ""
echo -e "  ${YELLOW}Deployments: Read and write${NC}"
echo "    This is REQUIRED for deployment protection rules"
echo ""
echo "  Other permissions: None needed (unless you want additional features)"
echo ""
read -p "Press Enter when you've set the permissions..."
echo ""

echo -e "${GREEN}Step 5: Subscribe to Events${NC}"
echo "---------------------------"
echo "Scroll down to 'Subscribe to events' and check:"
echo ""
echo -e "  ${YELLOW}✓ Deployment protection rule${NC}"
echo "    This is the event that triggers our webhook"
echo ""
read -p "Press Enter when done..."
echo ""

echo -e "${GREEN}Step 6: Where can this GitHub App be installed?${NC}"
echo "------------------------------------------------"
echo "Choose one:"
echo "  • Only on this account (recommended for testing)"
echo "  • Any account (if you want to share the app)"
echo ""
read -p "Press Enter when done..."
echo ""

echo -e "${GREEN}Step 7: Create the GitHub App${NC}"
echo "-----------------------------"
echo "Click the 'Create GitHub App' button at the bottom"
echo ""
read -p "Press Enter after creating the app..."
echo ""

echo -e "${GREEN}Step 8: Generate Private Key${NC}"
echo "----------------------------"
echo "After creation, you'll be on the app's settings page:"
echo ""
echo "  1. Scroll down to 'Private keys'"
echo "  2. Click 'Generate a private key'"
echo "  3. A .pem file will be downloaded"
echo "  4. Move it to: ./webhook-server/keys/private-key.pem"
echo ""
read -p "Have you generated and saved the private key? (y/n): " has_key

if [[ $has_key != "y" ]]; then
    echo -e "${RED}Please generate the private key before continuing!${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}Step 9: Note Your App ID${NC}"
echo "-----------------------"
echo "At the top of the page, find 'App ID' (it's a number)"
echo ""
read -p "Enter your App ID: " app_id
echo ""

echo -e "${GREEN}Step 10: Install the App${NC}"
echo "------------------------"
echo "Now install the app on your repository:"
echo ""
echo "  1. Click 'Install App' in the left sidebar"
echo "  2. Choose the account/organization"
echo "  3. Select 'Only select repositories'"
echo "  4. Choose your demo repository"
echo "  5. Click 'Install'"
echo ""
read -p "Press Enter after installing..."
echo ""

echo -e "${GREEN}Step 11: Configure Repository Environment${NC}"
echo "-----------------------------------------"
echo "Go to your repository:"
echo "  1. Settings → Environments"
echo "  2. Create/Edit 'production' environment"
echo "  3. Add environment secret:"
echo "     Name: EXAMPLE_SEC"
echo "     Value: Your secret value (e.g., 'Hello from production!')"
echo "  4. Under 'Deployment protection rules':"
echo "     - Enable 'Required reviewers' (add yourself)"
echo "     - Enable your custom GitHub App"
echo ""
read -p "Press Enter when environment is configured..."
echo ""

echo -e "${GREEN}Step 12: Create .env File${NC}"
echo "-------------------------"
echo "Creating .env file from template..."
echo ""

if [ -f webhook-server/.env ]; then
    read -p ".env file already exists. Overwrite? (y/n): " overwrite
    if [[ $overwrite != "y" ]]; then
        echo "Keeping existing .env file"
    else
        create_env=true
    fi
else
    create_env=true
fi

if [[ $create_env == true ]]; then
    cp webhook-server/.env.example webhook-server/.env
    
    # Update with App ID
    if [[ ! -z "$app_id" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/your_app_id_here/${app_id}/" webhook-server/.env
        else
            sed -i "s/your_app_id_here/${app_id}/" webhook-server/.env
        fi
    fi
    
    # Update with webhook secret
    if [[ ! -z "$secret" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/your_webhook_secret_here/${secret}/" webhook-server/.env
        else
            sed -i "s/your_webhook_secret_here/${secret}/" webhook-server/.env
        fi
    fi
    
    echo -e "${GREEN}✓ Created webhook-server/.env${NC}"
    echo ""
    echo "Please edit webhook-server/.env and ensure all values are correct"
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review and update webhook-server/.env if needed"
echo "  2. Ensure private key is at: webhook-server/keys/private-key.pem"
echo "  3. Start the webhook server: docker-compose up -d"
echo "  4. Test the workflow: .github/workflows/deploy-with-protection.yml"
echo ""
echo "Testing:"
echo "  • Trigger via schedule: Wait for scheduled run (every 6 hours)"
echo "  • Trigger manually: Go to Actions → Deploy with Protection → Run workflow"
echo ""
echo -e "${YELLOW}Important: Make sure your webhook URL is publicly accessible!${NC}"
echo "  • Use ngrok for local testing: ngrok http 5000"
echo "  • Update the webhook URL in GitHub App settings"
echo ""
echo -e "${GREEN}Happy deploying! 🚀${NC}"
