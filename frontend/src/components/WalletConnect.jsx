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
        <div className="glass-card">
            <h3>🔐 Wallet Authentication</h3>

            {!account ? (
                <div>
                    <p style={{ color: "var(--text-secondary)", marginBottom: "15px" }}>Connect your wallet to access secure image processing.</p>
                    <button
                        className="btn btn-primary"
                        onClick={connectWallet}
                    >
                        Connect MetaMask
                    </button>
                </div>
            ) : (
                <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                        <span style={{ color: "var(--success)" }}>●</span>
                        <span style={{ fontWeight: "500" }}>Connected securely</span>
                    </div>
                    <code>{account}</code>
                </div>
            )}

            {error && <p style={{ color: "var(--danger)", marginTop: "10px", fontSize: "0.9rem" }}>{error}</p>}
        </div>
    );
};

export default WalletConnect;