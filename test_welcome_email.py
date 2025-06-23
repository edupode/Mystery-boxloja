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

def login_admin():
    """Login as admin to get access token"""
    admin_credentials = {
        "email": "eduardocorreia3344@gmail.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{LOCAL_API_URL}/auth/login", json=admin_credentials)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            logger.error(f"Failed to login as admin: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during admin login: {str(e)}")
        return None

def test_welcome_email():
    """Test the welcome email endpoint"""
    
    # Test emails to send to
    test_emails = [
        "eduardocorreia3344@gmail.com",
        "pegojulia28@gmail.com"
    ]
    
    # Login as admin
    access_token = login_admin()
    if not access_token:
        logger.error("Cannot proceed without admin access token")
        return []
    
    # Set up headers with authorization
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    results = []
    
    for email in test_emails:
        logger.info(f"Testing welcome email sending to: {email}")
        
        # Prepare request data
        request_data = {
            "user_email": email,
            "user_name": "Test User"
        }
        
        try:
            # Send request to the test endpoint
            response = requests.post(
                f"{LOCAL_API_URL}/admin/emails/test-welcome", 
                json=request_data,
                headers=headers
            )
            
            # Check response
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"✅ Welcome email sent successfully to {email}")
                logger.info(f"Response: {json.dumps(response_data, indent=2)}")
                results.append({
                    "email": email,
                    "success": True,
                    "response": response_data
                })
            else:
                logger.error(f"❌ Failed to send welcome email to {email}")
                logger.error(f"Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                results.append({
                    "email": email,
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                })
        except Exception as e:
            logger.error(f"❌ Exception when sending welcome email to {email}: {str(e)}")
            results.append({
                "email": email,
                "success": False,
                "error": str(e)
            })
    
    # Print summary
    logger.info("\n=== EMAIL TEST SUMMARY ===")
    success_count = sum(1 for result in results if result["success"])
    logger.info(f"Total tests: {len(results)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {len(results) - success_count}")
    
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        logger.info(f"{status}: Email to {result['email']}")
    
    return results

if __name__ == "__main__":
    test_welcome_email()