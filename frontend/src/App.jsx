import React, { useState, useEffect } from 'react';
import axios from 'axios';
import WalletConnect from './components/WalletConnect';
import ImageUpload from './components/ImageUpload'; // ✅ Imported correctly

function App() {
  const [walletAddress, setWalletAddress] = useState("");
  const [backendStatus, setBackendStatus] = useState("Checking...");

  // 1. Check Backend Health on Load
  useEffect(() => {
    axios.get("http://127.0.0.1:8000/chain-status")
      .then(res => {
        if (res.data.status === "connected") {
          setBackendStatus(`✅ Online (Contract: ${res.data.contract_name})`);
        } else {
          setBackendStatus("❌ Backend Error: " + res.data.details);
        }
      })
      .catch(err => setBackendStatus("❌ Offline (Is Python running?)"));
  }, []);

  return (
    <div style={{ fontFamily: "Arial, sans-serif", padding: "40px", maxWidth: "800px", margin: "0 auto" }}>
      <h1>🛡️ Smart Privacy Shield</h1>

      {/* Status Bar */}
      <div style={{ marginBottom: "20px", padding: "10px", background: "#f0f8ff", borderRadius: "5px" }}>
        <strong>Backend Status:</strong> {backendStatus}
      </div>

      {/* Wallet Component */}
      <WalletConnect setWallet={setWalletAddress} />

      {/* ✅ CHANGE IS HERE: We replaced the old <div>...</div> with the component */}
      {walletAddress && (
        <ImageUpload walletAddress={walletAddress} />
      )}
    </div>
  );
}

export default App;