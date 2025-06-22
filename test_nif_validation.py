import requests
import json
import uuid
import time
import base64
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

# Test data
TEST_USER = {
    "email": f"test_user_{uuid.uuid4()}@example.com",
    "name": "Test User",
    "password": "Test@123"
}

def test_nif_validation():
    """Test NIF validation in profile update"""
    logger.info("Testing NIF validation...")
    
    # Register a new user
    response = requests.post(f"{API_URL}/auth/register", json=TEST_USER)
    if response.status_code != 200:
        logger.error(f"Failed to register user: {response.text}")
        return
    
    auth_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test with invalid NIF
    invalid_nifs = [
        "123456789",  # Invalid check digit
        "12345678",   # Too short
        "1234567890", # Too long
        "ABCDEFGHI",  # Non-numeric
        "PT12345678"  # Invalid with PT prefix
    ]
    
    for nif in invalid_nifs:
        profile_data = {
            "nif": nif
        }
        
        response = requests.put(f"{API_URL}/auth/profile", json=profile_data, headers=headers)
        logger.info(f"NIF: {nif}, Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
    
    # Test with valid NIF
    valid_nifs = [
        "501964843",  # Valid NIF
        "PT501964843" # Valid with PT prefix
    ]
    
    for nif in valid_nifs:
        profile_data = {
            "nif": nif
        }
        
        response = requests.put(f"{API_URL}/auth/profile", json=profile_data, headers=headers)
        logger.info(f"NIF: {nif}, Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
    
    # Get profile to verify
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    if response.status_code == 200:
        profile = response.json()
        logger.info(f"Current NIF in profile: {profile.get('nif')}")

if __name__ == "__main__":
    test_nif_validation()