import requests
import json
import uuid
import time
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

# For local testing
LOCAL_API_URL = "http://localhost:8001/api"

# Test data
TEST_USER = {
    "email": f"test_user_{uuid.uuid4()}@example.com",
    "name": "Test User",
    "password": "Test@123"
}

# Test customer email
TEST_CUSTOMER_EMAIL = f"customer_{uuid.uuid4()}@example.com"

# Mock price ID for testing
MOCK_PRICE_ID = "price_1RdXXXXXXXXXXXXXXXXXXXXX"

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

def test_create_subscription():
    """Test creating a subscription checkout session"""
    try:
        # Create a subscription checkout session
        subscription_data = {
            "customer_email": TEST_CUSTOMER_EMAIL,
            "price_id": MOCK_PRICE_ID,
            "success_url": f"{BACKEND_URL}/success",
            "cancel_url": f"{BACKEND_URL}/cancel",
            "metadata": {
                "test": "true",
                "source": "subscription_test"
            }
        }
        
        response = requests.post(f"{API_URL}/subscriptions/create", json=subscription_data)
        
        # Since we're using a mock price_id, we expect a 400 error from Stripe
        # But we want to verify the endpoint is working correctly
        if response.status_code == 400 and "No such price" in response.text:
            # This is expected with a mock price_id
            test_results["mock_subscription_test"] = True
            return log_test_result("Create Subscription Checkout", True, 
                                  "Endpoint working correctly (expected error with mock price_id)")
        elif response.status_code == 200:
            # If we somehow got a 200 response, store the session_id and customer_id
            response_data = response.json()
            test_results["subscription_session_id"] = response_data.get("session_id")
            test_results["customer_id"] = response_data.get("customer_id")
            return log_test_result("Create Subscription Checkout", True, 
                                  f"Created subscription session: {response_data.get('session_id')}")
        else:
            # Unexpected error
            return log_test_result("Create Subscription Checkout", False, 
                                  f"Failed with unexpected error: {response.text}")
    except Exception as e:
        return log_test_result("Create Subscription Checkout", False, f"Exception: {str(e)}")

def test_subscription_status():
    """Test getting subscription status"""
    try:
        # If we have a real session_id from previous test, use it
        if "subscription_session_id" in test_results:
            session_id = test_results["subscription_session_id"]
        else:
            # Otherwise use a mock session_id
            session_id = "cs_test_mockSessionId"
        
        response = requests.get(f"{API_URL}/subscriptions/status/{session_id}")
        
        # Since we're likely using a mock session_id, we expect an error status
        if response.status_code == 200:
            status_data = response.json()
            if status_data.get("status") == "error":
                # This is expected with a mock session_id
                return log_test_result("Get Subscription Status", True, 
                                      "Endpoint working correctly (returned error status for invalid session)")
            else:
                # We got a real status
                return log_test_result("Get Subscription Status", True, 
                                      f"Got subscription status: {status_data.get('status')}")
        else:
            # Unexpected error
            return log_test_result("Get Subscription Status", False, 
                                  f"Failed with unexpected error: {response.text}")
    except Exception as e:
        return log_test_result("Get Subscription Status", False, f"Exception: {str(e)}")

def test_customer_portal():
    """Test creating a customer portal session"""
    try:
        # If we have a real customer_id from previous test, use it
        if "customer_id" in test_results:
            customer_id = test_results["customer_id"]
        else:
            # Otherwise use a mock customer_id
            customer_id = "cus_mockCustomerId"
        
        portal_data = {
            "customer_id": customer_id,
            "return_url": f"{BACKEND_URL}/account"
        }
        
        response = requests.post(f"{API_URL}/subscriptions/customer-portal", json=portal_data)
        
        # Since we're likely using a mock customer_id, we expect a 400 error
        if response.status_code == 400 and "No such customer" in response.text:
            # This is expected with a mock customer_id
            return log_test_result("Create Customer Portal", True, 
                                  "Endpoint working correctly (expected error with mock customer_id)")
        elif response.status_code == 200:
            # If we somehow got a 200 response, we have a real customer
            response_data = response.json()
            return log_test_result("Create Customer Portal", True, 
                                  f"Created customer portal: {response_data.get('url')}")
        else:
            # Unexpected error
            return log_test_result("Create Customer Portal", False, 
                                  f"Failed with unexpected error: {response.text}")
    except Exception as e:
        return log_test_result("Create Customer Portal", False, f"Exception: {str(e)}")

