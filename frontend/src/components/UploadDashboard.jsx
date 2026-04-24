import React, { useState } from 'react';
import axios from '../api/axios';

const UploadDashboard = ({ walletAddress }) => {
    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [results, setResults] = useState([]);
    const [globalStatus, setGlobalStatus] = useState("");

    const handleFileChange = (e) => {
        if (e.target.files) {
            setFiles(Array.from(e.target.files));
            setResults([]);
            setGlobalStatus("");
        }
    };

    const handleBatchUpload = async () => {
        if (files.length === 0) return;
        setUploading(true);
        setGlobalStatus(`Processing ${files.length} images...`);
        
        const newResults = [];

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append("file", file);
            formData.append("wallet_address", walletAddress);
            formData.append("is_stego_mode", "false"); // Strict Encryption Mode

            try {
                setGlobalStatus(`Encrypting and Minting ${i + 1} of ${files.length}...`);
                const res = await axios.post("/process-image", formData, {
                    headers: { "Content-Type": "multipart/form-data" }
                });

                if (res.data.status === "success") {
                    newResults.push({
                        name: file.name,
                        status: "Success",
                        tokenId: res.data.token_id,
                        url: res.data.processed_url
                    });
                } else {
                    newResults.push({ name: file.name, status: `Failed: ${res.data.message}` });
                }
            } catch (error) {
                newResults.push({ 
                    name: file.name, 
                    status: `Error: ${error.response?.data?.detail || "Network issue"}` 
                });
            }
        }

        setResults(newResults);
        setGlobalStatus("Batch processing complete! Images are now secured in AWS S3.");
        setUploading(false);
        setFiles([]); // Clear input after successful upload
    };

    return (
        <div className="glass-card">
            <h3>📤 Secure Batch Upload</h3>
            <p style={{ color: "var(--text-secondary)", marginBottom: "20px" }}>
                Select images to encrypt. Each image will be secured with its own NFT access key before being sent to the cloud.
            </p>

            <div style={{ marginBottom: "20px" }}>
                <input 
                    type="file" 
                    multiple 
                    onChange={handleFileChange} 
                    accept="image/*" 
                    disabled={uploading}
                    className="input-field"
                    style={{ padding: "10px", width: "100%", background: "rgba(255,255,255,0.05)", borderRadius: "8px" }}
                />
            </div>

            <button 
                className="btn btn-primary" 
                onClick={handleBatchUpload} 
                disabled={files.length === 0 || uploading}
                style={{ width: "100%", padding: "12px", fontSize: "1.1rem" }}
            >
                {uploading ? "Securing Payload..." : `Encrypt & Upload ${files.length > 0 ? files.length : ''} Images`}
            </button>

            {globalStatus && (
                <div className="status-banner" style={{ marginTop: "20px" }}>
                    {globalStatus}
                </div>
            )}

            {results.length > 0 && (
                <div style={{ marginTop: "30px" }}>
                    <h4>Processing Results:</h4>
                    <ul style={{ listStyleType: "none", padding: 0, marginTop: "10px" }}>
                        {results.map((res, idx) => (
                            <li key={idx} style={{ 
                                padding: "10px", 
                                background: "rgba(0,0,0,0.2)", 
                                margin: "5px 0", 
                                borderRadius: "6px",
                                borderLeft: res.status === "Success" ? "4px solid var(--success)" : "4px solid var(--danger)"
                            }}>
                                <strong>{res.name}</strong> - {res.status}
                                {res.tokenId && <span style={{ float: "right", color: "var(--accent-primary)" }}>NFT ID: {res.tokenId}</span>}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default UploadDashboard;
