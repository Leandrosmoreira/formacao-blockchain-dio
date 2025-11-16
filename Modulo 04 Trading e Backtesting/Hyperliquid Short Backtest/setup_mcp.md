# Instalação do Hyperliquid MCP Server

Este guia explica como instalar e configurar o servidor MCP da Hyperliquid para usar com o backtest.

## O que é MCP?

MCP (Model Context Protocol) é um protocolo que permite integrar ferramentas externas com Claude. O servidor MCP da Hyperliquid fornece acesso direto às funcionalidades da exchange.

## Instalação

### 1. Clonar o Repositório

```bash
git clone https://github.com/caiovicentino/hyperliquid-mcp-server.git
cd hyperliquid-mcp-server
```

### 2. Instalação Automática (Recomendado)

```bash
python3 setup.py
```

Este script irá:
- Criar ambiente virtual Python
- Instalar dependências
- Configurar Claude Desktop automaticamente

### 3. Configurar Variáveis de Ambiente

Edite o arquivo `.env` criado:

```bash
HYPERLIQUID_PRIVATE_KEY=0x...  # Sua chave privada (OPCIONAL para backtest)
HYPERLIQUID_ACCOUNT_ADDRESS=0x...  # Seu endereço (OPCIONAL para backtest)
HYPERLIQUID_NETWORK=mainnet  # ou testnet
```

**IMPORTANTE**: Para apenas rodar backtests e buscar dados de mercado, você **NÃO precisa** fornecer chave privada. As ferramentas de dados de mercado são públicas.

## Ferramentas Disponíveis para Backtest

O MCP server fornece as seguintes ferramentas úteis para backtesting:

### 1. `get_candles`
Obtém dados históricos de preços (OHLCV)

**Parâmetros:**
- `coin`: Nome do token (ex: "ETH", "BTC")
- `interval`: Intervalo ("1m", "5m", "15m", "1h", "4h", "1d")
- `startTime`: Timestamp de início (ms)
- `endTime`: Timestamp de fim (ms)

### 2. `get_funding_rates`
Obtém funding rates atuais ou históricos

**Parâmetros:**
- `coin`: Nome do token (OPCIONAL, se omitido retorna todos)

### 3. `get_all_mids`
Obtém preços médios atuais de todos os tokens

### 4. `get_asset_contexts`
Obtém contextos detalhados dos ativos (funding rate, open interest, etc.)

## Uso no Backtest

Após instalar o MCP server, o script de backtest irá automaticamente:

1. Detectar se o MCP server está disponível
2. Usar as ferramentas MCP para buscar dados
3. Executar o backtest com os dados obtidos

## Testando a Instalação

Após instalar, você pode testar se está funcionando:

```bash
# No terminal do Claude Code
python hyperliquid_short_backtest.py
```

O script irá informar se está usando MCP ou API direta.

## Troubleshooting

### Erro: "MCP server não encontrado"
- Verifique se executou `python3 setup.py`
- Reinicie o Claude Desktop

### Erro: "Falha ao conectar"
- Verifique sua conexão com internet
- Certifique-se que o `HYPERLIQUID_NETWORK` está correto no `.env`

### Para apenas consultar dados (sem trading)
Você pode deixar `HYPERLIQUID_PRIVATE_KEY` vazio. As APIs públicas funcionarão normalmente.

## Recursos

- **Repositório MCP**: https://github.com/caiovicentino/hyperliquid-mcp-server
- **Documentação Hyperliquid**: https://hyperliquid.gitbook.io/hyperliquid-docs
- **MCP Protocol**: https://modelcontextprotocol.io

## Próximos Passos

Depois de configurar o MCP server:

1. Execute o backtest: `python hyperliquid_short_backtest.py`
2. Analise os resultados gerados em CSV
3. Ajuste parâmetros conforme necessário

## Alternativa: Uso Sem MCP

Se você não quiser instalar o MCP server, o backtest também funciona fazendo chamadas diretas à API pública da Hyperliquid. A única diferença é que algumas chamadas podem ser um pouco mais lentas.
