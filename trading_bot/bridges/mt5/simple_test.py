"""Simple test for MT5 bridge connection"""
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_bridge_connection():
    """Test basic MT5 bridge connection"""
    server_url = "http://localhost:5555"
    
    # Test server status
    try:
        response = requests.get(f"{server_url}/status", timeout=5)
        if response.status_code == 200:
            logger.info(f"Server status: {response.json()}")
            return True
        else:
            logger.error(f"Failed to get server status: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error connecting to server: {e}")
        return False

if __name__ == '__main__':
    if test_bridge_connection():
        logger.info("Bridge connection test successful")
    else:
        logger.error("Bridge connection test failed")
