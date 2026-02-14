require("@nomicfoundation/hardhat-toolbox");

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
  },
};