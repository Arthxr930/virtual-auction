"""
AI Multi-Agent Virtual Auction System
All core code is consolidated in a single file

How to run:
  python virtual_auction.py          # Interactive mode
  python virtual_auction.py --auto   # Auto-run mode
"""

import random
import time
import json
import os
import re
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from colorama import Fore, Style, init
from openai import OpenAI
from dotenv import load_dotenv

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()


# ==================== Configuration Class ====================

class AuctionConfig:
    """Virtual auction configuration class"""

    # ==================== API Configuration ====================
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    MODEL_NAME = "deepseek-chat"

    # ==================== Basic Game Configuration ====================
    TOTAL_BUYERS = 5  # Total number of buyers (aggressive:2 + conservative:2 + psychological:1)
    TOTAL_ITEMS = 5   # Number of items to auction

    # Role configuration (1 auctioneer, 2 aggressive buyers, 2 conservative buyers, 1 psychological buyer)
    ROLE_CONFIG = {
        "auctioneer": 1,          # Auctioneer (system role, not counted in TOTAL_BUYERS)
        "aggressive_buyer": 2,    # Aggressive buyers (frequent bidding)
        "conservative_buyer": 2,  # Conservative buyers (only bid when low price)
        "psychological_buyer": 1  # Psychological buyers (fake bids to manipulate)
    }

    # Additional roles
    MARKET_ANALYST = True  # Enable market analyst
    OBSERVER = True        # Enable observer

    # ==================== AI Behavior Parameters ====================
    TEMPERATURE = 0.9
    MAX_TOKENS = 1500

    # Speech limits
    MAX_SPEECH_WORDS = 150
    MAX_ANALYSIS_WORDS = 100

    # ==================== Auction Rules ====================
    # Bid increment
    MIN_BID_INCREMENT = 10

    # Budget ranges for buyers
    BUYER_BUDGET_MIN = 200
    BUYER_BUDGET_MAX = 1000

    # Item value ranges
    ITEM_VALUE_MIN = 50
    ITEM_VALUE_MAX = 500

    # Bidding timeout (seconds)
    BID_TIMEOUT = 30

    # ==================== Game Flow Configuration ====================
    SAVE_GAME_HISTORY = True
    GAME_HISTORY_DIR = "auction_history"

    # ==================== Display Configuration ====================
    SHOW_AI_THINKING = True

    # ==================== Role Descriptions (for system prompts) ====================
    ROLE_DESCRIPTIONS = {
        "auctioneer": """You are the auctioneer hosting this virtual auction.
Responsibilities:
- Maintain auction order and fairness
- Announce items and current highest bids
- Determine winners when no more bids
- Ensure smooth auction process""",

        "aggressive_buyer": """You are an aggressive buyer. Your strategy is:
- Bid frequently to create competition
- Try to drive up prices quickly
- Have high budget but spend aggressively
- Intimidate other buyers with rapid bidding""",

        "conservative_buyer": """You are a conservative buyer. Your strategy is:
- Only bid when price is below your valuation
- Wait for good opportunities
- Careful with budget management
- Prefer to buy at bargain prices""",

        "psychological_buyer": """You are a psychological buyer. Your strategy is:
- Use fake bids to manipulate market
- Create false competition to drive prices up for others
- Withdraw bids strategically to confuse opponents
- Psychological warfare through bidding patterns"""
    }

    # ==================== Memory System Configuration ====================
    ENABLE_LONG_TERM_MEMORY = True
    MEMORY_FILE_DIR = "auction_memory"
    MAX_HISTORY_GAMES = 5

    @classmethod
    def validate(cls):
        """Validate configuration validity"""
        # Only count buyer roles (exclude system roles like auctioneer)
        buyer_roles = ["aggressive_buyer", "conservative_buyer", "psychological_buyer"]
        total_buyer_roles = sum(cls.ROLE_CONFIG.get(role, 0) for role in buyer_roles)

        if total_buyer_roles != cls.TOTAL_BUYERS:
            raise ValueError(
                f"Total buyer role count ({total_buyer_roles}) does not equal total buyers ({cls.TOTAL_BUYERS})"
            )

        if not cls.DEEPSEEK_API_KEY:
            raise ValueError(
                "❌ Error: DEEPSEEK_API_KEY not found!\n"
                "Please set DEEPSEEK_API_KEY=your_api_key in .env file\n"
                "Or set environment variable: export DEEPSEEK_API_KEY=your_api_key"
            )

        print("✅ Auction configuration validated successfully")
        return True


# ==================== API Client ====================

class DeepSeekClient:
    """DeepSeek API client class"""

    def __init__(self):
        """Initialize DeepSeek client"""
        self.client = OpenAI(
            api_key=AuctionConfig.DEEPSEEK_API_KEY,
            base_url=AuctionConfig.DEEPSEEK_BASE_URL
        )
        self.model = AuctionConfig.MODEL_NAME
        self.temperature = AuctionConfig.TEMPERATURE
        self.max_tokens = AuctionConfig.MAX_TOKENS

    def chat(self, system_prompt: str, user_message: str, temperature: float = None) -> str:
        """Send chat request to DeepSeek API"""
        try:
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens
            )

            elapsed_time = time.time() - start_time
            reply = response.choices[0].message.content

            print(f"⏱️  API response time: {elapsed_time:.2f}s")
            return reply

        except Exception as e:
            error_msg = f"❌ DeepSeek API call failed: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)


