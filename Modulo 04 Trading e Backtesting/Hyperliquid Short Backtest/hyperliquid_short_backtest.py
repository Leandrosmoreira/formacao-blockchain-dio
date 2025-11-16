#!/usr/bin/env python3
"""
Backtest de Estratégia Short na Hyperliquid com Funding Rate

Este script realiza um backtest de uma estratégia de short em múltiplos tokens
na Hyperliquid, considerando o impacto do funding rate no P&L.

Tokens: WBTC, UNI, LINK, CRV, ETH, GMX
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import time


class HyperliquidAPI:
    """Cliente para interagir com a API da Hyperliquid"""

    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        self.session = requests.Session()

    def get_funding_history(self, coin: str, start_time: int, end_time: int = None) -> List[Dict]:
        """
        Obtém histórico de funding rate

        Args:
            coin: Nome do token (ex: 'ETH', 'BTC')
            start_time: Timestamp de início em milissegundos
            end_time: Timestamp de fim em milissegundos (opcional)
        """
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_time
        }

        if end_time:
            payload["endTime"] = end_time

        try:
            response = self.session.post(self.base_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao buscar funding history para {coin}: {e}")
            return []

    def get_candles(self, coin: str, interval: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Obtém dados de candles (OHLCV)

        Args:
            coin: Nome do token
            interval: Intervalo dos candles ('1h', '4h', '1d')
            start_time: Timestamp de início em milissegundos
            end_time: Timestamp de fim em milissegundos
        """
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time
            }
        }

        try:
            response = self.session.post(self.base_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao buscar candles para {coin}: {e}")
            return []

    def get_meta(self) -> Dict:
        """Obtém metadados dos mercados disponíveis"""
        payload = {"type": "meta"}

        try:
            response = self.session.post(self.base_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao buscar meta: {e}")
            return {}


class ShortBacktest:
    """
    Classe para realizar backtest de estratégia short com funding rate
    """

    def __init__(self, initial_capital: float = 10000):
        """
        Args:
            initial_capital: Capital inicial em USD
        """
        self.api = HyperliquidAPI()
        self.initial_capital = initial_capital
        self.results = {}

    def calculate_short_pnl(self, entry_price: float, exit_price: float,
                           position_size: float, funding_paid: float) -> Dict:
        """
        Calcula P&L de uma posição short

        Args:
            entry_price: Preço de entrada
            exit_price: Preço de saída
            position_size: Tamanho da posição em USD
            funding_paid: Total de funding pago/recebido

        Returns:
            Dict com métricas de P&L
        """
        # Short lucra quando preço cai
        price_pnl = (entry_price - exit_price) / entry_price * position_size

        # Funding rate: positivo = você recebe, negativo = você paga
        total_pnl = price_pnl + funding_paid

        return {
            'price_pnl': price_pnl,
            'funding_pnl': funding_paid,
            'total_pnl': total_pnl,
            'roi': (total_pnl / position_size) * 100
        }

    def backtest_token(self, coin: str, days_back: int = 30,
                      position_size_pct: float = 0.15) -> Dict:
        """
        Realiza backtest de short em um token específico

        Args:
            coin: Nome do token
            days_back: Quantos dias para trás analisar
            position_size_pct: Percentual do capital para alocar (ex: 0.15 = 15%)

        Returns:
            Dict com resultados do backtest
        """
        print(f"\n{'='*60}")
        print(f"Backtesting SHORT em {coin}")
        print(f"{'='*60}")

        # Calcular timestamps
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

        # Buscar dados de preço (candles de 1 hora)
        print(f"Buscando dados de preço para {coin}...")
        candles = self.api.get_candles(coin, "1h", start_time, end_time)

        if not candles:
            print(f"⚠️  Sem dados de candles para {coin}")
            return None

        # Processar candles
        df_price = pd.DataFrame(candles)
        if len(df_price) == 0:
            print(f"⚠️  DataFrame vazio para {coin}")
            return None

        # Converter timestamp e ordenar
        df_price['time'] = pd.to_datetime(df_price['t'], unit='ms')
        df_price = df_price.sort_values('time')

        # Buscar funding rate
        print(f"Buscando funding rate para {coin}...")
        funding_history = self.api.get_funding_history(coin, start_time, end_time)

        # Processar funding
        df_funding = pd.DataFrame(funding_history) if funding_history else pd.DataFrame()

        # Calcular tamanho da posição
        position_size = self.initial_capital * position_size_pct

        # Preços de entrada e saída
        entry_price = float(df_price.iloc[0]['c'])  # Primeiro close
        exit_price = float(df_price.iloc[-1]['c'])  # Último close

        # Calcular funding pago/recebido
        total_funding = 0
        if len(df_funding) > 0 and 'fundingRate' in df_funding.columns:
            # Funding rate é aplicado no valor da posição
            # Rate positivo = short recebe, rate negativo = short paga
            for _, row in df_funding.iterrows():
                funding_rate = float(row['fundingRate'])
                total_funding += funding_rate * position_size

        # Calcular P&L
        pnl = self.calculate_short_pnl(entry_price, exit_price, position_size, total_funding)

        # Métricas adicionais
        price_change_pct = ((exit_price - entry_price) / entry_price) * 100
        num_funding_payments = len(df_funding)
        avg_funding_rate = df_funding['fundingRate'].astype(float).mean() if len(df_funding) > 0 else 0

        results = {
            'coin': coin,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'price_change_pct': price_change_pct,
            'position_size': position_size,
            'price_pnl': pnl['price_pnl'],
            'funding_pnl': pnl['funding_pnl'],
            'total_pnl': pnl['total_pnl'],
            'roi': pnl['roi'],
            'num_funding_payments': num_funding_payments,
            'avg_funding_rate': avg_funding_rate,
            'days_analyzed': days_back,
            'num_candles': len(df_price)
        }

        # Exibir resultados
        self._print_token_results(results)

        return results

    def _print_token_results(self, results: Dict):
        """Exibe resultados formatados para um token"""
        print(f"\n📊 Resultados para {results['coin']}:")
        print(f"   Período: {results['days_analyzed']} dias ({results['num_candles']} candles de 1h)")
        print(f"   Preço Entrada: ${results['entry_price']:,.2f}")
        print(f"   Preço Saída: ${results['exit_price']:,.2f}")
        print(f"   Variação Preço: {results['price_change_pct']:+.2f}%")
        print(f"\n💰 P&L:")
        print(f"   Tamanho Posição: ${results['position_size']:,.2f}")
        print(f"   P&L Preço: ${results['price_pnl']:+,.2f}")
        print(f"   P&L Funding: ${results['funding_pnl']:+,.2f}")
        print(f"   P&L Total: ${results['total_pnl']:+,.2f}")
        print(f"   ROI: {results['roi']:+.2f}%")
        print(f"\n⚡ Funding Rate:")
        print(f"   Pagamentos: {results['num_funding_payments']}")
        print(f"   Rate Médio: {results['avg_funding_rate']:.6f}")

    def run_backtest(self, tokens: List[str], days_back: int = 30,
                    position_size_pct: float = 0.15) -> pd.DataFrame:
        """
        Executa backtest para múltiplos tokens

        Args:
            tokens: Lista de tokens para testar
            days_back: Dias para trás
            position_size_pct: Percentual do capital por token

        Returns:
            DataFrame com resultados consolidados
        """
        results = []

        for token in tokens:
            try:
                result = self.backtest_token(token, days_back, position_size_pct)
                if result:
                    results.append(result)
                # Pequeno delay para não sobrecarregar a API
                time.sleep(0.5)
            except Exception as e:
                print(f"❌ Erro ao processar {token}: {e}")
                continue

        if not results:
            print("\n❌ Nenhum resultado obtido!")
            return pd.DataFrame()

        # Criar DataFrame com resultados
        df_results = pd.DataFrame(results)

        # Exibir resumo consolidado
        self._print_summary(df_results)

        # Salvar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"backtest_results_{timestamp}.csv"
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Resultados salvos em: {output_file}")

        return df_results

    def _print_summary(self, df: pd.DataFrame):
        """Exibe resumo consolidado dos resultados"""
        print(f"\n{'='*60}")
        print("📈 RESUMO CONSOLIDADO - ESTRATÉGIA SHORT")
        print(f"{'='*60}")

        total_pnl = df['total_pnl'].sum()
        total_invested = df['position_size'].sum()
        avg_roi = df['roi'].mean()

        print(f"\n💼 Capital Inicial: ${self.initial_capital:,.2f}")
        print(f"   Total Investido: ${total_invested:,.2f}")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   ROI Médio: {avg_roi:+.2f}%")
        print(f"   Capital Final: ${self.initial_capital + total_pnl:,.2f}")

        # Melhores e piores performers
        best = df.loc[df['total_pnl'].idxmax()]
        worst = df.loc[df['total_pnl'].idxmin()]

        print(f"\n🏆 Melhor Performer:")
        print(f"   {best['coin']}: ${best['total_pnl']:+,.2f} ({best['roi']:+.2f}%)")

        print(f"\n📉 Pior Performer:")
        print(f"   {worst['coin']}: ${worst['total_pnl']:+,.2f} ({worst['roi']:+.2f}%)")

        # Estatísticas de funding
        print(f"\n⚡ Estatísticas de Funding:")
        print(f"   Total Funding P&L: ${df['funding_pnl'].sum():+,.2f}")
        print(f"   Avg Funding Rate: {df['avg_funding_rate'].mean():.6f}")

        # Win rate
        winners = len(df[df['total_pnl'] > 0])
        total = len(df)
        win_rate = (winners / total) * 100 if total > 0 else 0

        print(f"\n📊 Performance:")
        print(f"   Trades Lucrativos: {winners}/{total}")
        print(f"   Win Rate: {win_rate:.1f}%")


def main():
    """Função principal"""
    print("🚀 Iniciando Backtest de Estratégia Short na Hyperliquid")
    print("="*60)

    # Configurações
    TOKENS = ['WBTC', 'UNI', 'LINK', 'CRV', 'ETH', 'GMX']
    INITIAL_CAPITAL = 10000  # USD
    DAYS_BACK = 30  # Últimos 30 dias
    POSITION_SIZE_PCT = 0.15  # 15% do capital por token

    print(f"\n⚙️  Configurações:")
    print(f"   Tokens: {', '.join(TOKENS)}")
    print(f"   Capital Inicial: ${INITIAL_CAPITAL:,.2f}")
    print(f"   Período: Últimos {DAYS_BACK} dias")
    print(f"   Alocação por Token: {POSITION_SIZE_PCT*100:.0f}%")
    print(f"   Estratégia: SHORT (lucra com queda de preço)")

    # Executar backtest
    backtest = ShortBacktest(initial_capital=INITIAL_CAPITAL)
    results = backtest.run_backtest(
        tokens=TOKENS,
        days_back=DAYS_BACK,
        position_size_pct=POSITION_SIZE_PCT
    )

    print("\n✅ Backtest concluído!")

    return results


if __name__ == "__main__":
    main()
