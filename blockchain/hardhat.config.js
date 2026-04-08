require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.20",
  networks: {
    // We define a network named "ganache"
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      // Hardhat will automatically use the first account provided by Ganache
    },
    sepolia: {
      url: `https://eth-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
      accounts: [process.env.ADMIN_PRIVATE_KEY],
    },
  },
};