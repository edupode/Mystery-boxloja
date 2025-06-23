import requests
import json
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

# For local testing
LOCAL_API_URL = "http://localhost:8001/api"

def test_resend_status():
    """Test the Resend API status endpoint"""
    
    try:
        # Send request to the test endpoint
        response = requests.get(f"{LOCAL_API_URL}/test/resend-status")
        
        # Check response
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"✅ Resend status check successful")
            logger.info(f"Response: {json.dumps(response_data, indent=2)}")
            return response_data
        else:
            logger.error(f"❌ Failed to check Resend status")
            logger.error(f"Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Exception when checking Resend status: {str(e)}")
        return None

if __name__ == "__main__":
    test_resend_status()