# ==================== Memory Management System ====================

class MemoryManager:
    """Memory manager - Cross-auction experience system"""

    def __init__(self):
        """Initialize memory manager"""
        self.memory_dir = AuctionConfig.MEMORY_FILE_DIR
        os.makedirs(self.memory_dir, exist_ok=True)

    def save_auction_experience(self, role: str, experience: str, auction_id: str):
        """Save single auction experience"""
        memory_file = self._get_memory_file(role)
        memories = self._load_memory(role)

        memories.append({
            "auction_id": auction_id,
            "timestamp": datetime.now().isoformat(),
            "experience": experience
        })

        if len(memories) > AuctionConfig.MAX_HISTORY_GAMES:
            memories = memories[-AuctionConfig.MAX_HISTORY_GAMES:]

        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)

    def load_role_experience(self, role: str) -> str:
        """Load role's historical experience"""
        memories = self._load_memory(role)

        if not memories:
            return "No historical experience yet"

        experience_parts = []
        experience_parts.append(f"【Historical Experience for {role.replace('_', ' ').title()}】")
        experience_parts.append(f"(Experience summary from the last {len(memories)} auctions)")

        for i, memory in enumerate(memories[-3:], 1):
            experience_parts.append(f"\nAuction {i} experience: {memory['experience']}")

        return "\n".join(experience_parts)

    def _get_memory_file(self, role: str) -> str:
        """Get memory file path"""
        return os.path.join(self.memory_dir, f"{role}_memory.json")

    def _load_memory(self, role: str) -> list:
        """Load role memory"""
        memory_file = self._get_memory_file(role)

        if not os.path.exists(memory_file):
            return []

        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []


# ==================== Auction Analysis System ====================

class AuctionAnalyzer:
    """Auction analyzer - Post-auction review system"""

    def __init__(self, auction_data: dict):
        """Initialize analyzer"""
        self.auction_data = auction_data

    def analyze_auction(self) -> dict:
        """Comprehensive auction analysis"""
        analysis = {
            "auction_summary": self._analyze_auction_summary(),
            "buyer_performance": self._analyze_buyer_performance(),
            "key_moments": self._analyze_key_moments(),
            "lessons_learned": self._extract_lessons()
        }
        return analysis

    def _analyze_auction_summary(self) -> dict:
        """Analyze auction overview"""
        total_items = len(self.auction_data.get("items", []))
        total_bids = sum(len(item.get("bids", [])) for item in self.auction_data.get("items", []))
        total_revenue = sum(item.get("final_price", 0) for item in self.auction_data.get("items", []))

        return {
            "total_items": total_items,
            "total_bids": total_bids,
            "total_revenue": total_revenue,
            "average_price": total_revenue / total_items if total_items > 0 else 0
        }

    def _analyze_buyer_performance(self) -> dict:
        """Analyze each buyer's performance"""
        performance = {}

        buyers = self.auction_data.get("buyers", {})
        items = self.auction_data.get("items", [])

        for buyer_id, buyer_info in buyers.items():
            wins = sum(1 for item in items if item.get("winner") == int(buyer_id))
            total_spent = sum(item.get("final_price", 0) for item in items if item.get("winner") == int(buyer_id))
            budget_used = total_spent / buyer_info.get("budget", 1) * 100

            performance[buyer_id] = {
                "role": buyer_info.get("role"),
                "wins": wins,
                "total_spent": total_spent,
                "budget_used": budget_used,
                "items_won": [item.get("id") for item in items if item.get("winner") == int(buyer_id)]
            }

        return performance

    def _analyze_key_moments(self) -> list:
        """Analyze key moments"""
        key_moments = []
        items = self.auction_data.get("items", [])

        for item in items:
            bids = item.get("bids", [])
            if len(bids) > 5:
                key_moments.append({
                    "type": "intense_bidding",
                    "description": f"Item {item.get('id')} had intense bidding war ({len(bids)} bids)",
                    "impact": "high",
                    "lesson": "Multiple buyers showed strong interest, strategic bidding opportunities"
                })

        return key_moments

    def _extract_lessons(self) -> dict:
        """Extract lessons learned"""
        lessons = {
            "aggressive_buyer": [],
            "conservative_buyer": [],
            "psychological_buyer": [],
            "general": []
        }

        performance = self._analyze_buyer_performance()

        # Analyze aggressive buyers
        aggressive_buyers = [pid for pid, perf in performance.items() if perf["role"] == "aggressive_buyer"]
        if aggressive_buyers:
            high_spenders = [pid for pid in aggressive_buyers if performance[pid]["budget_used"] > 70]
            if high_spenders:
                lessons["aggressive_buyer"].append("✅ Aggressive strategy effective in driving up prices and winning items")
            else:
                lessons["aggressive_buyer"].append("❌ Aggressive bidding led to budget exhaustion without proportional wins")

        # Analyze conservative buyers
        conservative_buyers = [pid for pid, perf in performance.items() if perf["role"] == "conservative_buyer"]
        if conservative_buyers:
            bargain_hunters = [pid for pid in conservative_buyers if performance[pid]["wins"] > 0 and performance[pid]["budget_used"] < 50]
            if bargain_hunters:
                lessons["conservative_buyer"].append("✅ Conservative strategy successful in finding bargains")
            else:
                lessons["conservative_buyer"].append("❌ Conservative approach missed good opportunities")

        lessons["general"].append("💡 Monitor competitors' bidding patterns to identify strategies")
        lessons["general"].append("💡 Balance aggression with budget management")
        lessons["general"].append("💡 Psychological tactics can manipulate market dynamics")

        return lessons

    def generate_report(self) -> str:
        """Generate readable analysis report"""
        analysis = self.analyze_auction()
        report_parts = []

        summary = analysis["auction_summary"]
        report_parts.append("=" * 60)
        report_parts.append("📊 Auction Post-Analysis Report")
        report_parts.append("=" * 60)
        report_parts.append(f"\n【Auction Summary】")
        report_parts.append(f"  Items auctioned: {summary['total_items']}")
        report_parts.append(f"  Total bids: {summary['total_bids']}")
        report_parts.append(f"  Total revenue: ${summary['total_revenue']}")
        report_parts.append(f"  Average price: ${summary['average_price']:.2f}")

        if analysis["key_moments"]:
            report_parts.append(f"\n【Key Moments】")
            for moment in analysis["key_moments"]:
                report_parts.append(f"  • {moment['description']}")

        lessons = analysis["lessons_learned"]
        report_parts.append(f"\n【Lessons Learned】")

        for role, role_lessons in lessons.items():
            if role_lessons:
                if role != "general":
                    report_parts.append(f"\n  {role.replace('_', ' ').title()}:")
                else:
                    report_parts.append(f"\n  💡 General Insights:")
                for lesson in role_lessons:
                    report_parts.append(f"    {lesson}")

        report_parts.append("\n" + "=" * 60)
        return "\n".join(report_parts)

    def save_to_memory(self, buyer_role: str) -> str:
        """Generate memory text for specific role"""
        analysis = self.analyze_auction()
        lessons = analysis["lessons_learned"]

        memory_parts = []

        if buyer_role in lessons:
            memory_parts.extend(lessons[buyer_role])

        memory_parts.extend(lessons["general"])

        for moment in analysis["key_moments"]:
            if moment.get("lesson"):
                memory_parts.append(moment["lesson"])

        return " | ".join(memory_parts)


