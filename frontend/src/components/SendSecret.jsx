import React, { useState } from 'react';
import axios from '../api/axios';

const SendSecret = ({ walletAddress }) => {
    const [file, setFile] = useState(null);
    const [receiverAddress, setReceiverAddress] = useState("");
    const [status, setStatus] = useState("");
    const [uploading, setUploading] = useState(false);
    const [receipt, setReceipt] = useState(null);

    // Cover Image States
    const [coverOptions, setCoverOptions] = useState([]);
    const [selectedCover, setSelectedCover] = useState("default_cover.png");
    const [isCustomCover, setIsCustomCover] = useState(false); // Controls custom upload mode
    const [customCoverFile, setCustomCoverFile] = useState(null);

    // Fetch available covers from backend
    React.useEffect(() => {
        const fetchCovers = async () => {
            try {
                const res = await axios.get("/covers");
                setCoverOptions(res.data.covers || ["default_cover.png"]);
                if (res.data.covers && res.data.covers.length > 0) {
                    setSelectedCover(res.data.covers[0]);
                }
            } catch (err) {
                console.error("Failed to load covers", err);
            }
        };
        fetchCovers();
    }, []);

    const handleFileChange = (e) => {
        if (e.target.files) setFile(e.target.files[0]);
    };

    const handleSendSecret = async () => {
        if (!file || !receiverAddress) {
            setStatus("Please provide both a secret image and a receiver's wallet address.");
            return;
        }

        // Basic validation for an Ethereum address
        if (!/^0x[a-fA-F0-9]{40}$/.test(receiverAddress)) {
            setStatus("Invalid Ethereum wallet address format.");
            return;
        }

        setUploading(true);
        setStatus("Encrypting secret, embedding in cover, and airdropping NFT...");
        setReceipt(null);

        const formData = new FormData();
        formData.append("file", file);
        // TRICK: We pass the RECEIVER's address so the backend mints directly to them!
        formData.append("wallet_address", receiverAddress); 
        formData.append("is_stego_mode", "true");
        
        if (isCustomCover && customCoverFile) {
            formData.append("custom_cover", customCoverFile);
        } else {
            formData.append("cover_image_name", selectedCover);
        }

        try {
            const res = await axios.post("/process-image", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            if (res.data.status === "success") {
                setStatus("Secret sent successfully!");
                setReceipt({
                    coverUrl: res.data.display_url,
                    tokenId: res.data.token_id,
                    receiver: receiverAddress
                });
                setFile(null);
                setReceiverAddress("");
            } else {
                setStatus(`Failed: ${res.data.message}`);
            }
        } catch (error) {
            setStatus(`Error: ${error.response?.data?.detail || "Failed to send secret."}`);
        }
        setUploading(false);
    };

    return (
        <div className="glass-card">
            <h3>🕵️ Send Secret Payload</h3>
            <p style={{ color: "var(--text-secondary)", marginBottom: "20px" }}>
                Hide an encrypted image inside a normal-looking cover image. The access NFT will be minted directly to the recipient's wallet.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "15px", marginBottom: "20px" }}>
                <div>
                    <label style={{ display: "block", marginBottom: "5px", color: "var(--accent-primary)" }}>1. Select Secret Image</label>
                    <input 
                        type="file" 
                        onChange={handleFileChange} 
                        accept="image/*" 
                        disabled={uploading}
                        className="input-field"
                        style={{ padding: "10px", width: "100%", background: "rgba(255,255,255,0.05)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)" }}
                    />
                </div>

                <div>
                    <label style={{ display: "block", marginBottom: "5px", color: "var(--accent-primary)" }}>2. Receiver's Wallet Address</label>
                    <input 
                        type="text" 
                        placeholder="0x..." 
                        value={receiverAddress}
                        onChange={(e) => setReceiverAddress(e.target.value)}
                        disabled={uploading}
                        className="input-field"
                        style={{ padding: "12px", width: "100%", background: "rgba(255,255,255,0.05)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)", color: "white" }}
                    />
                </div>

                <div>
                    <label style={{ display: "block", marginBottom: "5px", color: "var(--accent-primary)" }}>3. Select Cover Image Strategy</label>
                    <div style={{ display: "flex", gap: "10px", marginBottom: "10px" }}>
                        <button 
                            className={`btn ${!isCustomCover ? 'btn-primary' : ''}`}
                            style={{ flex: 1, backgroundColor: !isCustomCover ? "var(--accent-primary)" : "rgba(255,255,255,0.05)" }}
                            onClick={() => setIsCustomCover(false)}
                            disabled={uploading}
                        >
                            🖼️ Choose Existing
                        </button>
                        <button 
                            className={`btn ${isCustomCover ? 'btn-primary' : ''}`}
                            style={{ flex: 1, backgroundColor: isCustomCover ? "var(--accent-primary)" : "rgba(255,255,255,0.05)" }}
                            onClick={() => setIsCustomCover(true)}
                            disabled={uploading}
                        >
                            ⬆️ Upload Custom Cover
                        </button>
                    </div>

                    {!isCustomCover ? (
                        <select 
                            value={selectedCover}
                            onChange={(e) => setSelectedCover(e.target.value)}
                            disabled={uploading}
                            className="input-field"
                            style={{ padding: "12px", width: "100%", background: "rgba(255,255,255,0.05)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)", color: "white" }}
                        >
                            {coverOptions.map(cover => (
                                <option key={cover} value={cover} style={{ color: "black" }}>{cover}</option>
                            ))}
                        </select>
                    ) : (
                        <input 
                            type="file" 
                            onChange={(e) => {
                                if (e.target.files) setCustomCoverFile(e.target.files[0]);
                            }} 
                            accept="image/*" 
                            disabled={uploading}
                            className="input-field"
                            style={{ padding: "10px", width: "100%", background: "rgba(255,255,255,0.05)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)" }}
                        />
                    )}
                </div>
            </div>

            <button 
                className="btn btn-primary" 
                onClick={handleSendSecret} 
                disabled={!file || !receiverAddress || uploading}
                style={{ width: "100%", padding: "12px", fontSize: "1.1rem", backgroundColor: "var(--accent-primary)" }}
            >
                {uploading ? "Airdropping Secret..." : "Hide & Transfer Ownership"}
            </button>

            {status && (
                <div className="status-banner" style={{ marginTop: "20px" }}>
                    {status}
                </div>
            )}

            {receipt && (
                <div style={{ marginTop: "20px", padding: "15px", background: "rgba(16, 185, 129, 0.1)", borderRadius: "8px", border: "1px solid var(--success)" }}>
                    <h4 style={{ color: "var(--success)", marginBottom: "10px" }}>Transfer Receipt</h4>
                    <p><strong>Receiver:</strong> {receipt.receiver}</p>
                    <p><strong>Token ID:</strong> {receipt.tokenId}</p>
                    <p><strong>AWS S3 Cover:</strong> <a href={receipt.coverUrl} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-primary)" }}>View Cover Image</a></p>
                </div>
            )}
        </div>
    );
};

export default SendSecret;
