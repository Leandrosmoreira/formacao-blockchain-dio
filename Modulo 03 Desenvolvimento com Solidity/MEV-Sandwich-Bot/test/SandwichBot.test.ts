import { expect } from "chai";
import { ethers } from "hardhat";
import { SandwichBot } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("SandwichBot", function () {
  let sandwichBot: SandwichBot;
  let owner: SignerWithAddress;
  let addr1: SignerWithAddress;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();

    const SandwichBot = await ethers.getContractFactory("SandwichBot");
    sandwichBot = await SandwichBot.deploy();
    await sandwichBot.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await sandwichBot.owner()).to.equal(owner.address);
    });
  });

  describe("Access Control", function () {
    it("Should only allow owner to execute functions", async function () {
      const router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"; // Uniswap V2 Router
      const weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";
      const usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48";
      const amount = ethers.parseEther("1");
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      // Should fail when called by non-owner
      await expect(
        sandwichBot.connect(addr1).executeFrontrun(
          router,
          weth,
          usdc,
          amount,
          0,
          deadline
        )
      ).to.be.revertedWith("Not owner");
    });
  });

  describe("Emergency Withdraw", function () {
    it("Should allow owner to withdraw ETH", async function () {
      // Send some ETH to contract
      await owner.sendTransaction({
        to: await sandwichBot.getAddress(),
        value: ethers.parseEther("1"),
      });

      const initialBalance = await ethers.provider.getBalance(owner.address);

      // Withdraw
      const tx = await sandwichBot.emergencyWithdraw(ethers.ZeroAddress, 0);
      const receipt = await tx.wait();

      // Owner should have received the ETH (minus gas costs)
      const finalBalance = await ethers.provider.getBalance(owner.address);
      expect(finalBalance).to.be.gt(initialBalance);
    });

    it("Should only allow owner to withdraw", async function () {
      await expect(
        sandwichBot.connect(addr1).emergencyWithdraw(ethers.ZeroAddress, 0)
      ).to.be.revertedWith("Not owner");
    });
  });

  describe("Token Balance", function () {
    it("Should correctly report token balance", async function () {
      const weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";
      const balance = await sandwichBot.getTokenBalance(weth);
      expect(balance).to.equal(0);
    });
  });
});