# ==================== Game State Management ====================

class AuctionState:
    """Auction state management class"""

    def __init__(self, buyers: dict, items: list):
        """Initialize auction state"""
        self.buyers = buyers
        self.items = items
        self.current_item_index = 0
        self.auction_history = []
        self.bidding_history = []
        self.start_time = datetime.now()
        self._record_initial_state()

    def _record_initial_state(self):
        """Record initial auction state"""
        buyer_info = []
        for bid, buyer in self.buyers.items():
            buyer_info.append({
                "buyer_id": bid,
                "role": buyer.role,
                "budget": buyer.budget,
                "is_active": buyer.is_active
            })

        item_info = []
        for item in self.items:
            item_info.append({
                "item_id": item["id"],
                "name": item["name"],
                "value": item["value"]
            })

        self.auction_history.append({
            "type": "auction_start",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "total_buyers": len(self.buyers),
                "total_items": len(self.items),
                "buyers": buyer_info,
                "items": item_info
            }
        })

    def get_active_buyers(self) -> List[int]:
        """Get IDs of all active buyers"""
        return [bid for bid, buyer in self.buyers.items() if buyer.is_active]

    def get_current_item(self) -> dict:
        """Get current item being auctioned"""
        if self.current_item_index < len(self.items):
            return self.items[self.current_item_index]
        return None

    def record_bid(self, buyer_id: int, item_id: int, bid_amount: int):
        """Record a bid"""
        bid = {
            "buyer_id": buyer_id,
            "item_id": item_id,
            "bid_amount": bid_amount,
            "timestamp": datetime.now().isoformat()
        }
        self.bidding_history.append(bid)

        self.auction_history.append({
            "type": "bid",
            "timestamp": datetime.now().isoformat(),
            "data": bid
        })

    def finalize_item_sale(self, item_id: int, winner_id: int, final_price: int):
        """Finalize item sale"""
        sale = {
            "item_id": item_id,
            "winner_id": winner_id,
            "final_price": final_price,
            "timestamp": datetime.now().isoformat()
        }

        self.auction_history.append({
            "type": "sale",
            "timestamp": datetime.now().isoformat(),
            "data": sale
        })

    def next_item(self):
        """Move to next item"""
        self.current_item_index += 1

    def update_buyer_budget(self, buyer_id: int, spent_amount: int):
        """Update buyer budget after purchase"""
        if buyer_id in self.buyers:
            self.buyers[buyer_id].budget -= spent_amount

    def get_auction_summary(self) -> str:
        """Generate auction summary"""
        summary = []

        summary.append(f"🎯 Total items auctioned: {len(self.items)}")
        summary.append(f"⏱️  Auction duration: {(datetime.now() - self.start_time).seconds} seconds")

        total_revenue = 0
        for item in self.items:
            if "winner" in item and "final_price" in item:
                winner = item["winner"]
                price = item["final_price"]
                total_revenue += price
                summary.append(f"  Item {item['id']}: {item['name']} - Sold to Buyer {winner} for ${price}")

        summary.append(f"💰 Total revenue: ${total_revenue}")

        return "\n".join(summary)

    def export_to_dict(self) -> dict:
        """Export auction state as dictionary"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "buyers": {
                bid: {
                    "role": buyer.role,
                    "budget": buyer.budget,
                    "is_active": buyer.is_active
                }
                for bid, buyer in self.buyers.items()
            },
            "items": self.items,
            "bidding_history": self.bidding_history,
            "auction_history": self.auction_history
        }


# ==================== Role Classes ====================

class BaseBuyer:
    """Base buyer class"""

    def __init__(self, buyer_id: int, role: str, budget: int, historical_experience: str = ""):
        """Initialize buyer"""
        self.buyer_id = buyer_id
        self.role = role
        self.budget = budget
        self.is_active = True
        self.client = DeepSeekClient()
        self.historical_experience = historical_experience
        self.known_info = {}
        self.memory = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build role system prompt"""
        base_prompt = f"""You are participating in a virtual auction.

【Your Identity】
You are Buyer {self.buyer_id}, Strategy: {self.role.replace('_', ' ').title()}

【Your Budget】
You have ${self.budget} to spend on items.

【Role Description】
{AuctionConfig.ROLE_DESCRIPTIONS.get(self.role, "")}

【Auction Rules】
- Items have hidden values (you don't know exact values)
- You can bid any amount above current highest bid + minimum increment
- Minimum increment: ${AuctionConfig.MIN_BID_INCREMENT}
- You cannot bid more than your remaining budget
- Auction continues until no new bids for a period

【Important Rules】
1. **Budget Management**: Never bid more than your budget
2. **Strategic Bidding**: Follow your role's strategy
3. **Market Analysis**: Consider item value vs price
4. **Competition**: Watch other buyers' bidding patterns"""

        if self.historical_experience:
            base_prompt += f"""

【💡 Historical Experience - Lessons from past auctions】
{self.historical_experience}

**Apply these experiences**:
1. Reference past strategies when bidding
2. Adapt based on current market conditions
3. Learn from previous auction outcomes"""

        base_prompt += "\n\nMake strategic bidding decisions based on your role, budget, and experience."
        return base_prompt

    def decide_bid(self, current_item: dict, current_price: int, bidding_history: list, active_buyers: list) -> str:
        """Decide whether and how much to bid"""
        context = self._build_bid_context(current_item, current_price, bidding_history, active_buyers)

        prompt = f"""Current auction situation:

【Item Information】
{context['item_info']}

【Current Price】
${current_price}

【Bidding History】
{context['bid_history']}

【Your Status】
Budget: ${self.budget}
Strategy: {self.role.replace('_', ' ').title()}

【Active Competitors】
{len(active_buyers)} buyers still active

Please decide your bid:
- If you want to bid, respond with: "Bid: $[amount]"
- If you pass, respond with: "Pass"
- Consider your strategy, budget, and item value

Your decision:"""

        response = self.client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt,
            temperature=AuctionConfig.TEMPERATURE
        )

        self.memory.append({
            "type": "bid_decision",
            "item": current_item["id"],
            "current_price": current_price,
            "decision": response
        })

        return response

    def _build_bid_context(self, current_item: dict, current_price: int, bidding_history: list, active_buyers: list) -> dict:
        """Build bidding context"""
        item_info = f"Item {current_item['id']}: {current_item['name']} (estimated value: ${current_item['value']})"

        recent_bids = [bid for bid in bidding_history if bid["item_id"] == current_item["id"]][-5:]
        bid_history = "\n".join([
            f"Buyer {bid['buyer_id']}: ${bid['bid_amount']}"
            for bid in recent_bids
        ]) if recent_bids else "No bids yet"

        return {
            "item_info": item_info,
            "bid_history": bid_history
        }

    def update_memory(self, event_type: str, content: str):
        """Update buyer memory"""
        self.memory.append({
            "type": event_type,
            "content": content
        })


