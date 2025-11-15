const hre = require("hardhat");

async function main() {
  console.log("🚀 Iniciando deploy do DeltaNeutralVaultV1...\n");

  // ========================================
  // CONFIGURAÇÃO - AJUSTE ESTES ENDEREÇOS
  // ========================================

  // ⚠️ ATENÇÃO: Ajuste estes endereços conforme sua rede!

  // Exemplo: Sepolia Testnet
  const USDC_ADDRESS = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"; // Sepolia USDC
  const CHAINLINK_FEED = "0x1b44F3514812d835EB1BDB0acB33d3fA3351Ee43"; // BTC/USD Sepolia

  // ⚠️ ALTERE PARA SEU ENDEREÇO
  const [deployer] = await hre.ethers.getSigners();
  const TREASURY_ADDRESS = deployer.address; // Por padrão, usa o deployer

  const VAULT_NAME = "Delta Neutral Vault Shares";
  const VAULT_SYMBOL = "dnvUSDC";

  console.log("📋 Configuração:");
  console.log("- Deployer:", deployer.address);
  console.log("- Network:", hre.network.name);
  console.log("- USDC:", USDC_ADDRESS);
  console.log("- Chainlink Feed:", CHAINLINK_FEED);
  console.log("- Treasury:", TREASURY_ADDRESS);
  console.log("");

  // Verificar saldo
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("💰 Saldo do deployer:", hre.ethers.formatEther(balance), "ETH\n");

  if (balance === 0n) {
    console.error("❌ Erro: Saldo insuficiente para deploy!");
    console.error("Por favor, adicione fundos na carteira:", deployer.address);
    process.exit(1);
  }

  // ========================================
  // DEPLOY
  // ========================================

  const DeltaNeutralVaultV1 = await hre.ethers.getContractFactory("DeltaNeutralVaultV1");

  console.log("📦 Fazendo deploy do contrato...");
  console.log("⏳ Aguarde...\n");

  const vault = await DeltaNeutralVaultV1.deploy(
    USDC_ADDRESS,
    VAULT_NAME,
    VAULT_SYMBOL,
    CHAINLINK_FEED,
    TREASURY_ADDRESS
  );

  await vault.waitForDeployment();
  const vaultAddress = await vault.getAddress();

  console.log("✅ DeltaNeutralVaultV1 deployed to:", vaultAddress);
  console.log("\n📋 Informações do Deploy:");
  console.log("├─ Asset (USDC):", USDC_ADDRESS);
  console.log("├─ Chainlink Feed:", CHAINLINK_FEED);
  console.log("├─ Treasury:", TREASURY_ADDRESS);
  console.log("├─ Nome:", VAULT_NAME);
  console.log("└─ Símbolo:", VAULT_SYMBOL);

  // ========================================
  // CONFIGURAÇÃO INICIAL
  // ========================================

  console.log("\n⚙️ Configurando vault...\n");

  // Definir keeper (por enquanto, o deployer)
  const tx1 = await vault.setKeeper(deployer.address);
  await tx1.wait();
  console.log("✅ Keeper definido:", deployer.address);

  // Definir fees (valores conservadores)
  const tx2 = await vault.setFees(
    2000, // 20% performance fee
    200,  // 2% management fee (anual)
    50,   // 0.5% entry fee
    50,   // 0.5% exit fee
    30,   // 0.3% swap fee
    10    // 0.1% keeper fee
  );
  await tx2.wait();
  console.log("✅ Fees configuradas:");
  console.log("   ├─ Performance: 20%");
  console.log("   ├─ Management: 2% (anual)");
  console.log("   ├─ Entry: 0.5%");
  console.log("   ├─ Exit: 0.5%");
  console.log("   ├─ Swap: 0.3%");
  console.log("   └─ Keeper: 0.1%");

  // ========================================
  // RESUMO
  // ========================================

  console.log("\n" + "=".repeat(60));
  console.log("🎉 DEPLOY COMPLETO!");
  console.log("=".repeat(60));
  console.log("\n📝 Endereço do Contrato:");
  console.log("   " + vaultAddress);
  console.log("\n⚠️ IMPORTANTE - ETAPA 1:");
  console.log("   Este contrato está na Etapa 1 (base/estrutura)");
  console.log("   As funções de Uniswap v3 são STUBS (não funcionam ainda)");
  console.log("\n✅ O que funciona:");
  console.log("   ├─ Deposit/Withdraw de USDC");
  console.log("   ├─ Cobrança de entry/exit fees");
  console.log("   ├─ Validação de oracles Chainlink");
  console.log("   └─ Sistema de permissões");
  console.log("\n❌ O que NÃO funciona ainda:");
  console.log("   ├─ Abrir posições LP no Uniswap v3");
  console.log("   ├─ Fechar posições LP");
  console.log("   ├─ Swaps automáticos");
  console.log("   └─ autoExit/autoReenter completos");

  console.log("\n📋 Próximos passos:");
  console.log("   1. Criar ou encontrar pool WBTC/USDC no Uniswap v3");
  console.log("   2. Chamar setUniswapPool(poolAddress)");
  console.log("   3. Chamar setRange(tickLower, tickUpper)");
  console.log("   4. Implementar Etapa 2 para funcionalidade completa");

  console.log("\n💡 Para configurar o pool:");
  console.log("   const vault = await ethers.getContractAt('DeltaNeutralVaultV1', '" + vaultAddress + "');");
  console.log("   await vault.setUniswapPool('0xPoolAddress');");
  console.log("   await vault.setRange(-887220, 887220); // Full range");

  console.log("\n🔗 Links úteis:");
  console.log("   - Uniswap v3: https://app.uniswap.org/pools");
  console.log("   - Chainlink Feeds: https://docs.chain.link/data-feeds");
  console.log("\n" + "=".repeat(60) + "\n");

  // Salvar endereços em arquivo
  const fs = require("fs");
  const deployData = {
    network: hre.network.name,
    vault: vaultAddress,
    usdc: USDC_ADDRESS,
    chainlinkFeed: CHAINLINK_FEED,
    treasury: TREASURY_ADDRESS,
    deployer: deployer.address,
    timestamp: new Date().toISOString()
  };

  fs.writeFileSync(
    "deployment.json",
    JSON.stringify(deployData, null, 2)
  );
  console.log("💾 Endereços salvos em: deployment.json\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n❌ Erro no deploy:");
    console.error(error);
    process.exit(1);
  });