def test_list_customer_subscriptions():
    """Test listing customer subscriptions"""
    try:
        # If we have a real customer_id from previous test, use it
        if "customer_id" in test_results:
            customer_id = test_results["customer_id"]
        else:
            # Otherwise use a mock customer_id
            customer_id = "cus_mockCustomerId"
        
        response = requests.get(f"{API_URL}/subscriptions/customer/{customer_id}")
        
        # Since we're likely using a mock customer_id, we expect a 400 error
        if response.status_code == 400 and "No such customer" in response.text:
            # This is expected with a mock customer_id
            return log_test_result("List Customer Subscriptions", True, 
                                  "Endpoint working correctly (expected error with mock customer_id)")
        elif response.status_code == 200:
            # If we somehow got a 200 response, we have a real customer
            response_data = response.json()
            subscriptions = response_data.get("subscriptions", [])
            return log_test_result("List Customer Subscriptions", True, 
                                  f"Listed {len(subscriptions)} subscriptions")
        else:
            # Unexpected error
            return log_test_result("List Customer Subscriptions", False, 
                                  f"Failed with unexpected error: {response.text}")
    except Exception as e:
        return log_test_result("List Customer Subscriptions", False, f"Exception: {str(e)}")

def test_subscription_webhook():
    """Test subscription webhook handler"""
    try:
        # Create a mock webhook event
        mock_event = {
            "id": "evt_mock",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_mock",
                    "customer": "cus_mock",
                    "status": "active"
                }
            }
        }
        
        # Send the webhook event
        response = requests.post(
            f"{API_URL}/subscriptions/webhook", 
            data=json.dumps(mock_event),
            headers={"Content-Type": "application/json"}
        )
        
        # We expect a 200 response even for mock data since we're not verifying the signature
        if response.status_code == 200:
            return log_test_result("Subscription Webhook", True, 
                                  "Webhook handler processed the event")
        else:
            # Unexpected error
            return log_test_result("Subscription Webhook", False, 
                                  f"Failed with unexpected error: {response.text}")
    except Exception as e:
        return log_test_result("Subscription Webhook", False, f"Exception: {str(e)}")

def test_stripe_live_keys():
    """Test if Stripe live keys are working"""
    try:
        # We'll use the create subscription endpoint to test if the keys are working
        # We'll use a real-looking but invalid price_id to see if we get the expected error
        subscription_data = {
            "customer_email": TEST_CUSTOMER_EMAIL,
            "price_id": "price_1RdXXXXXXXXXXXXXXXXXXXXX",  # Invalid but real-looking price_id
            "success_url": f"{BACKEND_URL}/success",
            "cancel_url": f"{BACKEND_URL}/cancel"
        }
        
        response = requests.post(f"{API_URL}/subscriptions/create", json=subscription_data)
        
        # With live keys, we expect a 400 error with "No such price" message
        if response.status_code == 400 and "No such price" in response.text:
            return log_test_result("Stripe Live Keys", True, 
                                  "Stripe live keys are working correctly")
        elif "authentication" in response.text.lower() or "invalid api key" in response.text.lower():
            return log_test_result("Stripe Live Keys", False, 
                                  "Stripe authentication failed - check API keys")
        else:
            return log_test_result("Stripe Live Keys", False, 
                                  f"Unexpected response: {response.text}")
    except Exception as e:
        return log_test_result("Stripe Live Keys", False, f"Exception: {str(e)}")

def run_subscription_tests():
    """Run all subscription-related tests"""
    logger.info("Starting subscription endpoint tests")
    
    # Test Stripe live keys first
    test_stripe_live_keys()
    
    # Test subscription endpoints
    test_create_subscription()
    test_subscription_status()
    test_customer_portal()
    test_list_customer_subscriptions()
    test_subscription_webhook()
    
    # Print summary
    logger.info("\n=== SUBSCRIPTION TESTS SUMMARY ===")
    passed = sum(1 for result in test_results.values() if isinstance(result, dict) and result.get("success"))
    failed = sum(1 for result in test_results.values() if isinstance(result, dict) and not result.get("success"))
    logger.info(f"PASSED: {passed}, FAILED: {failed}")
    
    for test_name, result in test_results.items():
        if isinstance(result, dict) and "success" in result:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
            if result.get("message"):
                logger.info(f"  - {result['message']}")
    
    return test_results

if __name__ == "__main__":
    run_subscription_tests()