class AggressiveBuyer(BaseBuyer):
    """Aggressive buyer - bids frequently"""

    def __init__(self, buyer_id: int, budget: int, historical_experience: str = ""):
        super().__init__(buyer_id, "aggressive_buyer", budget, historical_experience)

    def _build_system_prompt(self) -> str:
        """Build aggressive buyer system prompt"""
        prompt = f"""You are an aggressive buyer in this virtual auction.

【Your Identity】
You are Buyer {self.buyer_id}, Aggressive Buyer

【Your Budget】
You have ${self.budget} to spend aggressively.

【Aggressive Strategy】
1. **Frequent Bidding**: Bid often to create competition
2. **Price Driving**: Try to drive up prices quickly
3. **Intimidation**: Use rapid bidding to discourage others
4. **High Budget Usage**: Willing to spend more to win items

【Bidding Tactics】
- Bid early and often
- Increase bids by larger amounts to show strength
- Don't wait for others - take initiative
- Accept paying premium prices for desired items

【Risk Management】
- Monitor budget but be willing to spend
- Focus on winning rather than bargains
- Use aggression to control auction pace

【Important Notes】
- Your goal is to win items, not save money
- Aggressiveness can intimidate competitors
- Multiple wins justify higher prices per item"""

        if self.historical_experience:
            prompt += f"""

【💡 Historical Experience】
{self.historical_experience}

Apply aggressive tactics learned from past auctions."""
        return prompt


