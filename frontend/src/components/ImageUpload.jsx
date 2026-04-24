import React, { useState, useEffect } from 'react';
import axios from '../api/axios';

const ImageUpload = ({ walletAddress }) => {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState("");
    const [uploading, setUploading] = useState(false);

    // New states for feature
    const [processedImageUrl, setProcessedImageUrl] = useState("");
    const [originalFilename, setOriginalFilename] = useState("");
    const [decryptedImageUrl, setDecryptedImageUrl] = useState("");
    const [isDecrypting, setIsDecrypting] = useState(false);
    const [tokenId, setTokenId] = useState(null);

    // Phase 1 Steganography
    const [isStegoMode, setIsStegoMode] = useState(true);
    const [coverImageName, setCoverImageName] = useState("default_cover.png");
    const [stegoImageUrl, setStegoImageUrl] = useState("");
    const [availableCovers, setAvailableCovers] = useState([]);

    useEffect(() => {
        const fetchCovers = async () => {
            try {
                const res = await axios.get("/covers");
                setAvailableCovers(res.data.covers || []);
                if (res.data.covers && res.data.covers.length > 0 && !res.data.covers.includes(coverImageName)) {
                    setCoverImageName(res.data.covers[0]);
                }
            } catch (error) {
                console.error("Failed to fetch covers:", error);
            }
        };
        fetchCovers();
    }, []);

    const handleFileChange = (e) => {
        if (e.target.files) {
            setFile(e.target.files[0]);
            // Reset previews when a new file is selected
            setProcessedImageUrl("");
            setDecryptedImageUrl("");
            setStegoImageUrl("");
            setStatus("");
            setTokenId(null);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setStatus("Uploading & Processing secure payload...");
        setProcessedImageUrl("");
        setDecryptedImageUrl("");
        setStegoImageUrl("");
        setTokenId(null);

        const formData = new FormData();
        formData.append("file", file);
        formData.append("wallet_address", walletAddress);
        formData.append("is_stego_mode", isStegoMode);
        
        let endpoint = "/process-image";
        
        if (isStegoMode) {
            formData.append("cover_image_name", coverImageName);
        }

        try {
            // Send to your Python Backend
            const res = await axios.post(endpoint, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            if (res.data.status === "success") {
                setStatus("Processed Successfully!");
                setOriginalFilename(res.data.original);
                if (res.data.token_id !== undefined) {
                    setTokenId(res.data.token_id);
                }
                
                if (res.data.mode === "stego") {
                    setStegoImageUrl(res.data.display_url);
                } else {
                    setProcessedImageUrl(res.data.display_url);
                }
            } else {
                setStatus(`Error: ${res.data.message}`);
            }
        } catch (error) {
            console.error(error);
            if (error.response && error.response.data && error.response.data.detail) {
                setStatus(`Error: ${error.response.data.detail}`);
            } else {
                setStatus("Upload Failed");
            }
        }
        setUploading(false);
    };

    const handleDecrypt = async () => {
        if (!originalFilename || !walletAddress || tokenId === null) {
            setStatus("Error: Missing file, wallet address, or token ID.");
            return;
        }
        setIsDecrypting(true);
        setStatus(isStegoMode ? "Verifying wallet and extracting payload..." : "Verifying wallet and decrypting payload...");

        const formData = new FormData();
        formData.append("filename", originalFilename);
        formData.append("wallet_address", walletAddress);
        formData.append("token_id", tokenId); // Pass token_id to backend
        
        let endpoint = "/decrypt";

        try {
            const res = await axios.post(endpoint, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            if (res.data.status === "success") {
                setStatus(isStegoMode ? "Extracted and Decrypted Successfully!" : "Decrypted Successfully!");
                setDecryptedImageUrl(res.data.decrypted_url);
            } else {
                setStatus(`Error: ${res.data.message}`);
            }
        } catch (error) {
            console.error(error);
            // Show the specific error message from the backend if available
            if (error.response && error.response.data && error.response.data.detail) {
                 setStatus(`Error: ${error.response.data.detail}`);
            } else {
                 setStatus("Decrypt Failed");
            }
        }
        setIsDecrypting(false);
    }

    return (
        <div className="glass-card">
            <h3>📂 Security Dashboard</h3>

            <div style={{ marginBottom: "20px" }}>
                <input type="file" onChange={handleFileChange} accept="image/*" style={{ marginBottom: "10px", display: "block" }} />

                <div style={{ marginBottom: "15px", display: "flex", gap: "10px", alignItems: "center" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                        <input 
                            type="checkbox" 
                            checked={isStegoMode} 
                            onChange={(e) => setIsStegoMode(e.target.checked)} 
                        />
                        Steganography (Hide in Image)
                    </label>
                    
                    {isStegoMode && (
                        <select 
                            value={coverImageName} 
                            onChange={(e) => setCoverImageName(e.target.value)}
                            className="input-field"
                            style={{ padding: "5px 10px", borderRadius: "4px", border: "1px solid #ccc", background: "rgba(255,255,255,0.1)", color: "white" }}
                        >
                            {availableCovers.map(cover => (
                                <option key={cover} value={cover} style={{ color: "black" }}>{cover}</option>
                            ))}
                            {availableCovers.length === 0 && <option value="default_cover.png" style={{ color: "black" }}>default_cover.png</option>}
                        </select>
                    )}
                </div>

                <button
                    className="btn btn-primary"
                    onClick={handleUpload}
                    disabled={!file || uploading}
                >
                    {uploading ? "Processing..." : "Process & Secure Image"}
                </button>
            </div>

            {status && (
                <div style={{ padding: "10px", background: "rgba(255,255,255,0.05)", borderRadius: "6px", marginBottom: "20px", fontSize: "0.9rem" }}>
                    <span style={{ color: status.includes("Error") || status.includes("Failed") ? "var(--danger)" : "var(--accent-primary)" }}>●</span> {status}
                </div>
            )}

            {/* Display Previews */}
            {(processedImageUrl || stegoImageUrl || decryptedImageUrl) && (
                <div className="preview-container">
                    {(processedImageUrl || stegoImageUrl) && (
                        <div className="preview-box">
                            <h4 style={{ color: "var(--text-secondary)", marginBottom: "10px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                                {stegoImageUrl ? "🖼️ Stego Image (Secret Hidden)" : "🔒 Encrypted Output"}
                            </h4>
                            {tokenId !== null && (
                                <div style={{ fontSize: "12px", color: "var(--success)", background: "rgba(16, 185, 129, 0.1)", padding: "4px 8px", borderRadius: "12px", display: "inline-block" }}>
                                    NFT Minted! Token ID: <b>{tokenId}</b>
                                </div>
                            )}
                            <img
                                src={stegoImageUrl || processedImageUrl}
                                alt={stegoImageUrl ? "Steganography Cover" : "Encrypted"}
                            />
                            <div>
                                <button
                                    className="btn btn-danger"
                                    onClick={handleDecrypt}
                                    disabled={isDecrypting}
                                    style={{ width: "100%" }}
                                >
                                    {isDecrypting ? "Verifying..." : (isStegoMode ? "🔓 Extract & Decrypt Payload" : "🔓 Decrypt Payload")}
                                </button>
                            </div>
                        </div>
                    )}

                    {decryptedImageUrl && (
                        <div className="preview-box" style={{ borderColor: "rgba(16, 185, 129, 0.3)" }}>
                            <h4 style={{ color: "var(--success)", marginBottom: "10px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                                ✅ Restored Payload
                            </h4>
                            <img
                                src={decryptedImageUrl}
                                alt="Decrypted"
                            />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ImageUpload;