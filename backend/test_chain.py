import json
import os
from web3 import Web3

# 1. Connect to Ganache
ganache_url = "http://127.0.0.1:7545"
w3 = Web3(Web3.HTTPProvider(ganache_url))

# Check connection
if w3.is_connected():
    print("✅ Python is connected to Ganache!")
else:
    print("❌ Failed to connect to Ganache.")
    exit()

# 2. Load the Contract Address and ABI
# We go UP one level from 'backend' to the project root, then DOWN into 'blockchain'
current_dir = os.path.dirname(os.path.abspath(__file__))
base_path = os.path.dirname(current_dir)
blockchain_path = os.path.join(base_path, "blockchain")

print(f"📂 Looking for files in: {blockchain_path}")

try:
    with open(os.path.join(blockchain_path, "address.txt"), "r") as f:
        contract_address = f.read().strip()
    
    with open(os.path.join(blockchain_path, "abi.json"), "r") as f:
        contract_abi = json.load(f)
        
    print(f"📍 Loaded Contract Address: {contract_address}")
except FileNotFoundError:
    print("❌ Error: Could not find address.txt or abi.json in the blockchain folder.")
    print("👉 Please make sure you saved them in: " + blockchain_path)
    exit()

# 3. Create the Contract Object
try:
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    
    # 4. Test a Call (Read Data)
    name = contract.functions.name().call()
    symbol = contract.functions.symbol().call()
    print(f"🎉 Success! The Contract is: {name} ({symbol})")

except Exception as e:
    print(f"❌ Error calling contract: {e}")