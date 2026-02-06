import React, { useState } from 'react';
import { ethers } from 'ethers';

const WalletConnect = ({ setWallet }) => {
    const [account, setAccount] = useState("");
    const [error, setError] = useState("");

    const connectWallet = async () => {
        // 1. Check if MetaMask is installed
        if (!window.ethereum) {
            setError("MetaMask is not installed! Please install it.");
            return;
        }

        try {
            // 2. Request account access
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();
            const address = await signer.getAddress();
            
            // 3. Save the address
            setAccount(address);
            setWallet(address); // Pass it up to the parent app
            setError("");
        } catch (err) {
            setError("Failed to connect wallet.");
            console.error(err);
        }
    };

    return (
        <div style={{ padding: "20px", border: "1px solid #ddd", borderRadius: "8px", marginBottom: "20px" }}>
            <h3>🔐 Member 3: Wallet Auth</h3>
            
            {!account ? (
                <button 
                    onClick={connectWallet}
                    style={{ padding: "10px 20px", cursor: "pointer", background: "#4CAF50", color: "white", border: "none", borderRadius: "5px" }}
                >
                    Connect MetaMask
                </button>
            ) : (
                <div>
                    <p style={{ color: "green", fontWeight: "bold" }}>✅ Connected</p>
                    <code style={{ background: "#eee", padding: "5px" }}>{account}</code>
                </div>
            )}
            
            {error && <p style={{ color: "red" }}>{error}</p>}
        </div>
    );
};

export default WalletConnect;