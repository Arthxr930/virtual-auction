# 🛍️ AI Virtual Auction System

A multi-agent virtual auction system with strategic AI buyers competing in real-time bidding wars, powered by DeepSeek API.

## ✨ Features

- **Multi-Strategy AI Buyers**: Three distinct buyer types with unique bidding strategies (Aggressive, Conservative, Psychological)
- **Complete Auction Flow**: Professional auction process with auctioneer, market analysis, and observer analysis
- **Intelligent Bidding Competition**: AI agents make strategic decisions based on budget, market conditions, and historical experience
- **Market Analysis System**: Real-time valuation insights and market trend analysis
- **Long-term Memory System**: AI learns from past auctions and continuously optimizes strategies
- **Beautiful Output**: Colored terminal output for clear auction progress visualization
- **Comprehensive Analysis**: Post-auction performance analysis and strategic insights

## 🏗️ Project Structure

```
virtual_auction/
├── virtual_auction.py        # ⭐ Core file (contains all game logic)
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create yourself)
├── .env.example              # Environment variables example
├── auction_history/          # Auction records directory
├── auction_memory/           # Long-term memory directory
└── README.md                 # Documentation
```

**Note**: This project follows a single-file architecture. All core code (auction flow, buyer strategies, configuration, state management, analysis system, etc.) is consolidated in `virtual_auction.py` for easier understanding and maintenance.

## 🚀 Quick Start

### 1. Install Dependencies

**Method 1: Using UV (Recommended)**

