import { ethers } from "hardhat";
import * as dotenv from "dotenv";

dotenv.config();

async function main() {
  console.log("=".repeat(60));
  console.log("Deploying SandwichBot Contract...");
  console.log("=".repeat(60));

  const [deployer] = await ethers.getSigners();

  console.log("Deploying with account:", deployer.address);
  console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString());

  // Deploy contract
  const SandwichBot = await ethers.getContractFactory("SandwichBot");
  console.log("\nDeploying contract...");

  const sandwichBot = await SandwichBot.deploy();
  await sandwichBot.waitForDeployment();

  const contractAddress = await sandwichBot.getAddress();

  console.log("\n" + "=".repeat(60));
  console.log("✅ SandwichBot deployed successfully!");
  console.log("=".repeat(60));
  console.log("Contract Address:", contractAddress);
  console.log("Owner:", deployer.address);
  console.log("=".repeat(60));

  console.log("\n📝 Next steps:");
  console.log("1. Update your .env file with:");
  console.log(`   SANDWICH_CONTRACT_ADDRESS=${contractAddress}`);
  console.log("\n2. Fund the contract with tokens for trading");
  console.log("\n3. Verify contract on Etherscan:");
  console.log(`   npx hardhat verify --network ${process.env.NETWORK} ${contractAddress}`);

  // Save deployment info
  const deploymentInfo = {
    network: process.env.NETWORK || "unknown",
    contractAddress: contractAddress,
    owner: deployer.address,
    deployedAt: new Date().toISOString(),
    blockNumber: await ethers.provider.getBlockNumber(),
  };

  console.log("\nDeployment Info:", JSON.stringify(deploymentInfo, null, 2));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
