import json
import os
from web3 import Web3

GANACHE_URL = "http://127.0.0.1:7545"

def get_contract():
    # 1. Connect
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Ganache")

    # 2. Path Setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(current_dir)
    blockchain_path = os.path.join(base_path, "blockchain")

    # 3. Load Files
    try:
        with open(os.path.join(blockchain_path, "address.txt"), "r") as f:
            address = f.read().strip()
        
        with open(os.path.join(blockchain_path, "abi.json"), "r") as f:
            abi = json.load(f)
    except FileNotFoundError:
        print("❌ Critical Error: address.txt or abi.json missing in blockchain folder.")
        return None, None

    # 4. Return Contract
    contract = w3.eth.contract(address=address, abi=abi)
    return w3, contract