[UV](https://github.com/astral-sh/uv) is an extremely fast Python package manager.

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install project dependencies
uv pip install -e .
```

**Method 2: Using Traditional pip**

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file and add your DeepSeek API Key:

```bash
# .env file content
DEEPSEEK_API_KEY=your_api_key_here
```

**Getting API Key**:
1. Visit [DeepSeek Platform](https://platform.deepseek.com/)
2. Register and login
3. Create a new API Key in "API Keys" page
4. Copy the API Key and paste it into the `.env` file

### 3. Run the Auction

**Interactive Mode** (Recommended):
```bash
python virtual_auction.py
# or
python3 virtual_auction.py
```

**Auto Mode** (No interaction, just watch):
```bash
python virtual_auction.py --auto
# or
python3 virtual_auction.py --auto
```

## 🎯 Auction Rules

### Buyer Strategies (6 buyers total)
- 🗣️ **Aggressive Buyers** (2): Bid frequently, drive up prices, intimidate competitors
- 🎯 **Conservative Buyers** (2): Wait for bargains, careful budget management, selective bidding
- 🧠 **Psychological Buyers** (1): Use fake bids, manipulate market, strategic withdrawal

### Auction Components
- **🏛️ Auctioneer**: Hosts auction, announces items and bids, determines winners
- **📊 Market Analyst**: Provides item valuations and market insights
- **👁️ Observer**: Analyzes bidding patterns and strategies

### Auction Flow

**Item Auction Process**:
1. Auctioneer announces item and starting price
2. Market Analyst provides valuation insights
3. Bidding rounds begin:
   - Each buyer decides whether/ how much to bid
   - Auctioneer announces new highest bids
   - Continues until no new bids for a period
4. Auctioneer declares winner
5. Observer analyzes the auction round

**Victory Conditions**:
- Buyers aim to acquire valuable items at good prices
- Budget management is crucial
- Strategic bidding determines success

## 🤖 AI Buyer Details

### 1. 🗣️ Aggressive Buyer
- **Goal**: Win items through dominant bidding
- **Strategy**:
  - Bid early and frequently
  - Drive up prices to intimidate others
  - Accept premium prices for desired items
  - Control auction pace through aggression

### 2. 🎯 Conservative Buyer
- **Goal**: Find bargains and preserve budget
- **Strategy**:
  - Wait for low prices before entering
  - Bid minimally when participating
  - Withdraw when prices exceed limits
  - Focus on value over winning

### 3. 🧠 Psychological Buyer
- **Goal**: Manipulate market through deception
- **Strategy**:
  - Use fake bids to create competition
  - Strategic withdrawal to confuse opponents
  - Psychological warfare tactics
  - Manipulate others into bidding wars

## 🧠 Long-term Memory System

AI learns from each auction and continuously optimizes strategies:

1. **Auction Review**: Automatically analyzes bidding patterns after each auction
2. **Experience Extraction**: Extracts success/failure experiences for each strategy
3. **Memory Storage**: Saves to `auction_memory/` directory
4. **Experience Application**: Automatically loads historical experiences when starting new auctions

## ⚙️ Configuration

### Auction Configuration (`virtual_auction.py` - `AuctionConfig` class)

```python
# Buyer and item counts
TOTAL_BUYERS = 6  # Total number of buyers
TOTAL_ITEMS = 5   # Number of items to auction

# Buyer strategy configuration
ROLE_CONFIG = {
    "auctioneer": 1,          # Auctioneer (system role)
    "aggressive_buyer": 2,    # Aggressive buyers
    "conservative_buyer": 2,  # Conservative buyers
    "psychological_buyer": 1  # Psychological buyers
}

# Auction parameters
MIN_BID_INCREMENT = 10       # Minimum bid increment ($)
BUYER_BUDGET_MIN = 200      # Minimum buyer budget
BUYER_BUDGET_MAX = 1000     # Maximum buyer budget
ITEM_VALUE_MIN = 50         # Minimum item value
ITEM_VALUE_MAX = 500        # Maximum item value

# Long-term memory
ENABLE_LONG_TERM_MEMORY = True  # Enable cross-auction learning
MAX_HISTORY_GAMES = 5          # Keep recent N auctions
```

## 📊 Auction Output Example

```
================================================================================
                            🔨 Auctioning Item 1: Antique Item 1
================================================================================

🏛️ Auctioneer: Ladies and gentlemen, we begin with Antique Item 1, starting at $125!

📊 Market Analyst: This antique shows excellent craftsmanship with an estimated market value between $300-450. Current market trends suggest strong demand for similar pieces...

📢 Round 1 - Current price: $125

💰 Buyer 1 bids $150
💰 Buyer 3 bids $180
🚫 Buyer 2 passes
🚫 Buyer 4 passes
🚫 Buyer 5 passes
🚫 Buyer 6 passes

🏛️ Auctioneer: We have $180 from Buyer 3! Do I hear $190?

📢 Round 2 - Current price: $180

💰 Buyer 1 bids $200
🚫 Buyer 3 passes
🚫 Buyer 2 passes
🚫 Buyer 4 passes
🚫 Buyer 5 passes
🚫 Buyer 6 passes

🏛️ Auctioneer: $200 from Buyer 1! Going once...

🏛️ Auctioneer: Congratulations! Buyer 1 wins Antique Item 1 for $200!

👁️ Observer: This auction showed clear aggressive vs conservative strategies, with the aggressive buyer securing the win through persistent bidding...
```

## 🧪 Testing

Verify code syntax:

```bash
# Verify Python syntax
python3 -m py_compile virtual_auction.py

# View help information
python3 virtual_auction.py --help
```

## 🔧 Customization

### Adding New Buyer Strategies

1. Create new buyer class in `virtual_auction.py`:

```python
class NewStrategyBuyer(BaseBuyer):
    def _build_system_prompt(self):
        return """You are a new strategy buyer, your approach is..."""

    # Implement specific bidding logic
```

2. Add to configuration in `AuctionConfig`:

```python
ROLE_CONFIG = {
    "aggressive_buyer": 2,
    "conservative_buyer": 2,
    "psychological_buyer": 1,
    "new_strategy_buyer": 1  # New strategy
}
```

### Adjusting Auction Parameters

Modify `AuctionConfig` class in `virtual_auction.py`:

```python
class AuctionConfig:
    TOTAL_BUYERS = 8  # Change to 8 buyers
    TOTAL_ITEMS = 3   # Change to 3 items

    BUYER_BUDGET_MAX = 1500  # Increase max budget
```

### Disabling Components

```python
class AuctionConfig:
    MARKET_ANALYST = False  # Disable market analyst
    OBSERVER = False        # Disable observer
    ENABLE_LONG_TERM_MEMORY = False  # Disable memory system
```

## 📝 FAQ

### Q: API call failed, what to do?

A: Check the following:
1. Confirm API Key in `.env` file is correct
2. Check network connection is normal
3. Confirm DeepSeek API balance is sufficient

### Q: AI bidding seems too random?

A: You can try:
1. Let AI participate in multiple auctions to accumulate experience
2. Adjust `TEMPERATURE` parameter (0.7-1.0)
3. Modify buyer strategy prompts for more specific guidance

### Q: Auction takes too long?

A: You can:
1. Reduce buyer count or item count
2. Increase `MIN_BID_INCREMENT` to speed up bidding
3. Adjust bidding timeout settings

### Q: Can I use other LLM APIs?

A: Yes! Modify API configuration in `virtual_auction.py`:

```python
DEEPSEEK_BASE_URL = "https://api.openai.com/v1"  # Change to OpenAI
MODEL_NAME = "gpt-4"
```

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

MIT License

## 🙏 Acknowledgments

- [DeepSeek](https://www.deepseek.com/) - Providing powerful AI API
- [OpenAI Python SDK](https://github.com/openai/openai-python) - Excellent API client
- [Colorama](https://github.com/tartley/colorama) - Cross-platform colored terminal output

---

**🛍️ Start your AI Virtual Auction journey!**
