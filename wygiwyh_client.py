"""
WYGIWYH Finance Tracker Client
Interfaces with local WYGIWYH instance API for personal finance management.
All data stays local - no cloud services, no API keys needed.
"""
import os
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

WYGIWYH_URL = os.getenv("WYGIWYH_URL", "http://localhost:8000")


class WYGIWYHClient:
    def __init__(self):
        self.base_url = WYGIWYH_URL.rstrip("/")
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make async HTTP request to WYGIWYH API."""
        url = f"{self.base_url}/api{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    timeout=10.0,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            return {"error": f"WYGIWYH API error: {str(e)}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}
    
    async def get_accounts(self) -> List[Dict]:
        """Get all accounts."""
        result = await self._request("GET", "/accounts/")
        if "error" in result:
            return []
        return result.get("results", [])
    
    async def get_balance_summary(self, account_filter: Optional[str] = None) -> str:
        """Get formatted balance summary for all or specific account."""
        accounts = await self.get_accounts()
        
        if not accounts:
            if isinstance(accounts, dict) and "error" in accounts:
                return f"❌ {accounts['error']}"
            return "No accounts found. Set up WYGIWYH first at {}".format(self.base_url)
        
        # Filter by account name if specified
        if account_filter:
            accounts = [a for a in accounts if account_filter.lower() in a.get("name", "").lower()]
            if not accounts:
                return f"❌ No account matching '{account_filter}' found."
        
        lines = ["💰 **Account Balances**\n"]
        total_by_currency = {}
        
        for account in accounts:
            name = account.get("name", "Unknown")
            balance = account.get("balance", 0)
            currency = account.get("currency", {}).get("code", "USD")
            
            lines.append(f"  • **{name}**: {balance:,.2f} {currency}")
            
            # Track totals by currency
            if currency not in total_by_currency:
                total_by_currency[currency] = 0
            total_by_currency[currency] += balance
        
        # Add totals if multiple accounts
        if len(accounts) > 1:
            lines.append("\n**Totals:**")
            for currency, total in total_by_currency.items():
                lines.append(f"  • {total:,.2f} {currency}")
        
        return "\n".join(lines)
    
    async def get_transactions(self, limit: int = 10, category_filter: Optional[str] = None) -> List[Dict]:
        """Get recent transactions with optional category filter."""
        params = {"page_size": limit, "ordering": "-date"}
        
        if category_filter:
            # Get category ID by name
            categories = await self._request("GET", "/categories/")
            if not isinstance(categories, dict) or "error" in categories:
                return []
            
            category_list = categories.get("results", [])
            category_match = next(
                (c for c in category_list if category_filter.lower() in c.get("name", "").lower()),
                None
            )
            if category_match:
                params["category"] = category_match["id"]
        
        result = await self._request("GET", "/transactions/", params=params)
        if "error" in result:
            return []
        return result.get("results", [])
    
    async def get_recent_transactions(self, limit: int = 10, category: Optional[str] = None) -> str:
        """Get formatted list of recent transactions."""
        transactions = await self.get_transactions(limit, category)
        
        if not transactions:
            filter_text = f" in category '{category}'" if category else ""
            return f"No transactions found{filter_text}."
        
        lines = [f"📝 **Recent Transactions** (Last {limit})\n"]
        
        for tx in transactions:
            date = tx.get("date", "")
            amount = tx.get("amount", 0)
            currency = tx.get("currency", {}).get("code", "USD")
            description = tx.get("description", "No description")
            category_name = tx.get("category", {}).get("name", "Uncategorized")
            
            # Format amount with +/- sign
            sign = "+" if amount >= 0 else "-"
            amount_str = f"{sign}{abs(amount):,.2f} {currency}"
            
            lines.append(f"  • {date} | {amount_str} | {category_name}")
            lines.append(f"    _{description}_")
        
        return "\n".join(lines)
    
    async def create_transaction(self, amount: float, description: str, category_name: str, 
                                 account_name: Optional[str] = None, is_income: bool = False) -> str:
        """Create a new transaction (expense or income)."""
        # Get default account if not specified
        accounts = await self.get_accounts()
        if not accounts:
            return "❌ No accounts available. Create an account in WYGIWYH first."
        
        # Find matching account
        if account_name:
            account = next((a for a in accounts if account_name.lower() in a.get("name", "").lower()), None)
            if not account:
                return f"❌ Account '{account_name}' not found."
        else:
            account = accounts[0]  # Use first account as default
        
        # Get or create category
        categories = await self._request("GET", "/categories/")
        if "error" in categories:
            return f"❌ {categories['error']}"
        
        category_list = categories.get("results", [])
        category = next((c for c in category_list if category_name.lower() == c.get("name", "").lower()), None)
        
        if not category:
            # Create new category
            new_category = await self._request("POST", "/categories/", json={"name": category_name})
            if "error" in new_category:
                return f"❌ Failed to create category: {new_category['error']}"
            category = new_category
        
        # Create transaction
        # WYGIWYH uses negative amounts for expenses, positive for income
        final_amount = amount if is_income else -abs(amount)
        
        tx_data = {
            "amount": final_amount,
            "description": description,
            "category": category["id"],
            "account": account["id"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "currency": account.get("currency", {}).get("id")
        }
        
        result = await self._request("POST", "/transactions/", json=tx_data)
        if "error" in result:
            return f"❌ {result['error']}"
        
        type_str = "Income" if is_income else "Expense"
        return f"✅ {type_str} recorded: {abs(amount):,.2f} {account.get('currency', {}).get('code', 'USD')} - {description} ({category_name})"
    
    async def create_expense(self, amount: float, category: str, description: str, account: Optional[str] = None) -> str:
        """Create an expense transaction."""
        return await self.create_transaction(amount, description, category, account, is_income=False)
    
    async def create_income(self, amount: float, source: str, description: str, account: Optional[str] = None) -> str:
        """Create an income transaction."""
        return await self.create_transaction(amount, description, source, account, is_income=True)
    
    async def get_summary(self, period: str = "month") -> str:
        """Get financial summary for period (week, month, year)."""
        # Calculate date range
        now = datetime.now()
        if period == "week":
            start_date = now - timedelta(days=7)
        elif period == "year":
            start_date = now - timedelta(days=365)
        else:  # month
            start_date = now - timedelta(days=30)
        
        # Get transactions for period
        params = {
            "date_after": start_date.strftime("%Y-%m-%d"),
            "page_size": 1000  # Get all transactions in period
        }
        
        result = await self._request("GET", "/transactions/", params=params)
        if "error" in result:
            return f"❌ {result['error']}"
        
        transactions = result.get("results", [])
        
        if not transactions:
            return f"No transactions found in the last {period}."
        
        # Calculate totals by currency
        income_by_currency = {}
        expenses_by_currency = {}
        
        for tx in transactions:
            amount = tx.get("amount", 0)
            currency = tx.get("currency", {}).get("code", "USD")
            
            if amount >= 0:
                income_by_currency[currency] = income_by_currency.get(currency, 0) + amount
            else:
                expenses_by_currency[currency] = expenses_by_currency.get(currency, 0) + abs(amount)
        
        # Format summary
        period_title = period.capitalize()
        lines = [f"📊 **{period_title}ly Summary**\n"]
        
        all_currencies = set(income_by_currency.keys()) | set(expenses_by_currency.keys())
        
        for currency in sorted(all_currencies):
            income = income_by_currency.get(currency, 0)
            expenses = expenses_by_currency.get(currency, 0)
            net = income - expenses
            net_sign = "+" if net >= 0 else "-"
            
            lines.append(f"**{currency}:**")
            lines.append(f"  • Income: +{income:,.2f}")
            lines.append(f"  • Expenses: -{expenses:,.2f}")
            lines.append(f"  • Net: {net_sign}{abs(net):,.2f}\n")
        
        return "\n".join(lines)


# Global instance
_wygiwyh_client = WYGIWYHClient()


# Export convenience functions for llm_client.py
async def get_balance_summary(account_filter: Optional[str] = None) -> str:
    return await _wygiwyh_client.get_balance_summary(account_filter)


async def create_expense(amount: float, category: str, description: str, account: Optional[str] = None) -> str:
    return await _wygiwyh_client.create_expense(amount, category, description, account)


async def create_income(amount: float, source: str, description: str, account: Optional[str] = None) -> str:
    return await _wygiwyh_client.create_income(amount, source, description, account)


async def get_summary(period: str = "month") -> str:
    return await _wygiwyh_client.get_summary(period)


async def get_recent_transactions(limit: int = 10, category: Optional[str] = None) -> str:
    return await _wygiwyh_client.get_recent_transactions(limit, category)
