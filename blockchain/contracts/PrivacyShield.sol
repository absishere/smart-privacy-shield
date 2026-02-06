// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// We will import directly from URL for Remix
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract PrivacyShieldNFT is ERC721, Ownable {
    uint256 public nextTokenId;

    constructor(address initialOwner) 
        ERC721("PrivacyShield", "PSH") 
        Ownable(initialOwner) 
    {}

    function safeMint(address to) public onlyOwner {
        uint256 tokenId = nextTokenId++;
        _safeMint(to, tokenId);
    }

    function hasAccess(address user) public view returns (bool) {
        return balanceOf(user) > 0;
    }
}