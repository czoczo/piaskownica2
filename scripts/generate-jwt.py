#!/usr/bin/env python3
"""
Generate and test JWT tokens for GitHub App authentication.

This script helps verify that your GitHub App credentials are correctly
configured by generating a JWT token and optionally testing it against
the GitHub API.

Usage:
    python generate-jwt.py [--test] [--app-id APP_ID] [--key-path KEY_PATH]
"""

import argparse
import time
import sys
import os
from datetime import datetime, timedelta

try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import requests
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Install with: pip install PyJWT[crypto] cryptography requests")
    sys.exit(1)


def load_private_key(key_path):
    """Load private key from file."""
    try:
        with open(key_path, 'r') as key_file:
            private_key_pem = key_file.read()
        
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        return private_key
    except FileNotFoundError:
        print(f"Error: Private key file not found: {key_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading private key: {e}")
        sys.exit(1)


def generate_jwt_token(app_id, private_key):
    """Generate a JWT token for GitHub App authentication."""
    now = int(time.time())
    
    payload = {
        'iat': now - 60,  # Issued at (60 seconds in the past)
        'exp': now + (10 * 60),  # Expires (10 minutes)
        'iss': str(app_id)  # GitHub App ID
    }
    
    token = jwt.encode(payload, private_key, algorithm='RS256')
    
    return token


def test_jwt_token(token):
    """Test the JWT token by calling the GitHub API."""
    print("\n" + "=" * 60)
    print("Testing JWT token against GitHub API...")
    print("=" * 60)
    
    url = "https://api.github.com/app"
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            app_info = response.json()
            print("\n✅ JWT Token is VALID!")
            print("\nGitHub App Information:")
            print(f"  Name: {app_info.get('name')}")
            print(f"  ID: {app_info.get('id')}")
            print(f"  Owner: {app_info.get('owner', {}).get('login')}")
            print(f"  Created: {app_info.get('created_at')}")
            print(f"  Updated: {app_info.get('updated_at')}")
            
            # Show permissions
            permissions = app_info.get('permissions', {})
            if permissions:
                print("\n  Permissions:")
                for perm, level in permissions.items():
                    print(f"    - {perm}: {level}")
            
            # Show events
            events = app_info.get('events', [])
            if events:
                print("\n  Subscribed Events:")
                for event in events:
                    print(f"    - {event}")
            
            return True
        elif response.status_code == 401:
            print("\n❌ JWT Token is INVALID!")
            print(f"\nError: {response.json().get('message')}")
            print("\nPossible issues:")
            print("  - Incorrect App ID")
            print("  - Wrong private key")
            print("  - Token expired (shouldn't happen with fresh generation)")
            return False
        else:
            print(f"\n⚠️  Unexpected response: {response.status_code}")
            print(f"Message: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network error: {e}")
        return False


def decode_jwt_token(token):
    """Decode and display JWT token contents (without verification)."""
    print("\n" + "=" * 60)
    print("JWT Token Details (decoded without verification):")
    print("=" * 60)
    
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print(f"\nIssuer (iss): {decoded.get('iss')}")
        
        iat = decoded.get('iat')
        if iat:
            iat_dt = datetime.fromtimestamp(iat)
            print(f"Issued At (iat): {iat} ({iat_dt.isoformat()})")
        
        exp = decoded.get('exp')
        if exp:
            exp_dt = datetime.fromtimestamp(exp)
            now = datetime.now()
            remaining = exp_dt - now
            print(f"Expires At (exp): {exp} ({exp_dt.isoformat()})")
            print(f"Time Remaining: {remaining.total_seconds():.0f} seconds")
            
    except Exception as e:
        print(f"Error decoding token: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate and test JWT tokens for GitHub App authentication'
    )
    parser.add_argument(
        '--app-id',
        type=str,
        default=os.environ.get('GITHUB_APP_ID'),
        help='GitHub App ID (default: from GITHUB_APP_ID env var)'
    )
    parser.add_argument(
        '--key-path',
        type=str,
        default=os.environ.get('GITHUB_APP_PRIVATE_KEY_PATH', 'webhook-server/keys/private-key.pem'),
        help='Path to private key file (default: webhook-server/keys/private-key.pem)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test the generated token against GitHub API'
    )
    parser.add_argument(
        '--decode',
        action='store_true',
        help='Decode and display token contents'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.app_id:
        print("Error: App ID is required")
        print("Provide via --app-id or GITHUB_APP_ID environment variable")
        sys.exit(1)
    
    print("=" * 60)
    print("GitHub App JWT Token Generator")
    print("=" * 60)
    print(f"\nApp ID: {args.app_id}")
    print(f"Key Path: {args.key_path}")
    
    # Load private key
    print("\nLoading private key...")
    private_key = load_private_key(args.key_path)
    print("✓ Private key loaded successfully")
    
    # Generate JWT
    print("\nGenerating JWT token...")
    token = generate_jwt_token(args.app_id, private_key)
    print("✓ JWT token generated successfully")
    
    # Display token
    print("\n" + "=" * 60)
    print("Generated JWT Token:")
    print("=" * 60)
    print(f"\n{token}\n")
    
    # Decode if requested
    if args.decode:
        decode_jwt_token(token)
    
    # Test if requested
    if args.test:
        success = test_jwt_token(token)
        sys.exit(0 if success else 1)
    else:
        print("\nTo test this token, run with --test flag")
        print("Example: python generate-jwt.py --test")


if __name__ == '__main__':
    main()
