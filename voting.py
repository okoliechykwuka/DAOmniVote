import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from proposal_analysis import ProposalAnalyzer
from blockchain import GovernorBravoContract, ProposalState
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VotingSystem:
    def __init__(self, redis_client):
        # Load environment variables
        load_dotenv()
        
        # Redis client for session management
        self.redis_client = redis_client
        
        # Initialize the blockchain contract
        self.governor_contract = GovernorBravoContract(
            web3_provider_uri=os.getenv("INFURA_URL"),
            abi_path="contract/compiled/contract_abi.json",
            contract_address=os.getenv("CONTRACT_ADDRESS")
        )
        
    
    def get_wallet_address(self, session_id: str) -> Optional[str]:
        """Get wallet address from Redis session"""
        wallet = self.redis_client.get(f"wallet:{session_id}")
        return wallet.decode('utf-8') if wallet else None


    def set_wallet_address(self, session_id: str, wallet_address: str) -> bool:
        """Set wallet address in Redis session"""
        try:
            self.redis_client.set(f"wallet:{session_id}", wallet_address)
            # Initialize vote counts for new users
            if not self.redis_client.exists(f"votes:{wallet_address}"):
                self.redis_client.hmset(f"votes:{wallet_address}", {
                    'for': 0,
                    'against': 0,
                    'abstain': 0
                })
            return True
        except Exception as e:
            logger.error(f"Error setting wallet address: {str(e)}")
            return False

    def initialize_user(self, session_id: str, wallet_address: str) -> Tuple[bool, str]:
        """Initialize system with user's wallet address"""
        try:
            if not wallet_address.startswith('0x') or len(wallet_address) != 42:
                logger.error(f"Invalid wallet address format: {wallet_address}")
                return False, "Invalid wallet address format. Please provide a valid Ethereum address."
            
            if self.set_wallet_address(session_id, wallet_address):
                return True, f"Successfully initialized wallet: {wallet_address}"
            return False, "Failed to initialize wallet address."
            
        except Exception as e:
            logger.error(f"Error initializing user: {str(e)}")
            return False, f"Error initializing user: {str(e)}"

    def display_proposals(self, session_id: str) -> str:
        """Display analyzed proposals and their current status"""
        try:
            wallet_address = self.get_wallet_address(session_id)
            if not wallet_address:
                return "No user initialized. Please set wallet address first."
                
            output = []
            output.append("=== Current Proposal Analysis ===")
            
            # Initialize proposal analyzer
            proposal_analyzer = ProposalAnalyzer()
            analysis = proposal_analyzer.analyze_proposals()
            output.append(analysis)
            
            # Get proposal count
            proposal_count = self.governor_contract.get_proposal_count()
            latest_proposals = range(max(1, proposal_count - 10), proposal_count + 1)
            output.append("\n=== Available Proposals ID for Voting ===\n")
            output.append(str(list(latest_proposals)))
            
            # Get user's voting statistics - decode bytes to string
            user_stats = self.redis_client.hgetall(f"votes:{wallet_address}")
            output.append("\nCurrent Voting Statistics:\n")
            output.append(f"Total 'For' votes: {user_stats.get(b'for', b'0').decode('utf-8')}\n")
            output.append(f"Total 'Against' votes: {user_stats.get(b'against', b'0').decode('utf-8')}\n")
            output.append(f"Total 'Abstain' votes: {user_stats.get(b'abstain', b'0').decode('utf-8')}\n")
            
            return "\n".join(output)
                
        except Exception as e:
            logger.error(f"Error displaying proposals: {str(e)}")
            return f"Error displaying proposals: {str(e)}"

    def submit_vote(self, session_id: str, proposal_id: int, vote: str) -> str:
        """Submit a vote for a specific proposal"""
        try:
            wallet_address = self.get_wallet_address(session_id)
            if not wallet_address:
                return "No user initialized. Please set wallet address first."
            
            vote = vote.lower()
            if vote not in ['for', 'against', 'abstain']:
                return f"Invalid vote option: {vote}"
            
            # Check if proposal exists and is Executed
            proposal_details = self.governor_contract.get_proposal_details(proposal_id)
            if not proposal_details:
                return f"Proposal {proposal_id} not found"
            
            if proposal_details['state'] != ProposalState.Executed.name:
                return f"Proposal {proposal_id} is not Executed"
            
            # Create vote data dictionary
            vote_data = {
                'vote': vote,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'proposal_state': proposal_details['state']
            }
            
            # Store vote data as a string representation
            vote_key = f"proposal:{proposal_id}:votes"
            self.redis_client.hset(vote_key, wallet_address, str(vote_data))
            self.redis_client.hincrby(f"votes:{wallet_address}", vote, 1)
            
            log_message = f"Vote recorded - Proposal: {proposal_id}, Wallet: {wallet_address}, Vote: {vote}"
            logger.info(log_message)
            
            return f"Vote successfully recorded!\n\n{log_message}"
                
        except Exception as e:
            logger.error(f"Error submitting vote: {str(e)}")
            return f"Error submitting vote: {str(e)}"

    def get_all_voting_history(self, session_id: str) -> str:
        """Get complete voting history for current user"""
        try:
            wallet_address = self.get_wallet_address(session_id)
            if not wallet_address:
                return "No user initialized. Please set wallet address first."

            output = ["\n=== Your Voting History ==="]
            
            # Get current vote counts
            user_stats = self.redis_client.hgetall(f"votes:{wallet_address}")
            vote_counts = {
                'for': user_stats.get(b'for', b'0').decode('utf-8'),
                'against': user_stats.get(b'against', b'0').decode('utf-8'),
                'abstain': user_stats.get(b'abstain', b'0').decode('utf-8')
            }
            
            # Get all proposals
            proposal_count = self.governor_contract.get_proposal_count()
            for proposal_id in range(1, proposal_count + 1):
                vote_key = f"proposal:{proposal_id}:votes"
                vote_data = self.redis_client.hget(vote_key, wallet_address)
                
                if vote_data:
                    try:
                        # Handle both old and new vote data formats
                        vote_info = vote_data.decode('utf-8')
                        if vote_info.startswith('{'):
                            # New format with timestamp
                            import ast
                            vote_info = ast.literal_eval(vote_info)
                            vote = vote_info['vote']
                            timestamp = vote_info['timestamp']
                        else:
                            # Old format with just vote
                            vote = vote_info
                            timestamp = "Not recorded"
                        
                        proposal_details = self.governor_contract.get_proposal_details(proposal_id)
                        
                        output.append(f"\nProposal ID: {proposal_id}")
                        output.append(f"Vote: {vote}")
                        output.append(f"Timestamp: {timestamp}")
                        output.append(f"Proposal State: {proposal_details['state'] if proposal_details else 'Unknown'}")
                        output.append("Current Vote Counts:")
                        output.append(f"- For: {vote_counts['for']}")
                        output.append(f"- Against: {vote_counts['against']}")
                        output.append(f"- Abstain: {vote_counts['abstain']}")
                    except Exception as e:
                        logger.error(f"Error parsing vote data for proposal {proposal_id}: {str(e)}")
                        continue
            
            if len(output) == 1:
                return "No voting history found."
                    
            return "\n".join(output)
                
        except Exception as e:
            logger.error(f"Error retrieving voting history: {str(e)}")
            return f"Error retrieving voting history: {str(e)}"
    
    def get_menu(self) -> str:
        """Return the menu options"""
        menu = [
            "\n=== DAO Voting System ===",
            "1. View Proposals and Analysis",
            "2. Submit Vote",
            "3. View All Voting History",
            "4. Switch Wallet",
            "5. Exit",
            "\nEnter your choice (1-5): "
        ]
        return "\n".join(menu)