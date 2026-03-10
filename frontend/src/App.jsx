import React, { useState } from 'react';
import WalletConnect from './components/WalletConnect';
import Vault from './components/Vault';
import UploadDashboard from './components/UploadDashboard'; 
import SendSecret from './components/SendSecret';

import './index.css';

const App = () => {
    const [walletAddress, setWalletAddress] = useState("");
    const [activeTab, setActiveTab] = useState("vault"); // 'upload', 'vault', 'send'

    if (!walletAddress) {
        return <WalletConnect setWallet={setWalletAddress} />;
    }

    return (
        <div className="dashboard-container">
            {/* Sidebar Navigation */}
            <aside className="sidebar glass-card">
                <div className="sidebar-header">
                    <h2>🛡️ Privacy Shield</h2>
                    <p className="wallet-badge" 
                       onClick={() => navigator.clipboard.writeText(walletAddress)}
                       style={{ cursor: "pointer", title: "Click to copy address" }}>
                        {walletAddress.substring(0, 6)}...{walletAddress.substring(38)} 📋
                    </p>
                </div>
                
                <nav className="sidebar-nav">
                    <button 
                        className={`nav-btn ${activeTab === 'upload' ? 'active' : ''}`}
                        onClick={() => setActiveTab('upload')}
                    >
                        📤 Secure Upload
                    </button>
                    <button 
                        className={`nav-btn ${activeTab === 'vault' ? 'active' : ''}`}
                        onClick={() => setActiveTab('vault')}
                    >
                        🗄️ My Vault (S3)
                    </button>
                    <button 
                        className={`nav-btn ${activeTab === 'send' ? 'active' : ''}`}
                        onClick={() => setActiveTab('send')}
                    >
                        🕵️ Send Secret (Stego)
                    </button>
                </nav>
            </aside>

            {/* Main Content Area */}
            <main className="main-content">
                {activeTab === 'vault' && <Vault walletAddress={walletAddress} />}
                {activeTab === 'upload' && <UploadDashboard walletAddress={walletAddress} />}
                {activeTab === 'send' && <SendSecret walletAddress={walletAddress} />}
            </main>
        </div>
    );
};

export default App;