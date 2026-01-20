"""
Finance Dashboard View for Echo V3
Renders account balances, transactions, and spending analytics with cyberpunk aesthetics
"""

async def render_finance_view():
    """Render finance dashboard with WYGIWYH data"""
    try:
        import wygiwyh_client
        
        # Fetch data from WYGIWYH
        accounts = await wygiwyh_client._wygiwyh_client.get_accounts()
        transactions_raw = await wygiwyh_client._wygiwyh_client.get_transactions(limit=10)
        
        # Calculate totals by currency
        balance_by_currency = {}
        for account in accounts:
            currency = account.get("currency", {}).get("code", "USD")
            balance = account.get("balance", 0)
            if currency not in balance_by_currency:
                balance_by_currency[currency] = 0
            balance_by_currency[currency] += balance
        
        # Render account cards
        account_cards = ""
        for account in accounts:
            name = account.get("name", "Unknown")
            balance = account.get("balance", 0)
            currency = account.get("currency", {}).get("code", "USD")
            color = account.get("color", "purple")
            
            # Map color to neon variant
            neon_map = {
                "purple": "--neon-purple",
                "blue": "--neon-blue",
                "pink": "--neon-pink",
                "yellow": "--neon-yellow"
            }
            neon_color = neon_map.get(color.lower(), "--neon-purple")
            
            account_cards += f'''
                <div class="finance-account-card" style="border-color: var({neon_color});">
                    <div class="account-name">{name}</div>
                    <div class="account-balance">{balance:,.2f} <span class="currency">{currency}</span></div>
                    <div class="account-glow" style="background: var({neon_color}); opacity: 0.1;"></div>
                </div>
            '''
        
        # Render transactions
        transaction_rows = ""
        for tx in transactions_raw[:10]:
            date = tx.get("date", "")
            amount = tx.get("amount", 0)
            currency = tx.get("currency", {}).get("code", "USD")
            description = tx.get("description", "No description")
            category = tx.get("category", {}).get("name", "Uncategorized")
            
            # Color code by type
            amount_class = "income" if amount >= 0 else "expense"
            sign = "+" if amount >= 0 else "-"
            
            transaction_rows += f'''
                <div class="transaction-row {amount_class}">
                    <div class="tx-date">{date}</div>
                    <div class="tx-desc">
                        <div class="tx-description">{description}</div>
                        <div class="tx-category">{category}</div>
                    </div>
                    <div class="tx-amount">{sign}{abs(amount):,.2f} {currency}</div>
                </div>
            '''
        
        # Calculate spending summary
        total_income = sum(tx.get("amount", 0) for tx in transactions_raw if tx.get("amount", 0) >= 0)
        total_expenses = sum(abs(tx.get("amount", 0)) for tx in transactions_raw if tx.get("amount", 0) < 0)
        net = total_income - total_expenses
        
        return f'''
            <style>
                .finance-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }}
                
                .finance-account-card {{
                    background: var(--glass);
                    border: 1px solid var(--glass-border);
                    border-radius: 16px;
                    padding: 1.5rem;
                    position: relative;
                    overflow: hidden;
                    backdrop-filter: blur(20px);
                    transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
                }}
                
                .finance-account-card:hover {{
                    transform: translateY(-4px);
                    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
                }}
                
                .account-name {{
                    font-family: 'Orbitron', sans-serif;
                    font-size: 0.9rem;
                    color: var(--text-dim);
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    margin-bottom: 0.5rem;
                }}
                
                .account-balance {{
                    font-size: 2.2rem;
                    font-weight: 700;
                    color: #fff;
                    margin-bottom: 0.5rem;
                }}
                
                .currency {{
                    font-size: 1.2rem;
                    color: var(--text-dim);
                    font-weight: 400;
                }}
                
                .account-glow {{
                    position: absolute;
                    bottom: 0;
                    right: 0;
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    filter: blur(40px);
                    pointer-events: none;
                }}
                
                .finance-section {{
                    background: var(--glass);
                    border: 1px solid var(--glass-border);
                    border-radius: 16px;
                    padding: 2rem;
                    margin-bottom: 2rem;
                    backdrop-filter: blur(20px);
                }}
                
                .section-title {{
                    font-family: 'Orbitron', sans-serif;
                    font-size: 1.4rem;
                    color: var(--neon-blue);
                    margin-bottom: 1.5rem;
                    letter-spacing: 2px;
                    text-transform: uppercase;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }}
                
                .section-title::before {{
                    content: '';
                    width: 4px;
                    height: 24px;
                    background: var(--neon-blue);
                    box-shadow: 0 0 10px var(--neon-blue);
                }}
                
                .transaction-row {{
                    display: grid;
                    grid-template-columns: 100px 1fr 150px;
                    gap: 1rem;
                    padding: 1rem;
                    border-bottom: 1px solid var(--glass-border);
                    transition: background 0.2s ease;
                    align-items: center;
                }}
                
                .transaction-row:hover {{
                    background: rgba(255,255,255,0.03);
                }}
                
                .tx-date {{
                    font-family: 'Rajdhani', monospace;
                    color: var(--text-dim);
                    font-size: 0.9rem;
                }}
                
                .tx-desc {{
                    display: flex;
                    flex-direction: column;
                    gap: 0.3rem;
                }}
                
                .tx-description {{
                    color: var(--text-main);
                    font-weight: 500;
                }}
                
                .tx-category {{
                    color: var(--text-dim);
                    font-size: 0.85rem;
                    font-style: italic;
                }}
                
                .tx-amount {{
                    text-align: right;
                    font-weight: 700;
                    font-size: 1.1rem;
                }}
                
                .transaction-row.income .tx-amount {{
                    color: #00ff88;
                    text-shadow: 0 0 10px rgba(0,255,136,0.3);
                }}
                
                .transaction-row.expense .tx-amount {{
                    color: var(--neon-pink);
                    text-shadow: 0 0 10px rgba(255,0,85,0.3);
                }}
                
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 1.5rem;
                    margin-top: 2rem;
                }}
                
                .summary-stat {{
                    text-align: center;
                    padding: 1.5rem;
                    background: rgba(0,0,0,0.3);
                    border-radius: 12px;
                    border: 1px solid var(--glass-border);
                }}
                
                .stat-label {{
                    font-size: 0.85rem;
                    color: var(--text-dim);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 0.5rem;
                }}
                
                .stat-value {{
                    font-size: 2rem;
                    font-weight: 700;
                    color: #fff;
                }}
                
                .stat-value.income {{
                    color: #00ff88;
                }}
                
                .stat-value.expense {{
                    color: var(--neon-pink);
                }}
                
                .stat-value.net {{
                    color: var(--neon-blue);
                }}
                
                @media (max-width: 768px) {{
                    .transaction-row {{
                        grid-template-columns: 1fr;
                        gap: 0.5rem;
                    }}
                    
                    .tx-amount {{
                        text-align: left;
                    }}
                    
                    .summary-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
            
            <div class="chat-header">
                <div>
                    <div class="chat-title">💰 Finance Dashboard</div>
                    <div class="chat-subtitle">Transaction Management & Analytics</div>
                </div>
            </div>
            
            <div class="page-container">
                <!-- Account Balances -->
                <div class="finance-grid">
                    {account_cards if account_cards else '<div style="color: var(--text-dim); padding: 2rem; text-align: center;">No accounts found. Configure WYGIWYH first.</div>'}
                </div>
                
                <!-- Recent Transactions -->
                <div class="finance-section">
                    <div class="section-title">📝 Recent Transactions</div>
                    {transaction_rows if transaction_rows else '<div style="color: var(--text-dim); padding: 1rem; text-align: center;">No transactions found.</div>'}
                </div>
                
                <!-- Summary Stats -->
                <div class="summary-grid">
                    <div class="summary-stat">
                        <div class="stat-label">Income</div>
                        <div class="stat-value income">+{total_income:,.2f}</div>
                    </div>
                    <div class="summary-stat">
                        <div class="stat-label">Expenses</div>
                        <div class="stat-value expense">-{total_expenses:,.2f}</div>
                    </div>
                    <div class="summary-stat">
                        <div class="stat-label">Net</div>
                        <div class="stat-value net">{"+" if net >= 0 else "-"}{abs(net):,.2f}</div>
                    </div>
                </div>
            </div>
        '''
        
    except Exception as e:
        return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title">💰 Finance Dashboard</div>
                    <div class="chat-subtitle">Transaction Management & Analytics</div>
                </div>
            </div>
            
            <div class="page-container">
                <div style="background: var(--glass); border: 1px solid var(--neon-pink); border-radius: 16px; padding: 2rem; text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                    <div style="color: var(--neon-pink); font-size: 1.2rem; margin-bottom: 0.5rem;">WYGIWYH Connection Failed</div>
                    <div style="color: var(--text-dim); margin-top: 1rem;">
                        Error: {str(e)}<br><br>
                        Make sure WYGIWYH is running and configured in your .env file:<br>
                        <code style="background: rgba(0,0,0,0.3); padding: 0.5rem; display: inline-block; margin-top: 0.5rem;border-radius: 8px;">
                            WYGIWYH_URL=http://localhost:8000<br>
                            WYGIWYH_API_TOKEN=your_token_here
                        </code>
                    </div>
                </div>
            </div>
        '''
