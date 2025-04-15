"""Simple Flask server to bridge between Python trading bot and MT5"""
from flask import Flask, request, jsonify
import logging
import threading
import queue
import time

# Set up logging
logging.basicConfig(level=logging.INFO,
                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Request and result queues
request_queue = queue.Queue()
result_queue = queue.Queue()
last_result = None

@app.route('/check_requests', methods=['GET'])
def check_requests():
    """Endpoint for MT5 to check for pending requests"""
    if request_queue.empty():
        return "NO_REQUESTS"
    else:
        request = request_queue.get()
        logger.info(f"Sending request to MT5: {request}")
        return request

@app.route('/submit_result', methods=['POST'])
def submit_result():
    """Endpoint for MT5 to submit results"""
    global last_result
    result = request.form.get('result', '')
    logger.info(f"Received result from MT5: {result[:100]}...")  # Log first 100 chars
    
    # Store the result
    last_result = result
    result_queue.put(result)
    
    return "OK"

@app.route('/status', methods=['GET'])
def status():
    """Endpoint to check server status"""
    return jsonify({
        "status": "running",
        "pending_requests": request_queue.qsize(),
        "pending_results": result_queue.qsize(),
        "last_result": last_result[:100] + "..." if last_result and len(last_result) > 100 else last_result
    })

@app.route('/send_request', methods=['POST'])
def api_send_request():
    """API endpoint to send a request to MT5"""
    request_data = request.json
    if not request_data or 'request' not in request_data:
        return jsonify({"error": "Invalid request format"}), 400
    
    request_str = request_data['request']
    result = send_request(request_str)
    
    if result is None:
        return jsonify({"error": "Request timed out"}), 408
    
    return jsonify({"result": result})

def send_request(request_str, timeout=30):
    """
    Send a request to MT5 and wait for the result
    
    Args:
        request_str (str): Request string to send to MT5
        timeout (int): Timeout in seconds
        
    Returns:
        str: Result from MT5 or None if timeout
    """
    # Clear any previous results
    while not result_queue.empty():
        result_queue.get()
    
    # Send the request
    request_queue.put(request_str)
    
    # Wait for the result
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not result_queue.empty():
            return result_queue.get()
        time.sleep(0.1)
    
    return None

# Change the port from 5000 to 5555
def run_server():
    """Run the Flask server"""
    app.run(host='0.0.0.0', port=5555)


if __name__ == '__main__':
    # Start the server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    logger.info("MT5 Bridge Server started. Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Server shutting down...")