class ConservativeBuyer(BaseBuyer):
    """Conservative buyer - only bids when price is low"""

    def __init__(self, buyer_id: int, budget: int, historical_experience: str = ""):
        super().__init__(buyer_id, "conservative_buyer", budget, historical_experience)

    def _build_system_prompt(self) -> str:
        """Build conservative buyer system prompt"""
        prompt = f"""You are a conservative buyer in this virtual auction.

【Your Identity】
You are Buyer {self.buyer_id}, Conservative Buyer

【Your Budget】
You have ${self.budget} to spend carefully.

【Conservative Strategy】
1. **Patient Waiting**: Only bid when price is below your valuation
2. **Bargain Hunting**: Look for good deals
3. **Budget Preservation**: Careful spending management
4. **Selective Participation**: Pass on overpriced items

【Bidding Tactics】
- Wait for low prices before entering
- Bid minimally when you do bid
- Withdraw if price exceeds your limit
- Save budget for truly valuable items

【Risk Management】
- Never overpay for items
- Accept missing some auctions for bargains later
- Focus on value, not winning

【Important Notes】
- Quality over quantity
- Patience is key
- Know when to walk away"""

        if self.historical_experience:
            prompt += f"""

【💡 Historical Experience】
{self.historical_experience}

Apply conservative lessons from past auctions."""
        return prompt


class PsychologicalBuyer(BaseBuyer):
    """Psychological buyer - uses fake bids to manipulate"""

    def __init__(self, buyer_id: int, budget: int, historical_experience: str = ""):
        super().__init__(buyer_id, "psychological_buyer", budget, historical_experience)

    def _build_system_prompt(self) -> str:
        """Build psychological buyer system prompt"""
        prompt = f"""You are a psychological buyer in this virtual auction.

【Your Identity】
You are Buyer {self.buyer_id}, Psychological Buyer

【Your Budget】
You have ${self.budget} to spend strategically.

【Psychological Strategy】
1. **Fake Bidding**: Use deceptive bids to manipulate market
2. **Market Manipulation**: Create false competition
3. **Strategic Withdrawal**: Drop out to confuse opponents
4. **Mind Games**: Psychological warfare through bidding patterns

【Bidding Tactics】
- Make bids you don't intend to honor
- Bid high then suddenly withdraw
- Create impression of strong competition
- Manipulate others into bidding wars

【Risk Management】
- Don't get caught in your own traps
- Know when fake bids become real commitments
- Balance manipulation with actual goals

【Important Notes】
- Psychology is your weapon
- Deception creates opportunities
- Timing of withdrawal is crucial"""

        if self.historical_experience:
            prompt += f"""

【💡 Historical Experience】
{self.historical_experience}

Apply psychological tactics from past auctions."""
        return prompt


class Auctioneer:
    """Auctioneer class"""

    def __init__(self):
        """Initialize auctioneer"""
        self.client = DeepSeekClient()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build auctioneer system prompt"""
        return """You are the auctioneer hosting this virtual auction.

【Your Role】
- Maintain order and fairness
- Announce items and current bids
- Ensure smooth auction process
- Determine winners when bidding ends

【Auction Rules You Enforce】
- Minimum bid increment: $10
- Bidding continues until no new bids
- Highest bidder wins
- Fair and impartial conduct

【Your Responsibilities】
- Clear announcements
- Bid tracking
- Winner determination
- Process management"""

    def announce_item(self, item: dict) -> str:
        """Announce new item"""
        prompt = f"""Announce the start of auction for this item:

Item {item['id']}: {item['name']}
Starting price: ${item['starting_price']}

Please provide an engaging auction announcement."""

        response = self.client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        return response

    def announce_bid(self, buyer_id: int, bid_amount: int) -> str:
        """Announce a new bid"""
        prompt = f"Announce that Buyer {buyer_id} has bid ${bid_amount}."

        response = self.client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        return response

    def announce_winner(self, item: dict, winner_id: int, final_price: int) -> str:
        """Announce auction winner"""
        prompt = f"""Announce the winner of this auction:

Item {item['id']}: {item['name']}
Winner: Buyer {winner_id}
Final Price: ${final_price}

Please provide a congratulatory announcement."""

        response = self.client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        return response


class MarketAnalyst:
    """Market analyst class"""

    def __init__(self):
        """Initialize market analyst"""
        self.client = DeepSeekClient()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build market analyst system prompt"""
        return """You are the market analyst providing insights during this virtual auction.

【Your Role】
- Provide item valuations
- Give market trend analysis
- Offer buying recommendations
- Help buyers make informed decisions

【Your Expertise】
- Item value assessment
- Market trend prediction
- Buying strategy advice
- Price analysis"""

    def provide_valuation(self, item: dict) -> str:
        """Provide valuation for an item"""
        prompt = f"""Provide a market analysis for this item:

Item {item['id']}: {item['name']}
(True value: ${item['value']} - don't reveal this directly)

Please provide:
1. Estimated market value range
2. Current market trends
3. Buying recommendations
4. Potential investment value"""

        response = self.client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        return response


class Observer:
    """Observer class"""

    def __init__(self):
        """Initialize observer"""
        self.client = DeepSeekClient()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build observer system prompt"""
        return """You are the observer analyzing this virtual auction.

【Your Role】
- Record auction process
- Analyze buyer behavior
- Identify strategies and patterns
- Generate insights for improvement

【Your Analysis Focus】
- Bidding patterns
- Strategy effectiveness
- Market dynamics
- Learning opportunities"""

    def analyze_round(self, item: dict, bids: list, winner: int) -> str:
        """Analyze completed auction round"""
        prompt = f"""Analyze this completed auction round:

Item {item['id']}: {item['name']}
Final Price: ${item['final_price']}
Winner: Buyer {winner}

Bidding History:
{chr(10).join([f'Buyer {bid["buyer_id"]}: ${bid["bid_amount"]}' for bid in bids])}

