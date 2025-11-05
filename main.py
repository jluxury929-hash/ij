FastAPI Backend

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
import os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Environment variables
ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "")
PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY", "")
TOKEN_ADDRESS = os.getenv("REWARD_TOKEN_ADDRESS", "0x8502496d6739dd6e18ced318c4b5fc12a5fb2c2c")

# Web3 setup
w3 = None
admin_account = None

if ALCHEMY_KEY:
    w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"))
    if PRIVATE_KEY and w3.is_connected():
        admin_account = w3.eth.account.from_key(PRIVATE_KEY)

# Token ABI
TOKEN_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "mint",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# 10X Earning strategies
STRATEGIES = {
    "aave_lending": {"apy": 0.85, "weight": 0.15},
    "compound": {"apy": 0.78, "weight": 0.12},
    "uniswap_v3": {"apy": 2.45, "weight": 0.18},
    "curve_stable": {"apy": 1.25, "weight": 0.10},
    "yearn_vaults": {"apy": 1.98, "weight": 0.15},
    "convex": {"apy": 3.12, "weight": 0.10},
    "balancer": {"apy": 1.67, "weight": 0.08},
    "sushiswap": {"apy": 2.89, "weight": 0.05},
    "mev_arb": {"apy": 4.25, "weight": 0.03},
    "flashloan": {"apy": 5.12, "weight": 0.02},
    "governance": {"apy": 0.95, "weight": 0.01},
    "staking": {"apy": 1.42, "weight": 0.01}
}

AI_BOOST = 2.5
user_sessions = {}

class EngineRequest(BaseModel):
    walletAddress: str
    miningContract: str
    yieldAggregator: str
    strategies: list

def calculate_earnings(principal, seconds):
    total_apy = sum(s["apy"] * s["weight"] for s in STRATEGIES.values()) * AI_BOOST
    rate = total_apy / (365 * 24 * 3600)
    return principal * rate * seconds, total_apy

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "10X Hyper Earning Backend",
        "version": "10.0.0",
        "strategies": len(STRATEGIES),
        "ai_boost": AI_BOOST,
        "web3_ready": w3 is not None and w3.is_connected() if w3 else False
    }

@app.get("/health")
def health():
    return {"status": "healthy", "time": datetime.now().isoformat()}

@app.post("/api/engine/start")
def start_engine(req: EngineRequest):
    wallet = req.walletAddress.lower()
    user_sessions[wallet] = {
        "start": datetime.now().timestamp(),
        "earned": 0.0,
        "last_mint": datetime.now().timestamp()
    }
    return {
        "success": True,
        "message": "Engine started",
        "boost": AI_BOOST
    }

@app.get("/api/engine/metrics")
def get_metrics(x_wallet_address: str = Header(None)):
    if not x_wallet_address:
        raise HTTPException(400, "Wallet header required")
    
    wallet = x_wallet_address.lower()
    
    if wallet not in user_sessions:
        user_sessions[wallet] = {
            "start": datetime.now().timestamp(),
            "earned": 0.0,
            "last_mint": datetime.now().timestamp()
        }
    
    session = user_sessions[wallet]
    now = datetime.now().timestamp()
    running = now - session["start"]
    since_mint = now - session["last_mint"]
    
    principal = 100000.0
    earnings, apy = calculate_earnings(principal, running)
    session["earned"] += earnings
    
    # Mint every 5 seconds
    if since_mint >= 5 and w3 and admin_account:
        try:
            mint_tokens(wallet, session["earned"])
            session["last_mint"] = now
            session["earned"] = 0
        except Exception as e:
            print(f"Mint error: {e}")
    
    hourly = (earnings / running * 3600) if running > 0 else 0
    
    return {
        "totalProfit": session["earned"],
        "hourlyRate": hourly,
        "dailyProfit": hourly * 24,
        "activePositions": len(STRATEGIES),
        "pendingRewards": session["earned"] * 0.1,
        "total_apy": f"{apy * 100:.2f}%"
    }

def mint_tokens(wallet, amount):
    if not w3 or not admin_account:
        return
    
    try:
        token_amount = int(amount * 10**18)
        if token_amount <= 0:
            return
        
        print(f"\nMINTING {amount:.4f} tokens to {wallet}")
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(TOKEN_ADDRESS),
            abi=TOKEN_ABI
        )
        
        gas_price = int(w3.eth.gas_price * 1.2)
        nonce = w3.eth.get_transaction_count(admin_account.address)
        
        tx = contract.functions.mint(
            Web3.to_checksum_address(wallet),
            token_amount
        ).build_transaction({
            'from': admin_account.address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': gas_price,
            'chainId': w3.eth.chain_id
        })
        
        signed = admin_account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        print(f"TX: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt['status'] == 1:
            print(f"✅ CONFIRMED - Block {receipt['blockNumber']}")
            print(f"https://etherscan.io/tx/{tx_hash.hex()}")
        else:
            print(f"❌ FAILED")
        
        return tx_hash.hex()
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.post("/api/engine/stop")
def stop_engine(req: dict):
    wallet = req.get("walletAddress", "").lower()
    if wallet in user_sessions:
        del user_sessions[wallet]
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
