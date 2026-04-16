import hardhatToolboxMochaEthersPlugin from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { defineConfig } from "hardhat/config";
import dotenv from "dotenv";

dotenv.config({ quiet: true });

const AMOY_RPC_URL = process.env.AMOY_RPC_URL ?? "http://127.0.0.1:8545";
const AMOY_PRIVATE_KEY =
  process.env.AMOY_PRIVATE_KEY ??
  "0x0000000000000000000000000000000000000000000000000000000000000001";

export default defineConfig({
  plugins: [hardhatToolboxMochaEthersPlugin],
  solidity: {
    profiles: {
      default: {
        version: "0.8.28",
      },
      production: {
        version: "0.8.28",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
    },
  },
  networks: {
    hardhatMainnet: {
      type: "edr-simulated",
      chainType: "l1",
    },
    hardhatOp: {
      type: "edr-simulated",
      chainType: "op",
    },
    amoy: {
      type: "http",
      chainType: "l1",
      url: AMOY_RPC_URL,
      accounts: [AMOY_PRIVATE_KEY],
      chainId: 80002,
    },
  },
});
