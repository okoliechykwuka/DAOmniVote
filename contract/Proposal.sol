// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract GovernorBravo {
    address public owner;
    uint256 public proposalCount;
    
    enum ProposalState { 
        Pending,
        Active,
        Canceled,
        Defeated,
        Succeeded,
        Queued,
        Expired,
        Executed
    }
    
    struct Proposal {
        uint256 id;
        address proposer;
        uint256 eta;
        uint256 startBlock;
        uint256 endBlock;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool canceled;
        bool executed;
        string description;
        mapping(address => Receipt) receipts;
    }
    
    struct Receipt {
        bool hasVoted;
        uint8 support;
        uint256 votes;
    }
    
    mapping(uint256 => Proposal) public proposals;
    
    event ProposalCreated(
        uint256 id,
        address proposer,
        string description,
        uint256 startBlock,
        uint256 endBlock
    );
    
    event VoteCast(
        address voter,
        uint256 proposalId,
        uint8 support,
        uint256 votes
    );
    
    constructor() {
        owner = msg.sender;
        proposalCount = 0;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }
    
    function makeProposal(
        address proposer,
        string memory description
    ) public onlyOwner returns (uint256) {
        proposalCount++;
        uint256 startBlock = block.number;
        uint256 endBlock = startBlock + 40320; // About 1 week of blocks
        
        Proposal storage newProposal = proposals[proposalCount];
        newProposal.id = proposalCount;
        newProposal.proposer = proposer;
        newProposal.startBlock = startBlock;
        newProposal.endBlock = endBlock;
        newProposal.description = description;
        newProposal.forVotes = 0;
        newProposal.againstVotes = 0;
        newProposal.abstainVotes = 0;
        newProposal.canceled = false;
        newProposal.executed = false;
        
        emit ProposalCreated(
            proposalCount,
            proposer,
            description,
            startBlock,
            endBlock
        );
        
        return proposalCount;
    }
    
    function getProposalDetails(uint256 proposalId) 
        public 
        view 
        returns (
            uint256 id,
            address proposer,
            uint256 startBlock,
            uint256 endBlock,
            uint256 forVotes,
            uint256 againstVotes,
            uint256 abstainVotes,
            bool canceled,
            bool executed,
            string memory description
        ) 
    {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal id");
        Proposal storage proposal = proposals[proposalId];
        
        return (
            proposal.id,
            proposal.proposer,
            proposal.startBlock,
            proposal.endBlock,
            proposal.forVotes,
            proposal.againstVotes,
            proposal.abstainVotes,
            proposal.canceled,
            proposal.executed,
            proposal.description
        );
    }
    
    function state(uint256 proposalId) public view returns (ProposalState) {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal id");
        Proposal storage proposal = proposals[proposalId];
        
        if (proposal.canceled) {
            return ProposalState.Canceled;
        } else if (block.number <= proposal.startBlock) {
            return ProposalState.Pending;
        } else if (block.number <= proposal.endBlock) {
            return ProposalState.Active;
        } else if (proposal.forVotes <= proposal.againstVotes) {
            return ProposalState.Defeated;
        } else if (proposal.executed) {
            return ProposalState.Executed;
        } else if (block.number > proposal.endBlock + 20) {
            return ProposalState.Expired;
        } else {
            return ProposalState.Succeeded;
        }
    }
    
    function castVote(uint256 proposalId, uint8 support) public {
        require(support <= 2, "Invalid vote type");
        require(state(proposalId) == ProposalState.Active, "Proposal not active");
        
        Proposal storage proposal = proposals[proposalId];
        Receipt storage receipt = proposal.receipts[msg.sender];
        require(!receipt.hasVoted, "Already voted");
        
        uint256 votes = 1; // Simplified voting power
        
        receipt.hasVoted = true;
        receipt.support = support;
        receipt.votes = votes;
        
        if (support == 0) {
            proposal.againstVotes += votes;
        } else if (support == 1) {
            proposal.forVotes += votes;
        } else {
            proposal.abstainVotes += votes;
        }
        
        emit VoteCast(msg.sender, proposalId, support, votes);
    }
}