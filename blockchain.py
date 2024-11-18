import os
import json
from web3 import Web3
from pathlib import Path
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

class ProposalState(Enum):
    Pending = 0
    Active = 1
    Canceled = 2
    Defeated = 3
    Succeeded = 4
    Queued = 5
    Expired = 6
    Executed = 7

class GovernorBravoContract:
    def __init__(self, web3_provider_uri, abi_path, contract_address):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider_uri))
        web3_provider_uri = os.getenv("INFURA_URL")
        contract_address = os.getenv("CONTRACT_ADDRESS")
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        
        with open(Path(abi_path)) as f:
            contract_abi = json.load(f)
            
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(contract_address),
            abi=contract_abi
        )
    
    def get_proposal_count(self):
        """Get the total number of proposals"""
        return self.contract.functions.proposalCount().call({
                'from': self.wallet_address})

    def get_proposal_state(self, proposal_id):
        """Get the current state of a proposal with error handling"""
        try:
            state_int = self.contract.functions.state(proposal_id).call()
            return ProposalState(state_int).name
        except Exception as e:
            return f"Invalid or non-existent proposal: {str(e)}"

    def get_proposal_details(self, proposal_id):
        """Get the details of a specific proposal with error handling"""
        try:
            proposal = self.contract.functions.proposals(proposal_id).call()
            
            # GovernorBravo proposal structure typically includes:
            # [id, proposer, eta, startBlock, endBlock, forVotes, againstVotes, abstainVotes, canceled, executed]
            proposal_dict = {
                'id': proposal_id,
                'proposer': proposal[1] if len(proposal) > 1 else None,
                'startBlock': proposal[3] if len(proposal) > 3 else None,
                'endBlock': proposal[4] if len(proposal) > 4 else None,
                'forVotes': proposal[5] if len(proposal) > 5 else None,
                'againstVotes': proposal[6] if len(proposal) > 6 else None,
                'abstainVotes': proposal[7] if len(proposal) > 7 else None,
                'canceled': proposal[8] if len(proposal) > 8 else None,
                'executed': proposal[9] if len(proposal) > 9 else None,
                'state': self.get_proposal_state(proposal_id)
            }
            return proposal_dict
        except Exception as e:
            return None
        

# def main():
#     # Load environment variables
#     web3_provider_uri = os.getenv("INFURA_URL")
#     CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
    
#     # Initialize the governance contract
#     gov = GovernorBravoContract(web3_provider_uri, "contract/compiled/contract_abi.json", CONTRACT_ADDRESS)
    
#     try:
#         # Get total number of proposals
#         proposal_count = gov.get_proposal_count()
#         print(f"Total proposals: {proposal_count}")
        
#         # Get the current block number to use as reference
#         current_block = gov.w3.eth.block_number
#         print(f"Current block number: {current_block}")
        
#         # Instead of iterating from 1, try to get the latest proposals
#         # GovernorBravo proposal IDs are sequential but might start from a higher number
#         latest_proposals = range(max(1, proposal_count - 10), proposal_count + 1)
        
#         print("\nFetching latest proposals...")
#         for proposal_id in latest_proposals:
#             proposal = gov.get_proposal_details(proposal_id)
#             if proposal:
#                 print(f"\nProposal {proposal_id}:")
#                 print(f"State: {proposal['state']}")
#                 print(f"Proposer: {proposal['proposer']}")
#                 if proposal['startBlock'] and proposal['endBlock']:
#                     print(f"Voting period: blocks {proposal['startBlock']} to {proposal['endBlock']}")
#                     if proposal['endBlock'] > current_block:
#                         blocks_left = proposal['endBlock'] - current_block
#                         print(f"Blocks remaining: {blocks_left}")
#                 if proposal['forVotes'] is not None:
#                     print(f"Votes For: {Web3.from_wei(proposal['forVotes'], 'ether')} ETH")
#                     print(f"Votes Against: {Web3.from_wei(proposal['againstVotes'], 'ether')} ETH")
#                     if proposal['abstainVotes'] is not None:
#                         print(f"Votes Abstain: {Web3.from_wei(proposal['abstainVotes'], 'ether')} ETH")

#     except Exception as e:
#         print(f"Error: {str(e)}")

# if __name__ == "__main__":
#     main()