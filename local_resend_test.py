import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Backend URL (local)
API_URL = "http://localhost:8001/api"

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

def test_resend_status():
    """Test Resend API status endpoint"""
    try:
        response = requests.get(f"{API_URL}/test/resend-status")
        if response.status_code != 200:
            return log_test_result("Resend API Status", False, f"Failed with status code {response.status_code}: {response.text}")
        
        status_data = response.json()
        if status_data.get("status") != "ok":
            return log_test_result("Resend API Status", False, f"API not working: {status_data.get('message', 'No message')}")
        
        return log_test_result("Resend API Status", True, f"API is working: {status_data.get('message', '')}")
    except Exception as e:
        return log_test_result("Resend API Status", False, f"Exception: {str(e)}")

def test_send_test_email():
    """Test sending a test email"""
    try:
        test_email = "test@example.com"
        response = requests.post(
            f"{API_URL}/test/send-email", 
            json={
                "to_email": test_email,
                "subject": "Test Email",
                "message": "This is a test email from Mystery Box Store."
            }
        )
        
        if response.status_code != 200:
            return log_test_result("Send Test Email", False, f"Failed with status code {response.status_code}: {response.text}")
        
        email_data = response.json()
        if not email_data.get("success", False):
            return log_test_result("Send Test Email", False, f"Email not sent: {email_data.get('error', 'No error message')}")
        
        message_id = email_data.get("email_result", {}).get("message_id")
        if not message_id:
            return log_test_result("Send Test Email", False, "No message ID returned")
        
        return log_test_result("Send Test Email", True, f"Email sent successfully with ID: {message_id}")
    except Exception as e:
        return log_test_result("Send Test Email", False, f"Exception: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting email system tests for Mystery Box Store")
    
    # Test Resend API status
    test_resend_status()
    
    # Test sending a test email
    test_send_test_email()
    
    # Print summary
    logger.info("\n=== EMAIL TESTS SUMMARY ===")
    passed = sum(1 for result in test_results.values() if isinstance(result, dict) and result.get("success"))
    failed = sum(1 for result in test_results.values() if isinstance(result, dict) and not result.get("success"))
    logger.info(f"PASSED: {passed}, FAILED: {failed}")
    
    for test_name, result in test_results.items():
        if isinstance(result, dict) and "success" in result:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
            if result.get("message"):
                logger.info(f"  - {result['message']}")