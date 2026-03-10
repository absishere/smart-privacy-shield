import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Vault = ({ walletAddress }) => {
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState("");
    
    // Decryption States
    const [decryptedImage, setDecryptedImage] = useState(null);
    const [isDecrypting, setIsDecrypting] = useState(false);
    const [timeLeft, setTimeLeft] = useState(0);

    // Fetch images from S3 via Backend
    const fetchImages = async () => {
        try {
            const res = await axios.get(`http://127.0.0.1:8000/user-images?wallet_address=${walletAddress}`);
            if (res.data.status === "success") {
                // Filter out the .roi files so we only show the images
                const imageFiles = res.data.images.filter(img => !img.key.endsWith('.roi'));
                setImages(imageFiles);
            }
        } catch (error) {
            console.error("Failed to fetch images", error);
            setStatus("Failed to load vault from AWS S3.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchImages();
    }, [walletAddress]);

    // Timer logic for Decrypted Image
    useEffect(() => {
        let timer;
        if (timeLeft > 0 && decryptedImage) {
            timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
        } else if (timeLeft === 0 && decryptedImage) {
            // Shred the image from RAM when time is up
            setDecryptedImage(null);
            setStatus("Session expired. Image shredded from memory.");
        }
        return () => clearTimeout(timer);
    }, [timeLeft, decryptedImage]);

    const handleDecrypt = async (s3Key) => {
        // Send the full S3 Key so the backend knows if it's stego/ or encrypted/
        const filename = s3Key;
        
        // In a real app, we'd fetch the specific tokenId linked to this image from a DB or Blockchain index.
        // For the mockup, we will prompt the user (or you can hardcode '1' if you only minted one).
        const tokenId = prompt("Enter the NFT Token ID for this image to verify ownership:");
        if (!tokenId) return;

        setIsDecrypting(true);
        setStatus("Verifying NFT ownership and decrypting in RAM...");

        const formData = new FormData();
        formData.append("filename", filename);
        formData.append("wallet_address", walletAddress);
        formData.append("token_id", tokenId);

        try {
            const res = await axios.post("http://127.0.0.1:8000/decrypt", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            if (res.data.status === "success") {
                setDecryptedImage(res.data.image_data);
                setTimeLeft(60); // 60 seconds viewing window
                setStatus("Decrypted successfully. Image is live in secure memory.");
            } else {
                setStatus(`Error: ${res.data.message}`);
            }
        } catch (error) {
            console.error(error);
            setStatus(error.response?.data?.detail || "Decryption failed. Check ownership.");
        }
        setIsDecrypting(false);
    };

    const handleDownload = () => {
        if (!decryptedImage) return;
        const link = document.createElement('a');
        link.href = decryptedImage;
        link.download = 'secure_decrypted_payload.jpg';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleDelete = async (s3Key) => {
        const confirmDelete = window.confirm("Are you sure? This will permanently wipe the encrypted data from AWS S3.");
        if (!confirmDelete) return;

        const filename = s3Key; // Use full S3 key to avoid decryption key mismatch issues!
        const tokenId = prompt("Enter the NFT Token ID to verify deletion authority:");
        if (!tokenId) return;

        setStatus(`Verifying ownership and shredding ${filename.split('/').pop()} from AWS...`);

        const formData = new FormData();
        formData.append("filename", filename);
        formData.append("wallet_address", walletAddress);
        formData.append("token_id", tokenId);

        try {
            const res = await axios.delete("http://127.0.0.1:8000/delete-image", {
                data: formData, // axios.delete requires payload to be inside 'data'
                headers: { "Content-Type": "multipart/form-data" }
            });

            if (res.data.status === "success") {
                setStatus("✅ File permanently shredded from the cloud.");
                // Refresh the vault instantly
                fetchImages(); 
            }
        } catch (error) {
            console.error(error);
            setStatus(error.response?.data?.detail || "Deletion failed. Check ownership.");
        }
    };

    if (loading) return <div className="glass-card">Loading Secure Vault...</div>;

    return (
        <div className="vault-container">
            <div className="glass-card">
                <h3>🗄️ AWS S3 Vault</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: "20px" }}>
                    These images are heavily encrypted at rest. To view them, your wallet must hold the corresponding NFT.
                </p>

                {status && (
                    <div className="status-banner">
                        {status}
                    </div>
                )}

                {/* Active Decryption Modal/View */}
                {decryptedImage && (
                    <div className="decrypted-viewer glass-card" style={{ borderColor: "var(--danger)", marginBottom: "30px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <h4 style={{ color: "var(--danger)" }}>⚠️ SECURE VIEW ACTIVE</h4>
                            <span style={{ fontWeight: "bold", fontSize: "1.2rem", color: timeLeft <= 10 ? "red" : "white" }}>
                                Shredding in: {timeLeft}s
                            </span>
                        </div>
                        
                        <div className="image-wrapper" style={{ marginTop: "15px", textAlign: "center" }}>
                            <img 
                                src={decryptedImage} 
                                alt="Decrypted Payload" 
                                style={{ maxWidth: "100%", maxHeight: "400px", borderRadius: "8px", userSelect: "none", WebkitUserDrag: "none" }} 
                            />
                        </div>
                        
                        <div style={{ marginTop: "15px", display: "flex", gap: "10px" }}>
                            <button className="btn btn-primary" onClick={handleDownload}>
                                ⬇️ Download to Device
                            </button>
                            <button className="btn btn-danger" onClick={() => setDecryptedImage(null)}>
                                🔒 Shred Now
                            </button>
                        </div>
                    </div>
                )}

                {/* S3 Grid */}
                <div className="image-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "20px" }}>
                    {images.map((img, idx) => (
                        <div key={idx} className="grid-item glass-card" style={{ padding: "10px", textAlign: "center" }}>
                            <img 
                                src={img.url} 
                                alt="Encrypted Cover" 
                                style={{ width: "100%", height: "150px", objectFit: "cover", borderRadius: "6px", marginBottom: "10px" }} 
                            />
                            <p style={{ fontSize: "0.8rem", wordBreak: "break-all", marginBottom: "10px", color: "var(--text-secondary)" }}>
                                {img.key.split('/').pop()}
                            </p>
                            <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                                <button 
                                    className="btn btn-primary" 
                                    style={{ flex: 1, fontSize: "0.9rem" }}
                                    onClick={() => handleDecrypt(img.key)}
                                    disabled={isDecrypting || decryptedImage !== null}
                                >
                                    🔓 Decrypt
                                </button>
                                <button 
                                    className="btn btn-danger" 
                                    style={{ flex: 1, fontSize: "0.9rem", backgroundColor: "var(--danger)" }}
                                    onClick={() => handleDelete(img.key)}
                                    disabled={isDecrypting || decryptedImage !== null}
                                >
                                    🗑️ Shred
                                </button>
                            </div>
                        </div>
                    ))}
                    {images.length === 0 && <p>Your vault is empty.</p>}
                </div>
            </div>
        </div>
    );
};

export default Vault;
