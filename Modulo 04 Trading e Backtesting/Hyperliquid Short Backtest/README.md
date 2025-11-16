# Backtest de Estratégia Short na Hyperliquid

Backtest completo de uma estratégia de short em múltiplos tokens na Hyperliquid, considerando o impacto do funding rate no P&L.

## Índice

- [Sobre](#sobre)
- [Tokens Analisados](#tokens-analisados)
- [Como Funciona](#como-funciona)
- [Instalação](#instalação)
- [Uso](#uso)
- [Configurações](#configurações)
- [Resultados](#resultados)
- [FAQ](#faq)

## Sobre

Este projeto faz parte do **Módulo 04 - Trading e Backtesting** da Formação Blockchain DIO. O objetivo é demonstrar como realizar backtests de estratégias de trading em exchanges descentralizadas, especificamente a Hyperliquid.

### O que é Short?

Uma posição **short** (venda a descoberto) é uma estratégia onde você lucra quando o preço de um ativo **cai**.

**Exemplo:**
- Você abre short em ETH a $3,000
- ETH cai para $2,700
- Você lucrou $300 por ETH vendido

### O que é Funding Rate?

O **funding rate** é uma taxa periódica (geralmente a cada 8h) paga entre traders long e short para manter o preço do contrato perpétuo alinhado com o preço spot.

**Como funciona:**
- **Funding Rate Positivo**: Mercado está otimista (mais longs que shorts)
  - Longs pagam shorts → **Você RECEBE dinheiro**
- **Funding Rate Negativo**: Mercado está pessimista (mais shorts que longs)
  - Shorts pagam longs → **Você PAGA dinheiro**

### Por que isso é importante?

Em um short, além de lucrar com a queda do preço, você também pode:
- **Ganhar** funding rate quando o mercado está otimista demais (taxa positiva)
- **Perder** funding rate quando o mercado está pessimista (taxa negativa)

Este backtest calcula ambos os componentes do P&L.

## Tokens Analisados

O backtest analisa os seguintes tokens:

| Token | Nome | Tipo |
|-------|------|------|
| **WBTC** | Wrapped Bitcoin | BTC on Ethereum |
| **ETH** | Ethereum | Layer 1 |
| **UNI** | Uniswap | DEX Token |
| **LINK** | Chainlink | Oracle |
| **CRV** | Curve | DeFi |
| **GMX** | GMX | Perps DEX |

## Como Funciona

### Estratégia Implementada

1. **Entrada**: Abre posição short no início do período
2. **Holding**: Mantém a posição durante todo o período
3. **Funding**: Recebe/paga funding rate a cada 8h
4. **Saída**: Fecha posição no final do período

### Cálculo de P&L

```
P&L Total = P&L Preço + P&L Funding

Onde:
- P&L Preço = (Preço Entrada - Preço Saída) / Preço Entrada × Tamanho Posição
- P&L Funding = Σ (Funding Rate × Tamanho Posição)
```

### Métricas Calculadas

- **P&L de Preço**: Lucro/prejuízo da variação de preço
- **P&L de Funding**: Lucro/prejuízo acumulado de funding rates
- **P&L Total**: Soma dos dois acima
- **ROI**: Retorno sobre o investimento (%)
- **Win Rate**: Percentual de trades lucrativos

## Instalação

### 1. Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### 2. Instalar Dependências

```bash
# Navegue até o diretório
cd "Modulo 04 Trading e Backtesting/Hyperliquid Short Backtest"

# Instale as dependências
pip install -r requirements.txt
```

### 3. (Opcional) Instalar MCP Server

Para melhor performance e acesso a dados em tempo real, você pode instalar o servidor MCP da Hyperliquid:

```bash
# Veja instruções detalhadas em:
cat setup_mcp.md
```

**Nota**: O MCP server NÃO é obrigatório. O backtest funciona com a API pública também.

## Uso

### Execução Básica

```bash
python hyperliquid_short_backtest.py
```

Isso irá:
1. Buscar dados dos últimos 30 dias
2. Simular shorts em todos os 6 tokens
3. Calcular P&L incluindo funding rate
4. Gerar relatório consolidado
5. Salvar resultados em CSV

### Saída Esperada

```
🚀 Iniciando Backtest de Estratégia Short na Hyperliquid
============================================================

⚙️  Configurações:
   Tokens: WBTC, UNI, LINK, CRV, ETH, GMX
   Capital Inicial: $10,000.00
   Período: Últimos 30 dias
   Alocação por Token: 15%
   Estratégia: SHORT (lucra com queda de preço)

============================================================
Backtesting SHORT em WBTC
============================================================
Buscando dados de preço para WBTC...
Buscando funding rate para WBTC...

📊 Resultados para WBTC:
   Período: 30 dias (720 candles de 1h)
   Preço Entrada: $95,234.50
   Preço Saída: $89,123.00
   Variação Preço: -6.42%

💰 P&L:
   Tamanho Posição: $1,500.00
   P&L Preço: +$96.30
   P&L Funding: +$12.45
   P&L Total: +$108.75
   ROI: +7.25%

⚡ Funding Rate:
   Pagamentos: 90
   Rate Médio: 0.000092

[... resultados para outros tokens ...]

============================================================
📈 RESUMO CONSOLIDADO - ESTRATÉGIA SHORT
============================================================

💼 Capital Inicial: $10,000.00
   Total Investido: $9,000.00
   Total P&L: +$234.56
   ROI Médio: +2.61%
   Capital Final: $10,234.56

🏆 Melhor Performer:
   ETH: +$145.23 (+9.68%)

📉 Pior Performer:
   UNI: -$45.12 (-3.01%)

⚡ Estatísticas de Funding:
   Total Funding P&L: +$67.89
   Avg Funding Rate: 0.000087

📊 Performance:
   Trades Lucrativos: 4/6
   Win Rate: 66.7%

💾 Resultados salvos em: backtest_results_20250116_143025.csv
```

## Configurações

Você pode ajustar as configurações editando o arquivo `hyperliquid_short_backtest.py`:

```python
# No final do arquivo, função main():

# Lista de tokens para testar
TOKENS = ['WBTC', 'UNI', 'LINK', 'CRV', 'ETH', 'GMX']

# Capital inicial em USD
INITIAL_CAPITAL = 10000

# Quantos dias para trás analisar
DAYS_BACK = 30

# Percentual do capital alocado por token
POSITION_SIZE_PCT = 0.15  # 15%
```

### Exemplos de Customização

**Testar apenas ETH e BTC:**
```python
TOKENS = ['ETH', 'WBTC']
```

**Aumentar capital inicial:**
```python
INITIAL_CAPITAL = 50000  # $50k
```

**Testar últimos 90 dias:**
```python
DAYS_BACK = 90
```

**Aumentar alocação por token:**
```python
POSITION_SIZE_PCT = 0.25  # 25% por token
```

## Resultados

### Arquivo CSV

O backtest gera um arquivo CSV com todas as métricas:

```csv
coin,entry_price,exit_price,price_change_pct,position_size,price_pnl,funding_pnl,total_pnl,roi,num_funding_payments,avg_funding_rate,days_analyzed,num_candles
ETH,3245.67,3012.34,-7.19,1500.00,107.95,12.34,120.29,8.02,90,0.000091,30,720
WBTC,95234.50,89123.00,-6.42,1500.00,96.30,12.45,108.75,7.25,90,0.000092,30,720
...
```

### Análise dos Resultados

**O que observar:**

1. **Total P&L Positivo** = Estratégia lucrativa no período
2. **P&L Funding Positivo** = Mercado estava otimista (bom para shorts)
3. **Win Rate > 50%** = Mais trades lucrativos que perdedores
4. **ROI Individual** = Performance de cada token

**Interpretação:**

- Se **price_pnl** é positivo → Preço caiu (bom para short)
- Se **funding_pnl** é positivo → Você recebeu funding (mercado otimista)
- Se ambos positivos → Short perfeito!

## FAQ

### 1. Preciso de conta na Hyperliquid?

**Não!** Este backtest usa apenas dados públicos da API. Você não precisa de conta, chave privada ou qualquer credencial.

### 2. O backtest executa trades reais?

**Não!** É apenas uma simulação com dados históricos. Nenhum trade real é executado.

### 3. Qual a diferença entre usar MCP e API direta?

- **Com MCP**: Dados em tempo real, acesso mais rápido, mais ferramentas
- **Sem MCP**: Funciona perfeitamente, usa API pública, pode ser um pouco mais lento

Ambas as formas funcionam bem para backtesting.

### 4. Posso adicionar mais tokens?

Sim! Edite a variável `TOKENS` no código. Qualquer token disponível na Hyperliquid pode ser adicionado.

### 5. Como interpretar funding rate negativo?

- **Positivo**: Mercado otimista → Shorts RECEBEM dinheiro
- **Negativo**: Mercado pessimista → Shorts PAGAM dinheiro

Se o funding médio for negativo, significa que você pagou para manter o short.

### 6. Este backtest considera slippage e fees?

**Não**. Esta é uma versão simplificada para fins educacionais. Em trading real, você deve considerar:
- Taxas de abertura/fechamento (taker/maker fees)
- Slippage no preenchimento das ordens
- Custos de gas (se aplicável)

### 7. Posso usar isso para trading real?

Este código é **apenas educacional**. Se quiser usar em produção:
- Adicione gerenciamento de risco (stop loss, take profit)
- Implemente controle de alavancagem
- Considere fees e slippage
- Teste extensivamente
- Nunca arrisque mais do que pode perder

### 8. Onde encontro mais informações sobre Hyperliquid?

- **Documentação Oficial**: https://hyperliquid.gitbook.io/hyperliquid-docs
- **MCP Server**: https://github.com/caiovicentino/hyperliquid-mcp-server
- **Discord**: https://discord.gg/hyperliquid

## Próximos Passos

Ideias para expandir este projeto:

1. **Adicionar Visualizações**
   - Gráficos de P&L ao longo do tempo
   - Heatmap de correlação entre tokens
   - Distribuição de funding rates

2. **Estratégias Mais Avançadas**
   - Short dinâmico baseado em indicadores
   - Stop loss e take profit
   - Rebalanceamento de portfólio

3. **Análise de Risco**
   - Drawdown máximo
   - Sharpe ratio
   - Value at Risk (VaR)

4. **Backtesting Multi-período**
   - Testar em diferentes condições de mercado
   - Walk-forward analysis
   - Monte Carlo simulation

## Contribuindo

Este é um projeto educacional. Sugestões e melhorias são bem-vindas!

## Licença

MIT License - Livre para uso educacional e comercial.

## Autor

Parte da Formação Blockchain DIO - Módulo 04: Trading e Backtesting

---

**Disclaimer**: Este projeto é apenas para fins educacionais. Não constitui aconselhamento financeiro. Trading envolve risco de perda de capital.
