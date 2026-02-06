const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    // 1. Get the deployer's wallet address (First account in Ganache)
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying contracts with the account:", deployer.address);

    // 2. Deploy the Contract
    // We pass the deployer's address as the 'initialOwner' constructor argument
    const privacyShield = await hre.ethers.deployContract("PrivacyShieldNFT", [deployer.address]);

    await privacyShield.waitForDeployment();

    const contractAddress = await privacyShield.getAddress();
    console.log("✅ PrivacyShieldNFT deployed to:", contractAddress);

    // 3. Save the Address and ABI automatically (So Python can find it)
    // We save these directly into the 'blockchain' folder root
    const addressPath = path.join(__dirname, "..", "address.txt");
    const abiPath = path.join(__dirname, "..", "abi.json");

    // Save Address
    fs.writeFileSync(addressPath, contractAddress);

    // Save ABI
    // We extract the ABI from the build artifacts
    const artifactPath = path.join(__dirname, "..", "artifacts", "contracts", "PrivacyShield.sol", "PrivacyShieldNFT.json");
    const contractArtifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    fs.writeFileSync(abiPath, JSON.stringify(contractArtifact.abi));

    console.log("💾 Address and ABI saved successfully!");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});