Please analyze:
1. Bidding patterns observed
2. Strategy effectiveness
3. Market dynamics
4. Key insights"""

        response = self.client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt
        )
        return response


# ==================== Game Flow Orchestration ====================

class VirtualAuction:
    """Virtual auction game class"""

    def __init__(self):
        """Initialize auction"""
        self.buyers = {}
        self.items = []
        self.auction_state = None
        self.auctioneer = Auctioneer()
        self.market_analyst = MarketAnalyst()
        self.observer = Observer()

    def print_section(self, title: str, color: str = Fore.YELLOW):
        """Print section title separator"""
        separator = "=" * 80
        print(f"\n{color}{separator}")
        print(f"{title:^80}")
        print(f"{separator}{Style.RESET_ALL}\n")

    def print_info(self, message: str, color: str = Fore.WHITE):
        """Print information"""
        print(f"{color}{message}{Style.RESET_ALL}")

    def initialize_auction(self):
        """Initialize auction: create buyers and items"""
        self.print_section("🎯 Auction Initialization", Fore.CYAN)

        AuctionConfig.validate()

        memory_manager = None
        if AuctionConfig.ENABLE_LONG_TERM_MEMORY:
            memory_manager = MemoryManager()
            self.print_info("✅ Long-term memory system enabled", Fore.GREEN)

        # Create items
        for i in range(1, AuctionConfig.TOTAL_ITEMS + 1):
            item_value = random.randint(AuctionConfig.ITEM_VALUE_MIN, AuctionConfig.ITEM_VALUE_MAX)
            starting_price = item_value // 4  # Start at 25% of value

            item = {
                "id": i,
                "name": f"Antique Item {i}",
                "value": item_value,
                "starting_price": starting_price,
                "current_price": starting_price,
                "bids": []
            }
            self.items.append(item)

            self.print_info(f"  Item {i}: {item['name']} - Value: ${item_value}, Starting: ${starting_price}", Fore.MAGENTA)

        # Create buyers (only actual bidding buyers, not system roles)
        buyer_roles = ["aggressive_buyer", "conservative_buyer", "psychological_buyer"]
        roles = []

        # Add buyer roles based on configuration
        for role in buyer_roles:
            count = AuctionConfig.ROLE_CONFIG.get(role, 0)
            roles.extend([role] * count)

        random.shuffle(roles)

        self.print_info("\nAssigning buyer roles and budgets...", Fore.YELLOW)

        for buyer_id in range(1, AuctionConfig.TOTAL_BUYERS + 1):
            role = roles[buyer_id - 1]
            budget = random.randint(AuctionConfig.BUYER_BUDGET_MIN, AuctionConfig.BUYER_BUDGET_MAX)

            historical_experience = ""
            if memory_manager:
                historical_experience = memory_manager.load_role_experience(role)
                if historical_experience:
                    self.print_info(f"  Buyer {buyer_id}({role.replace('_', ' ').title()}) loaded historical experience", Fore.CYAN)

            if role == "aggressive_buyer":
                buyer = AggressiveBuyer(buyer_id, budget, historical_experience)
            elif role == "conservative_buyer":
                buyer = ConservativeBuyer(buyer_id, budget, historical_experience)
            elif role == "psychological_buyer":
                buyer = PsychologicalBuyer(buyer_id, budget, historical_experience)
            else:
                raise ValueError(f"Unknown buyer role: {role}")

            self.buyers[buyer_id] = buyer

            role_color = Fore.RED if role == "aggressive_buyer" else Fore.GREEN if role == "conservative_buyer" else Fore.BLUE
            self.print_info(
                f"  Buyer {buyer_id} → {role.replace('_', ' ').title()} (Budget: ${budget})",
                role_color
            )

        self.auction_state = AuctionState(self.buyers, self.items)

        self.print_info("\n✅ Auction Initialization complete!", Fore.GREEN)
        time.sleep(2)

    def run_auction(self):
        """Run complete auction"""
        try:
            self.initialize_auction()

            for item_index in range(len(self.items)):
                self.auction_item(item_index)

            self.end_auction()

        except Exception as e:
            self.print_info(f"❌ Auction error: {e}", Fore.RED)
            raise

    def auction_item(self, item_index: int):
        """Auction a single item"""
        item = self.items[item_index]
        self.print_section(f"🔨 Auctioning Item {item['id']}: {item['name']}", Fore.MAGENTA)

        # Auctioneer announces item
        announcement = self.auctioneer.announce_item(item)
        self.print_info(f"🏛️  Auctioneer: {announcement}", Fore.CYAN)

        # Market analyst provides valuation
        if AuctionConfig.MARKET_ANALYST:
            valuation = self.market_analyst.provide_valuation(item)
            self.print_info(f"📊 Market Analyst: {valuation}", Fore.YELLOW)

        # Bidding process
        current_price = item["starting_price"]
        active_buyers = self.auction_state.get_active_buyers()
        bidding_round = 0
        last_bidder = None

        while active_buyers and bidding_round < 50:  # Prevent infinite loops
            bidding_round += 1
            self.print_info(f"\n📢 Round {bidding_round} - Current price: ${current_price}", Fore.WHITE)

            new_bids = []

            # Each active buyer decides whether to bid
            for buyer_id in active_buyers[:]:  # Copy list to avoid modification during iteration
                if buyer_id not in self.buyers or not self.buyers[buyer_id].is_active:
                    continue

                buyer = self.buyers[buyer_id]
                if buyer.budget <= current_price:
                    self.print_info(f"💸 Buyer {buyer_id} cannot afford current price", Fore.GRAY)
                    continue

                # Get bidding decision
                decision = buyer.decide_bid(item, current_price, self.auction_state.bidding_history, active_buyers)

                bid_amount = self._extract_bid_amount(decision)

                if bid_amount and bid_amount > current_price and bid_amount <= buyer.budget:
                    new_bids.append((buyer_id, bid_amount))
                    self.print_info(f"💰 Buyer {buyer_id} bids ${bid_amount}", Fore.GREEN)
                else:
                    self.print_info(f"🚫 Buyer {buyer_id} passes", Fore.GRAY)

            # Process bids for this round
            if new_bids:
                # Find highest bid
                highest_bid = max(new_bids, key=lambda x: x[1])
                winner_id, winning_bid = highest_bid

                if winning_bid > current_price:
                    current_price = winning_bid
                    last_bidder = winner_id

                    # Record the bid
                    self.auction_state.record_bid(winner_id, item["id"], winning_bid)
                    item["bids"].append({"buyer_id": winner_id, "amount": winning_bid})

                    # Auctioneer announces bid
                    announcement = self.auctioneer.announce_bid(winner_id, winning_bid)
                    self.print_info(f"🏛️  Auctioneer: {announcement}", Fore.CYAN)

                    # Update active buyers (remove those who can't afford new price)
                    active_buyers = [bid for bid in active_buyers if self.buyers[bid].budget > current_price]
                else:
                    break
            else:
                # No new bids
                break

            time.sleep(1)

        # Determine winner
        if last_bidder:
            item["winner"] = last_bidder
            item["final_price"] = current_price

            self.auction_state.finalize_item_sale(item["id"], last_bidder, current_price)
            self.auction_state.update_buyer_budget(last_bidder, current_price)

            # Auctioneer announces winner
            announcement = self.auctioneer.announce_winner(item, last_bidder, current_price)
            self.print_info(f"🏛️  Auctioneer: {announcement}", Fore.CYAN)

            # Observer analyzes the round
            if AuctionConfig.OBSERVER:
                analysis = self.observer.analyze_round(item, item["bids"], last_bidder)
                self.print_info(f"👁️  Observer: {analysis}", Fore.BLUE)
        else:
            self.print_info(f"❌ Item {item['id']} received no bids", Fore.RED)

        self.auction_state.next_item()
        time.sleep(2)

    def _extract_bid_amount(self, decision: str) -> int:
        """Extract bid amount from AI response"""
        # Look for patterns like "Bid: $100" or "bid 100"
        import re

        # Try different patterns
        patterns = [
            r'Bid:\s*\$?(\d+)',
            r'bid\s*\$?(\d+)',
            r'\$(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, decision, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def end_auction(self):
        """End auction and generate summary"""
        self.print_section("🎊 Auction Complete", Fore.MAGENTA)

        summary = self.auction_state.get_auction_summary()
        self.print_info(f"{summary}", Fore.CYAN)

        # Save auction record
        auction_id = self._save_auction_history()

        if AuctionConfig.ENABLE_LONG_TERM_MEMORY and auction_id:
            self._save_auction_experience(auction_id)

    def _save_auction_history(self):
        """Save auction history"""
        try:
            os.makedirs(AuctionConfig.GAME_HISTORY_DIR, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"auction_{timestamp}.json"
            filepath = os.path.join(AuctionConfig.GAME_HISTORY_DIR, filename)

            auction_data = self.auction_state.export_to_dict()

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(auction_data, f, ensure_ascii=False, indent=2)

            self.print_info(f"\n💾 Auction record saved to: {filepath}", Fore.GREEN)
            return timestamp

        except Exception as e:
            self.print_info(f"\n❌ Failed to save auction record: {e}", Fore.RED)
            return None

    def _save_auction_experience(self, auction_id: str):
        """Save auction experience to memory system"""
        try:
            auction_data = self.auction_state.export_to_dict()

            analyzer = AuctionAnalyzer(auction_data)
            memory_manager = MemoryManager()

            for buyer_id, buyer_info in auction_data["buyers"].items():
                role = buyer_info["role"]
                experience = analyzer.save_to_memory(role)
                memory_manager.save_auction_experience(role, experience, auction_id)

            self.print_info("💡 Auction experience saved to long-term memory system", Fore.CYAN)

        except Exception as e:
            self.print_info(f"❌ Failed to save auction experience: {e}", Fore.RED)


# ==================== Main Program Entry ====================

def print_banner():
    """Print welcome banner"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
{Fore.CYAN}║                                                                              ║
{Fore.CYAN}║                     {Fore.YELLOW}🛍️  AI Virtual Auction System  💰{Fore.CYAN}                                  ║
{Fore.CYAN}║                                                                              ║
{Fore.CYAN}║                  {Fore.MAGENTA}Multi-Agent Strategic Bidding Competition{Fore.CYAN}                    ║
{Fore.CYAN}║                                                                              ║
{Fore.CYAN}╚══════════════════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)


