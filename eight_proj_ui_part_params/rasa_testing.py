from flask import Flask, request, jsonify
from rasa.core.agent import Agent
import asyncio
import logging
from rasa.utils.endpoints import EndpointConfig


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

try:
    action_endpoint = EndpointConfig(url="http://localhost:5055/webhook")
    # Load the trained Rasa model
    model_path = "models/20250310-154908-inventive-eaves.tar.gz"
    logger.info(f"Loading model from: {model_path}")
    agent = Agent.load(model_path,action_endpoint=action_endpoint)
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

async def get_response(message):
    logger.info(f"Processing message: {message}")
    try:
        responses = await agent.handle_text(message)
        logger.info(f"Rasa response: {responses}")
        return responses
    except Exception as e:
        logger.error(f"Error getting response: {str(e)}")
        return []

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    logger.info(f"Received message: {user_message}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(get_response(user_message))
    
    # Log the complete raw response for debugging
    logger.info(f"Complete raw response: {response}")
    
    # Return the raw response directly without modification
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(port=5000, debug=True)