const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time, loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("DeltaNeutralVaultV1", function () {

  // Fixture para deploy do contrato
  async function deployVaultFixture() {
    const [owner, keeper, treasury, user1, user2] = await ethers.getSigners();

    // Deploy mock tokens
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    const usdc = await MockERC20.deploy("USD Coin", "USDC", 6);
    const wbtc = await MockERC20.deploy("Wrapped Bitcoin", "WBTC", 8);

    // Deploy mock Chainlink feed
    const MockChainlinkFeed = await ethers.getContractFactory("MockChainlinkFeed");
    const chainlinkFeed = await MockChainlinkFeed.deploy(8, 40000_00000000); // $40,000

    // Deploy mock Uniswap contracts
    const MockPositionManager = await ethers.getContractFactory("MockPositionManager");
    const positionManager = await MockPositionManager.deploy();

    const MockSwapRouter = await ethers.getContractFactory("MockSwapRouter");
    const swapRouter = await MockSwapRouter.deploy();

    // Deploy vault
    const DeltaNeutralVault = await ethers.getContractFactory("DeltaNeutralVaultV1");
    const vault = await DeltaNeutralVault.deploy(
      await usdc.getAddress(),
      "Delta Neutral Vault Shares",
      "dnvUSDC",
      await chainlinkFeed.getAddress(),
      treasury.address,
      await positionManager.getAddress(),
      await swapRouter.getAddress()
    );

    // Mint tokens para users
    await usdc.mint(user1.address, ethers.parseUnits("100000", 6)); // 100k USDC
    await usdc.mint(user2.address, ethers.parseUnits("50000", 6));  // 50k USDC

    return {
      vault,
      usdc,
      wbtc,
      chainlinkFeed,
      positionManager,
      swapRouter,
      owner,
      keeper,
      treasury,
      user1,
      user2
    };
  }

  describe("Deployment", function () {
    it("Should set the correct owner", async function () {
      const { vault, owner } = await loadFixture(deployVaultFixture);
      expect(await vault.owner()).to.equal(owner.address);
    });

    it("Should set the correct treasury", async function () {
      const { vault, treasury } = await loadFixture(deployVaultFixture);
      expect(await vault.treasury()).to.equal(treasury.address);
    });

    it("Should set the correct asset (USDC)", async function () {
      const { vault, usdc } = await loadFixture(deployVaultFixture);
      expect(await vault.asset()).to.equal(await usdc.getAddress());
    });

    it("Should initialize with default parameters", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      expect(await vault.maxOracleDeviationBps()).to.equal(500);  // 5%
      expect(await vault.maxOracleDelay()).to.equal(3600);        // 1 hour
      expect(await vault.maxSlippageBps()).to.equal(100);         // 1%
    });
  });

  describe("Configuration", function () {
    it("Should allow owner to set keeper", async function () {
      const { vault, keeper } = await loadFixture(deployVaultFixture);

      await expect(vault.setKeeper(keeper.address))
        .to.emit(vault, "KeeperUpdated")
        .withArgs(ethers.ZeroAddress, keeper.address);

      expect(await vault.keeper()).to.equal(keeper.address);
    });

    it("Should not allow non-owner to set keeper", async function () {
      const { vault, keeper, user1 } = await loadFixture(deployVaultFixture);

      await expect(
        vault.connect(user1).setKeeper(keeper.address)
      ).to.be.revertedWith("Ownable: caller is not the owner");
    });

    it("Should allow owner to set fees", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      await expect(vault.setFees(
        2000,  // 20% performance
        200,   // 2% management
        50,    // 0.5% entry
        50,    // 0.5% exit
        30,    // 0.3% swap
        10     // 0.1% keeper
      )).to.emit(vault, "FeesUpdated");

      expect(await vault.performanceFeeBps()).to.equal(2000);
      expect(await vault.managementFeeBps()).to.equal(200);
      expect(await vault.entryFeeBps()).to.equal(50);
      expect(await vault.exitFeeBps()).to.equal(50);
      expect(await vault.swapFeeBps()).to.equal(30);
      expect(await vault.keeperFeeBps()).to.equal(10);
    });

    it("Should reject fees that are too high", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      await expect(
        vault.setFees(6000, 200, 50, 50, 30, 10) // 60% performance - too high
      ).to.be.revertedWith("DeltaNeutralVault: performance fee too high");
    });
  });

  describe("Deposits", function () {
    it("Should allow deposits", async function () {
      const { vault, usdc, user1 } = await loadFixture(deployVaultFixture);

      const depositAmount = ethers.parseUnits("1000", 6); // 1000 USDC

      // Approve
      await usdc.connect(user1).approve(await vault.getAddress(), depositAmount);

      // Deposit
      await expect(vault.connect(user1).deposit(depositAmount, user1.address))
        .to.emit(vault, "Deposit");

      // Verificar shares recebidas
      const shares = await vault.balanceOf(user1.address);
      expect(shares).to.be.gt(0);
    });

    it("Should charge entry fee on deposit", async function () {
      const { vault, usdc, treasury, user1 } = await loadFixture(deployVaultFixture);

      // Set entry fee de 1%
      await vault.setFees(0, 0, 100, 0, 0, 0);

      const depositAmount = ethers.parseUnits("1000", 6); // 1000 USDC
      const expectedFee = ethers.parseUnits("10", 6);     // 10 USDC (1%)

      await usdc.connect(user1).approve(await vault.getAddress(), depositAmount);

      const treasuryBalanceBefore = await usdc.balanceOf(treasury.address);

      await vault.connect(user1).deposit(depositAmount, user1.address);

      const treasuryBalanceAfter = await usdc.balanceOf(treasury.address);

      expect(treasuryBalanceAfter - treasuryBalanceBefore).to.equal(expectedFee);
    });

    it("Should handle multiple deposits", async function () {
      const { vault, usdc, user1, user2 } = await loadFixture(deployVaultFixture);

      const amount1 = ethers.parseUnits("1000", 6);
      const amount2 = ethers.parseUnits("2000", 6);

      await usdc.connect(user1).approve(await vault.getAddress(), amount1);
      await usdc.connect(user2).approve(await vault.getAddress(), amount2);

      await vault.connect(user1).deposit(amount1, user1.address);
      await vault.connect(user2).deposit(amount2, user2.address);

      const totalAssets = await vault.totalAssets();
      expect(totalAssets).to.equal(amount1 + amount2);
    });
  });

  describe("Withdrawals", function () {
    async function depositedVaultFixture() {
      const fixture = await deployVaultFixture();
      const { vault, usdc, user1 } = fixture;

      const depositAmount = ethers.parseUnits("10000", 6);
      await usdc.connect(user1).approve(await vault.getAddress(), depositAmount);
      await vault.connect(user1).deposit(depositAmount, user1.address);

      return fixture;
    }

    it("Should allow withdrawals", async function () {
      const { vault, usdc, user1 } = await loadFixture(depositedVaultFixture);

      const shares = await vault.balanceOf(user1.address);
      const assets = await vault.convertToAssets(shares);

      const balanceBefore = await usdc.balanceOf(user1.address);

      await vault.connect(user1).redeem(shares, user1.address, user1.address);

      const balanceAfter = await usdc.balanceOf(user1.address);

      expect(balanceAfter - balanceBefore).to.be.closeTo(
        assets,
        ethers.parseUnits("1", 6) // 1 USDC de margem para fees
      );
    });

    it("Should charge exit fee on withdrawal", async function () {
      const { vault, usdc, treasury, user1 } = await loadFixture(depositedVaultFixture);

      // Set exit fee de 1%
      await vault.setFees(0, 0, 0, 100, 0, 0);

      const shares = await vault.balanceOf(user1.address);
      const assets = await vault.convertToAssets(shares);
      const expectedFee = (assets * 100n) / 10000n; // 1%

      const treasuryBalanceBefore = await usdc.balanceOf(treasury.address);

      await vault.connect(user1).redeem(shares, user1.address, user1.address);

      const treasuryBalanceAfter = await usdc.balanceOf(treasury.address);

      expect(treasuryBalanceAfter - treasuryBalanceBefore).to.be.closeTo(
        expectedFee,
        ethers.parseUnits("0.1", 6) // Margem de erro
      );
    });
  });

  describe("Oracle", function () {
    it("Should get oracle price correctly", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      // Esta função é internal, mas podemos testar via autoExit
      // que usa _checkOracle internamente

      // Por enquanto, apenas verificar que o oracle foi configurado
      const oracleAddress = await vault.chainlinkPriceFeed();
      expect(oracleAddress).to.not.equal(ethers.ZeroAddress);
    });

    it("Should reject stale oracle data", async function () {
      const { vault, keeper, chainlinkFeed } = await loadFixture(deployVaultFixture);

      await vault.setKeeper(keeper.address);

      // Avançar tempo para tornar oracle stale
      await time.increase(3601); // > maxOracleDelay (3600)

      // Tentar autoExit deve falhar
      await expect(
        vault.connect(keeper).autoExit(40000_00000000, 0)
      ).to.be.revertedWith("DeltaNeutralVault: oracle data too old");
    });
  });

  describe("Pause", function () {
    it("Should allow owner to pause", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      await expect(vault.pause())
        .to.emit(vault, "Paused");

      expect(await vault.paused()).to.be.true;
    });

    it("Should prevent deposits when paused", async function () {
      const { vault, usdc, user1 } = await loadFixture(deployVaultFixture);

      await vault.pause();

      const depositAmount = ethers.parseUnits("1000", 6);
      await usdc.connect(user1).approve(await vault.getAddress(), depositAmount);

      await expect(
        vault.connect(user1).deposit(depositAmount, user1.address)
      ).to.be.revertedWith("Pausable: paused");
    });

    it("Should allow owner to unpause", async function () {
      const { vault } = await loadFixture(deployVaultFixture);

      await vault.pause();

      await expect(vault.unpause())
        .to.emit(vault, "Unpaused");

      expect(await vault.paused()).to.be.false;
    });
  });

  describe("Management Fee", function () {
    it("Should accrue management fee over time", async function () {
      const { vault, usdc, treasury, user1 } = await loadFixture(deployVaultFixture);

      // Set management fee de 2% anual
      await vault.setFees(0, 200, 0, 0, 0, 0);

      // Deposit
      const depositAmount = ethers.parseUnits("10000", 6);
      await usdc.connect(user1).approve(await vault.getAddress(), depositAmount);
      await vault.connect(user1).deposit(depositAmount, user1.address);

      // Avançar 1 ano
      await time.increase(365 * 24 * 60 * 60);

      const treasurySharesBefore = await vault.balanceOf(treasury.address);

      // Trigger management fee (via deposit de outro user)
      await usdc.connect(user1).approve(await vault.getAddress(), ethers.parseUnits("1", 6));
      await vault.connect(user1).deposit(ethers.parseUnits("1", 6), user1.address);

      const treasurySharesAfter = await vault.balanceOf(treasury.address);

      // Treasury deve ter recebido shares equivalentes a ~2% dos assets
      expect(treasurySharesAfter).to.be.gt(treasurySharesBefore);
    });
  });
});
