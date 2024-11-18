#proposal_analysis.py
import os
import logging
# from openai import OpenAI
import anthropic
from dotenv import load_dotenv
from web3 import Web3
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProposalAnalyzer:
    def __init__(self):
        load_dotenv()
        
        # Initialize OpenAI client
        # self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Set up Anthropic client
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Initialize Web3 and contract (read-only operations)
        self.web3 = Web3(Web3.HTTPProvider(os.getenv("INFURA_URL")))
        self.contract_address = os.getenv("CONTRACT_ADDRESS")
        
        # Load contract ABI
        with open("contract/compiled/contract_abi.json", "r") as f:
            contract_abi = json.load(f)
        
        # Initialize contract
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=contract_abi
        )
        
        # Fetch wallet balance
        self.wallet_balance = self.web3.eth.get_balance(self.web3.to_checksum_address(os.getenv("WALLET_ADDRESS")))
        
        logger.info(f"Wallet balance: {self.wallet_balance} ETH")
    
    def chat_model(self, prompt):
        # logger.info(f"Sending prompt to OpenAI: {prompt}")
        
        # try:
        #     completion = self.client.chat.completions.create(
        #         model="gpt-4o-mini",
        #         messages=[{"role": "user", "content": prompt}]
        #     )
        #     return completion.choices[0].message.content
        # except Exception as e:
        #     logger.error(f"Error communicating with OpenAI: {str(e)}")
        #     return "Error communicating with OpenAI."
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.8,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Error communicating with Anthropic: {str(e)}")
            return "Error communicating with Anthropic."

    def evaluate_proposal(self, proposal):
        """Evaluate a single proposal based on various metrics"""
        evaluation = {
            'id': proposal['id'],
            'feasibility': 'High',
            'impact': 'Moderate',
            'alignment': 'Yes',
            'support_ratio': 0,
            'status': 'Active',
            'risks': []
        }

        # Calculate support ratio
        total_votes = proposal['forVotes'] + proposal['againstVotes'] + proposal['abstainVotes']
        if total_votes > 0:
            evaluation['support_ratio'] = (proposal['forVotes'] / total_votes) * 100

        # Evaluate feasibility based on support ratio
        if evaluation['support_ratio'] < 30:
            evaluation['feasibility'] = 'Low'
        elif evaluation['support_ratio'] > 70:
            evaluation['feasibility'] = 'High'

        # Evaluate impact based on total participation
        if total_votes > 1000:
            evaluation['impact'] = 'High'
        elif total_votes > 500:
            evaluation['impact'] = 'Moderate'
        else:
            evaluation['impact'] = 'Low'

        # Check proposal state
        state = proposal['state']
        if state == 1:  # Active
            evaluation['status'] = 'Active'
        elif state == 2:  # Canceled
            evaluation['status'] = 'Canceled'
            evaluation['risks'].append('Proposal has been canceled')
        elif state == 3:  # Defeated
            evaluation['status'] = 'Defeated'
            evaluation['risks'].append('Proposal did not receive sufficient support')
        elif state == 4:  # Succeeded
            evaluation['status'] = 'Succeeded'

        return evaluation

    def analyze_proposals(self):
        """Analyze all recent proposals and provide insights"""
        try:
            logger.info("Starting proposal analysis process.")
            
            # Fetch total number of proposals
            proposal_count = self.contract.functions.proposalCount().call()
            latest_proposals = range(max(1, proposal_count - 10), proposal_count + 1)

            all_proposals = []
            
            for proposal_id in latest_proposals:
                try:
                    proposal_details = self.contract.functions.proposals(proposal_id).call()
                    state = self.contract.functions.state(proposal_id).call()
                    
                    if proposal_details:
                        proposal_dict = {
                            'id': proposal_details[0],
                            'proposer': proposal_details[1],
                            'startBlock': proposal_details[2],
                            'endBlock': proposal_details[3],
                            'forVotes': proposal_details[4],
                            'againstVotes': proposal_details[5],
                            'abstainVotes': proposal_details[6],
                            'state': state
                        }
                        all_proposals.append(proposal_dict)
                except Exception as e:
                    logger.error(f"Error fetching proposal {proposal_id}: {str(e)}")
                    continue

            if not all_proposals:
                return "No active or recent proposals detected in the governance contract."
            
            # Evaluate all proposals
            evaluations = [self.evaluate_proposal(proposal) for proposal in all_proposals]
            
            # Prepare analytics summary
            active_proposals = len([e for e in evaluations if e['status'] == 'Active'])
            high_impact_proposals = len([e for e in evaluations if e['impact'] == 'High'])
            avg_support = sum(e['support_ratio'] for e in evaluations) / len(evaluations)
            
            # Prepare prompt for detailed analysis
            prompt = f"""
            Analyze the following DAO governance data:
            
            Current State:
            - Total Proposals Analyzed: {len(evaluations)}
            - Active Proposals: {active_proposals}
            - High Impact Proposals: {high_impact_proposals}
            - Average Support Ratio: {avg_support:.2f}%
            
            Detailed Evaluations: {evaluations}
            
            Provide a concise analysis focusing on:
            1. Overall governance health
            2. Key trends in proposal success/failure
            3. Recommendations for improving participation
            """

            analysis_response = self.chat_model(prompt)
            return analysis_response

        except Exception as e:
            logger.error(f"Error during proposal analysis: {str(e)}")
            return f"An error occurred during analysis: {str(e)}"

# def main():
#     analyzer = ProposalAnalyzer()
#     response = analyzer.analyze_proposals()
#     print(f"\nDAO Analysis Response:\n{response}")

# if __name__ == "__main__":
#     main()