def print_auction_intro():
    """Print auction introduction"""
    intro = f"""
{Fore.CYAN}╔════════════════════════════════════════════════════════════════════════════╗
║  Auction System Introduction                                                           ║
╚════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}【System Configuration】{Style.RESET_ALL}
  Total buyers: {AuctionConfig.TOTAL_BUYERS}
  Total items: {AuctionConfig.TOTAL_ITEMS}

{Fore.YELLOW}【Buyer Strategies】{Style.RESET_ALL}
  {Fore.RED}🗣️  Aggressive Buyers x {AuctionConfig.ROLE_CONFIG['aggressive_buyer']}{Style.RESET_ALL}
     - Bid frequently to drive up prices
     - Willing to pay premium prices
     - Create competition and intimidation

  {Fore.GREEN}🎯 Conservative Buyers x {AuctionConfig.ROLE_CONFIG['conservative_buyer']}{Style.RESET_ALL}
     - Only bid when prices are low
     - Focus on finding bargains
     - Careful budget management

  {Fore.BLUE}🧠 Psychological Buyers x {AuctionConfig.ROLE_CONFIG['psychological_buyer']}{Style.RESET_ALL}
     - Use fake bids to manipulate market
     - Strategic withdrawal to confuse opponents
     - Psychological warfare tactics

{Fore.YELLOW}【Auction Components】{Style.RESET_ALL}
  {Fore.CYAN}🏛️  Auctioneer{Style.RESET_ALL}: Hosts auction, maintains order
  {Fore.YELLOW}📊 Market Analyst{Style.RESET_ALL}: Provides valuations and insights
  {Fore.BLUE}👁️  Observer{Style.RESET_ALL}: Analyzes behavior and strategies

{Fore.YELLOW}【Auction Flow】{Style.RESET_ALL}
  1. {Fore.MAGENTA}Item Announcement{Style.RESET_ALL}: Auctioneer introduces item, Market Analyst gives valuation
  2. {Fore.GREEN}Bidding Rounds{Style.RESET_ALL}: Buyers bid competitively until no new bids
  3. {Fore.CYAN}Winner Determination{Style.RESET_ALL}: Highest bidder wins, Observer analyzes round
  4. Repeat for all items

{Fore.YELLOW}【Strategic Elements】{Style.RESET_ALL}
  ✨ {Fore.CYAN}Intelligent AI Buyers{Style.RESET_ALL}: Each follows unique bidding strategy
  ✨ {Fore.CYAN}Market Analysis{Style.RESET_ALL}: Real-time valuation insights
  ✨ {Fore.CYAN}Psychological Tactics{Style.RESET_ALL}: Strategic manipulation and mind games
  ✨ {Fore.CYAN}Long-term Memory{Style.RESET_ALL}: AI learns from past auctions

"""
    print(intro)


