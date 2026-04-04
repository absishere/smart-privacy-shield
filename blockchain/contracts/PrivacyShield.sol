// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// We will import directly from URL for Remix
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract PrivacyShieldNFT is ERC721, Ownable {
    uint256 public nextTokenId;
    
    // Mapping from tokenId to encrypted key
    mapping(uint256 => string) private _keys;

    struct AccessRecord {
        address accessor;
        uint256 timestamp;
        string action;
    }
    
    mapping(uint256 => AccessRecord[]) private _auditTrail;
    
    event KeyAccessed(uint256 indexed tokenId, address indexed accessor, uint256 timestamp, string action);

    constructor(address initialOwner) 
        ERC721("PrivacyShield", "PSH") 
        Ownable(initialOwner) 
    {}

    // Mint NFT and store the associated encryption key
    function safeMint(address to, string memory encryptedKey) public onlyOwner returns (uint256) {
        uint256 tokenId = nextTokenId++;
        _safeMint(to, tokenId);
        _keys[tokenId] = encryptedKey;
        return tokenId;
    }

    // Retrieve key only if caller owns the token
    function getKey(uint256 tokenId) public view returns (string memory) {
        require(ownerOf(tokenId) == msg.sender, "Caller is not the owner of this NFT");
        return _keys[tokenId];
    }

    function hasAccess(address user) public view returns (bool) {
        return balanceOf(user) > 0;
    }

    // IMMUTABLE AUDIT TRAIL LOGGING
    // Only the backend administrator can record access to ensure logs are fully trusted and avoid giving users gas fees
    function recordAccess(uint256 tokenId, address accessor) external onlyOwner {
        _auditTrail[tokenId].push(AccessRecord(accessor, block.timestamp, "Decryption"));
        emit KeyAccessed(tokenId, accessor, block.timestamp, "Decryption");
    }

    function getAuditTrail(uint256 tokenId) external view returns (AccessRecord[] memory) {
        require(ownerOf(tokenId) == msg.sender || msg.sender == owner(), "Caller is not authorized to view audit trail");
        return _auditTrail[tokenId];
    }
}