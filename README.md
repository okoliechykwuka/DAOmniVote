# DAO Voting System

A comprehensive voting and proposal analysis system for Decentralized Autonomous Organizations (DAOs) built with Python, Web3, and Redis.

## 🌟 Features

- Real-time proposal analysis and evaluation
- Secure voting mechanism with wallet integration
- Historical vote tracking and analytics
- Integration with Ethereum blockchain
- Automated proposal state monitoring
- Support for multiple voting options (For, Against, Abstain)
- Redis-based session management
- Detailed governance analytics using AI (Claude)

## 🔧 Prerequisites

- Python 3.8+
- Redis Server
- Ethereum Node Access (Infura)
- Anthropic API Key
- Docker (for deployment)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/okoliechykwuka/DAOmniVote.git
cd dao-voting-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` file with your credentials:
```
AGENT_PRIVATE_KEY = your_agent_private_key
THEORIQ_URI=https://theoriq-backend.prod-02.chainml.net
INFURA_URL=your_infura_url
CONTRACT_ADDRESS=your_contract_address
ANTHROPIC_API_KEY=your_anthropic_api_key
REDIS_HOST=...
REDIS_PORT=..
REDIS_PASSWORD=...
```

## 🏃‍♂️ Running the Application

### Local Development
```bash
python main.py
```

### Using Docker
```bash
docker build -t dao-voting-system .
docker run -p 8000:8000 dao-voting-system
```

## 📁 Project Structure

```
dao-voting-system/
├── proposal_analysis.py   # Proposal analysis and AI integration
├── voting.py             # Core voting system implementation
├── blockchain.py         # Blockchain interaction layer
├── main.py              # Application entry point
├── contract/            # Smart contract artifacts
│   └── compiled/
│       └── contract_abi.json
├── Dockerfile           # Container configuration
└── requirements.txt     # Project dependencies
```

## 🔒 Security

- All blockchain interactions are read-only by default
- Session-based wallet management
- No private keys stored in the application
- Rate limiting on API endpoints
- Input validation for all user inputs

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
