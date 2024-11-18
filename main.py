# main.py
import logging
import uuid
import sys
import dotenv
import redis
import os
from flask import Flask
from theoriq import AgentConfig, ExecuteContext, ExecuteResponse
from theoriq.biscuit import TheoriqCost
from theoriq.extra.flask import theoriq_blueprint
from theoriq.schemas import ExecuteRequestBody, TextItemBlock
from theoriq.types import Currency
from voting import VotingSystem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD'),
)

# Initialize VotingSystem
voting_system = VotingSystem(redis_client)
def is_new_session_request(current_state, user_input):
    """
    Checks if the user input indicates the start of a new DAO Voting session.
    """
    start_phrases = [
        "start a new vote",
        "begin dao session",
        "initiate governance",
        "reset voting session"
    ]
    return current_state is None or user_input.lower().strip() in [phrase.lower() for phrase in start_phrases]


def generate_session_token():
    """Generate a unique session token."""
    return str(uuid.uuid4())

def get_session_token(context: ExecuteContext):
    """Get or create a session token for the current user."""
    session_key = f"session:{context.agent_address}"
    session_token = redis_client.get(session_key)
    if not session_token:
        session_token = generate_session_token()
        redis_client.set(session_key, session_token)
    return session_token.decode() if isinstance(session_token, bytes) else session_token


def execute(context: ExecuteContext, req: ExecuteRequestBody) -> ExecuteResponse:
    """Main execution function for Theoriq Agent"""
    logger.info(f"Received request: {context.request_id}")
    
    # Get the input text from request
    last_block = req.last_item.blocks[0]
    input_text = last_block.data.text.strip()
    
    # Get session state
    session_id = get_session_token(context)
    session_state = redis_client.get(f"state:{session_id}")
    wallet_address = voting_system.get_wallet_address(session_id)
    
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Current state: {session_state}")
    logger.info(f"Current wallet: {wallet_address}")
    logger.info(f"Input received: {input_text}")
    
    response_text = ""
    
    # Check if user input indicates a new session
    if is_new_session_request(redis_client.get(f"state:{session_id}"), input_text):
        redis_client.set(f"state:{session_id}", "awaiting_wallet")
        return context.new_response(
            blocks=[
                TextItemBlock(
                    text="=== Welcome to DAO Voting System ===\n\n"
                        "Please enter your wallet address to continue:\n\n"
                        "(Note: It should be a 42-character ID starting with '0x'. Ensure you have it ready to proceed with voting.)"
                ),
            ],
            cost=TheoriqCost(amount=1, currency=Currency.USDC),
        )
    
    # Check if we're awaiting a wallet address
    if session_state == b"awaiting_wallet":
        success, message = voting_system.initialize_user(session_id, input_text)
        if success:
            redis_client.set(f"state:{session_id}", "menu")
            response_text = f"{message} \n\n" + voting_system.get_menu()
        else:
            response_text = message + "\nPlease enter your wallet address:"
        
        return context.new_response(
            blocks=[TextItemBlock(text=response_text)],
            cost=TheoriqCost(amount=1, currency=Currency.USDC),
        )
    
    # Handle menu state
    if wallet_address and (session_state == b"menu" or not session_state):
        choice = input_text.strip()
        
        # Handle exit choice immediately
        if choice == "5":
            redis_client.delete(f"state:{session_id}")
            return context.new_response(
                blocks=[TextItemBlock(text="Thank you for using the DAO Voting System!")],
                cost=TheoriqCost(amount=1, currency=Currency.USDC),
            )
            
        if choice == "1":
            response_text = voting_system.display_proposals(session_id)
            response_text += "\n" + voting_system.get_menu()
        elif choice == "2":
            redis_client.set(f"state:{session_id}", "awaiting_proposal")
            response_text = "Enter proposal ID:"
            return context.new_response(
                blocks=[TextItemBlock(text=response_text)],
                cost=TheoriqCost(amount=1, currency=Currency.USDC),
            )
        elif choice == "3":
            response_text = voting_system.get_all_voting_history(session_id)
            response_text += "\n" + voting_system.get_menu()
        elif choice == "4":
            redis_client.set(f"state:{session_id}", "awaiting_wallet")
            redis_client.delete(f"wallet:{session_id}")
            response_text = "Please enter your new wallet address:"
            return context.new_response(
                blocks=[TextItemBlock(text=response_text)],
                cost=TheoriqCost(amount=1, currency=Currency.USDC),
            )
        else:
            response_text = "Invalid choice. " + voting_system.get_menu()
            
        return context.new_response(
            blocks=[TextItemBlock(text=response_text)],
            cost=TheoriqCost(amount=1, currency=Currency.USDC),
        )
    
    # Handle proposal submission state
    elif session_state == b"awaiting_proposal":
        try:
            proposal_id = int(input_text)
            redis_client.set(f"state:{session_id}", "awaiting_vote")
            redis_client.set(f"proposal:{session_id}", str(proposal_id))
            response_text = "Enter your vote (for/against/abstain):"
        except ValueError:
            redis_client.set(f"state:{session_id}", "menu")
            response_text = "Invalid proposal ID. " + voting_system.get_menu()
        
        return context.new_response(
            blocks=[TextItemBlock(text=response_text)],
            cost=TheoriqCost(amount=1, currency=Currency.USDC),
        )
    
    # Handle vote submission state
    elif session_state == b"awaiting_vote":
        proposal_id = redis_client.get(f"proposal:{session_id}")
        if proposal_id:
            response_text = voting_system.submit_vote(session_id, int(proposal_id), input_text)
            redis_client.set(f"state:{session_id}", "menu")
            redis_client.delete(f"proposal:{session_id}")
            response_text += "\n" + voting_system.get_menu()
        else:
            redis_client.set(f"state:{session_id}", "menu")
            response_text = "Error: No proposal ID found. " + voting_system.get_menu()
        
        return context.new_response(
            blocks=[TextItemBlock(text=response_text)],
            cost=TheoriqCost(amount=1, currency=Currency.USDC),
        )
    
    # Default to menu if state is unknown
    else:
        redis_client.set(f"state:{session_id}", "menu")
        response_text = voting_system.get_menu()
    
    logger.info(f"Final state: {redis_client.get(f'state:{session_id}')}")
    logger.info(f"Response: {response_text}")
    
    return context.new_response(
        blocks=[TextItemBlock(text=response_text)],
        cost=TheoriqCost(amount=1, currency=Currency.USDC),
    )

if __name__ == "__main__":
    app = Flask(__name__)
    
    # Load agent configuration from env
    dotenv.load_dotenv()
    agent_config = AgentConfig.from_env()
    
    # Create and register theoriq blueprint
    blueprint = theoriq_blueprint(agent_config, execute)
    app.register_blueprint(blueprint)
    
    print("Starting Flask server...", flush=True)
    app.run(host="0.0.0.0", port=8000, debug=True)

