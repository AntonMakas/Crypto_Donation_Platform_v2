import { network } from "hardhat";
import { formatEther } from "ethers";

function getCliNetwork(): string {
  const networkArgIndex = process.argv.indexOf("--network");
  if (networkArgIndex >= 0 && process.argv[networkArgIndex + 1]) {
    return process.argv[networkArgIndex + 1];
  }
  return process.env.HARDHAT_NETWORK ?? "amoy";
}

const targetNetwork = getCliNetwork();
const { ethers } = await network.connect({
  network: targetNetwork,
  chainType: "l1",
});

const [deployer] = await ethers.getSigners();
const deployerAddress = await deployer.getAddress();
const deployerBalance = await ethers.provider.getBalance(deployerAddress);

console.log(`Deploying to ${targetNetwork}`);
console.log(`Deployer: ${deployerAddress}`);
console.log(`Balance: ${formatEther(deployerBalance)} POL`);

const JarFund = await ethers.getContractFactory("JarFund");
const jarFund = await JarFund.deploy();

await jarFund.waitForDeployment();

const address = await jarFund.getAddress();
console.log(`JarFund deployed to ${targetNetwork}: ${address}`);
