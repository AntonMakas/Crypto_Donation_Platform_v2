import { network } from "hardhat";

const { ethers } = await network.connect({
  network: "amoy",
  chainType: "l1",
});

const JarFund = await ethers.getContractFactory("JarFund");
const jarFund = await JarFund.deploy(100);

await jarFund.waitForDeployment();

const address = await jarFund.getAddress();
console.log(`JarFund deployed to: ${address}`);