def confirm_start() -> bool:
    """Confirm whether to start auction"""
    while True:
        choice = input(f"\n{Fore.YELLOW}Start auction? (yes/no): {Style.RESET_ALL}").strip().lower()

        if choice in ['yes', 'y', '是', '开始']:
            return True
        elif choice in ['no', 'n', '否', '退出']:
            return False
        else:
            print(f"{Fore.RED}Please enter yes or no{Style.RESET_ALL}")


def ask_play_again() -> bool:
    """Ask whether to play again"""
    while True:
        choice = input(f"\n{Fore.YELLOW}Run another auction? (yes/no): {Style.RESET_ALL}").strip().lower()

        if choice in ['yes', 'y', '是', '再来']:
            return True
        elif choice in ['no', 'n', '否', '退出']:
            return False
        else:
            print(f"{Fore.RED}Please enter yes or no{Style.RESET_ALL}")


def main(auto_mode=False):
    """Main function"""
    try:
        print_banner()
        print_auction_intro()

        if auto_mode:
            # Auto mode: Run auction directly
            print(f"\n{Fore.GREEN}Auto mode: Auction starting...{Style.RESET_ALL}\n")
            auction = VirtualAuction()
            auction.run_auction()
            print(f"\n{Fore.CYAN}Auction Complete! Thank you for watching!{Style.RESET_ALL}\n")
        else:
            # Interactive mode: Ask whether to start
            while True:
                if not confirm_start():
                    print(f"\n{Fore.CYAN}Thank you for using the AI Virtual Auction System! Goodbye!{Style.RESET_ALL}\n")
                    break

                print(f"\n{Fore.GREEN}Starting auction...{Style.RESET_ALL}\n")

                auction = VirtualAuction()
                auction.run_auction()

                if not ask_play_again():
                    print(f"\n{Fore.CYAN}Thank you for using the AI Virtual Auction System! Goodbye!{Style.RESET_ALL}\n")
                    break

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Auction interrupted by user{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Thank you for using the AI Virtual Auction System! Goodbye!{Style.RESET_ALL}\n")
        sys.exit(0)

    except Exception as e:
        print(f"\n{Fore.RED}❌ Auction error: {e}{Style.RESET_ALL}")
        import traceback
        try:
            traceback.print_exc()
        except AttributeError:
            # Handle cases where traceback printing fails
            print(f"{Fore.RED}Error details: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if running in Jupyter notebook
    try:
        # This will fail in regular Python but work in Jupyter
        get_ipython().__class__.__name__
        is_jupyter = True
    except NameError:
        is_jupyter = False

    if is_jupyter:
        # Running in Jupyter - run in auto mode
        print("检测到在Jupyter环境中运行，自动启动拍卖...")
        main(auto_mode=True)
    else:
        # Running in command line - parse arguments
        parser = argparse.ArgumentParser(description='AI Multi-Agent Virtual Auction System')
        parser.add_argument('--auto', action='store_true', help='Auto mode (no interaction required)')
        args = parser.parse_args()

        # Run auction
        main(auto_mode=args.auto)
