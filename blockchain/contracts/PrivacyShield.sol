// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// We will import directly from URL for Remix
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract PrivacyShieldNFT is ERC721, Ownable {
    uint256 public nextTokenId;
    
    // Mapping from tokenId to encrypted key
    mapping(uint256 => string) private _keys;

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
}