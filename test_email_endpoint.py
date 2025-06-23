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
API_URL = f"{BACKEND_URL}"  # No need to add /api since it's already in the router prefix

# For local testing
LOCAL_API_URL = "http://localhost:8001"  # No need to add /api since it's already in the router prefix

def test_send_email(use_local=True):
    """Test the email test endpoint with both email addresses"""
    
    # Test emails to send to
    test_emails = [
        "eduardocorreia3344@gmail.com",
        "pegojulia28@gmail.com"
    ]
    
    results = []
    
    # Choose API URL based on whether we're testing locally or remotely
    url_base = LOCAL_API_URL if use_local else API_URL
    logger.info(f"Using API URL: {url_base}")
    
    for email in test_emails:
        logger.info(f"Testing email sending to: {email}")
        
        # Prepare request data
        request_data = {
            "to_email": email,
            "subject": "Teste de Email - Mystery Box Store Funcionando!",
            "message": "Este é um teste do sistema de emails através do Resend. Se você recebeu este email, tudo está funcionando perfeitamente! 🎉"
        }
        
        try:
            # Send request to the test endpoint
            response = requests.post(f"{url_base}/api/test/send-email", json=request_data)
            
            # Check response
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"✅ Email sent successfully to {email}")
                logger.info(f"Response: {json.dumps(response_data, indent=2)}")
                results.append({
                    "email": email,
                    "success": True,
                    "response": response_data
                })
            else:
                logger.error(f"❌ Failed to send email to {email}")
                logger.error(f"Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                results.append({
                    "email": email,
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                })
        except Exception as e:
            logger.error(f"❌ Exception when sending email to {email}: {str(e)}")
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
    # Test using local API
    test_send_email(use_local=True)