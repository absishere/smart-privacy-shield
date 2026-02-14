import React, { useState } from 'react';
import axios from 'axios';

const ImageUpload = ({ walletAddress }) => {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState("");
    const [uploading, setUploading] = useState(false);

    const handleFileChange = (e) => {
        if (e.target.files) {
            setFile(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setStatus("Uploading...");

        const formData = new FormData();
        formData.append("file", file);

        try {
            // Send to your Python Backend
            const res = await axios.post("http://127.0.0.1:8000/upload", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            if (res.data.status === "pending_ai") {
                setStatus("✅ Uploaded! (Waiting for AI integration)");
                console.log("Server response:", res.data);
            } else {
                setStatus("✅ Processed!");
            }
        } catch (error) {
            console.error(error);
            setStatus("❌ Upload Failed");
        }
        setUploading(false);
    };

    return (
        <div style={{ marginTop: "20px", padding: "20px", border: "1px solid #ccc", borderRadius: "8px" }}>
            <h3>📂 Member 4: Image Dashboard</h3>
            <p>Wallet: <code style={{ background: "#eee" }}>{walletAddress}</code></p>

            <input type="file" onChange={handleFileChange} accept="image/*" />

            <button
                onClick={handleUpload}
                disabled={!file || uploading}
                style={{ marginLeft: "10px", padding: "8px 16px", cursor: "pointer" }}
            >
                {uploading ? "Uploading..." : "Upload Image"}
            </button>

            {status && <p style={{ marginTop: "10px", fontWeight: "bold" }}>{status}</p>}
        </div>
    );
};

export default ImageUpload;