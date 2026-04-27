import json
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")

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
        print("[!] Critical Error: address.txt or abi.json missing in blockchain folder.")
        return None, None

    # 4. Return Contract
    contract = w3.eth.contract(address=address, abi=abi)
    return w3, contract

def mint_privacy_nft(wallet_address, encrypted_key, file_hash):
    w3, contract = get_contract()
    if not w3 or not contract:
        return None

    # 1. Get credentials from environment
    private_key = os.getenv("ADMIN_PRIVATE_KEY")
    admin_address = os.getenv("ADMIN_ADDRESS")

    if not private_key or not admin_address:
        print("[!] Error: ADMIN_PRIVATE_KEY or ADMIN_ADDRESS not set in .env")
        return None

    try:
        # 2. Get the nonce
        nonce = w3.eth.get_transaction_count(admin_address)
        chain_id = w3.eth.chain_id
        
        # 3. Build the Transaction
        transaction = contract.functions.safeMint(
            w3.to_checksum_address(wallet_address), 
            encrypted_key,
            file_hash
        ).build_transaction({
            'chainId': chain_id, # Can be overridden in production
            'gas': 2000000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
        })

        # 4. Sign the transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
        
        # 5. Send it
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        # 6. Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # 7. Extract TokenID from the Transfer event
        logs = contract.events.Transfer().process_receipt(receipt)
        token_id = logs[0]['args']['tokenId']
        
        print(f"[*] NFT Minted on-chain! ID: {token_id}")
        return token_id

    except Exception as e:
        print(f"[!] Production Minting Error: {e}")
        return None

def record_access_fire_and_forget(token_id, wallet_address):
    w3, contract = get_contract()
    if not w3 or not contract:
        return

    # 1. Get credentials from environment
    private_key = os.getenv("ADMIN_PRIVATE_KEY")
    admin_address = os.getenv("ADMIN_ADDRESS")

    if not private_key or not admin_address:
        print("❌ Error: ADMIN_PRIVATE_KEY or ADMIN_ADDRESS not set in .env")
        return

    try:
        # 2. Get the nonce
        nonce = w3.eth.get_transaction_count(admin_address)
        chain_id = w3.eth.chain_id
        
        # 3. Build the Transaction
        transaction = contract.functions.recordAccess(
            token_id,
            w3.to_checksum_address(wallet_address)
        ).build_transaction({
            'chainId': chain_id,
            'gas': 2000000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
        })

        # 4. Sign the transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
        
        # 5. Send it (Fire and forget, no wait_for_transaction_receipt)
        w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"[*] Audit log dispatched via background tx for token {token_id}")

    except Exception as e:
        print(f"[!] Async audit logging failed: {e}")