#!/usr/bin/env python3
"""
Web Scraper alternativo usando Playwright para extrair dados do Revert Finance
Mais eficiente para SPAs modernas e pode interceptar requisições de rede
"""

import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime
import csv


try:
    from playwright.async_api import async_playwright, Page, Browser
    import pandas as pd
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright não está instalado. Execute: pip install playwright && playwright install")


class RevertFinanceScraperPlaywright:
    """Scraper usando Playwright para extrair dados do Revert Finance"""

    def __init__(self, headless: bool = True):
        """
        Inicializa o scraper

        Args:
            headless: Se True, executa o navegador em modo headless
        """
        self.headless = headless
        self.all_data = []
        self.network_requests = []

    async def extract_page_data(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Extrai todos os dados de uma página

        Args:
            page: Página do Playwright
            url: URL da página

        Returns:
            Dicionário com os dados extraídos
        """
        print(f"\nExtraindo dados de: {url}")

        data = {
            'url': url,
            'position_id': url.split('/')[-1],
            'timestamp': datetime.now().isoformat(),
        }

        # Intercepta requisições de rede
        network_data = []

        async def handle_response(response):
            """Captura respostas de API"""
            if 'api' in response.url or 'graph' in response.url or 'json' in response.url:
                try:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            json_data = await response.json()
                            network_data.append({
                                'url': response.url,
                                'data': json_data
                            })
                            print(f"  📡 API capturada: {response.url[:80]}...")
                except Exception as e:
                    pass

        page.on('response', handle_response)

        try:
            # Navega para a página
            await page.goto(url, wait_until='networkidle', timeout=60000)

            # Aguarda um pouco mais para garantir que todo o JavaScript foi executado
            await page.wait_for_timeout(5000)

            # Extrai o conteúdo da página
            content = await page.content()

            # Salva o HTML para debug
            with open(f'revert-finance-scraper/debug_playwright_{data["position_id"]}.html', 'w', encoding='utf-8') as f:
                f.write(content)

            # Tenta extrair dados estruturados
            # 1. Extrai todas as tabelas
            tables = await page.locator('table').all()
            for idx, table in enumerate(tables):
                try:
                    table_text = await table.inner_text()
                    if table_text.strip():
                        data[f'table_{idx+1}'] = table_text
                except:
                    pass

            # 2. Extrai pares de label-valor comuns em interfaces DeFi
            # Procura por elementos que possam conter informações de posição
            selectors = [
                'div[class*="position"]',
                'div[class*="pool"]',
                'div[class*="info"]',
                'div[class*="detail"]',
                'div[class*="stat"]',
                'div[class*="metric"]',
                'div[class*="value"]',
                'div[class*="amount"]',
            ]

            for selector in selectors:
                try:
                    elements = await page.locator(selector).all()
                    for element in elements:
                        text = await element.inner_text()
                        if text and '\n' in text:
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if len(lines) >= 2:
                                key = lines[0].lower().replace(' ', '_').replace(':', '').replace('-', '_')
                                if key and len(key) < 50:
                                    value = ' | '.join(lines[1:])
                                    if key not in data:
                                        data[key] = value
                except:
                    pass

            # 3. Extrai dados específicos usando JavaScript
            try:
                # Tenta extrair todos os dados visíveis na página
                all_text = await page.evaluate('''() => {
                    return document.body.innerText;
                }''')

                # Procura por padrões específicos
                keywords = {
                    'token0': ['Token 0', 'Token A', 'Base Token'],
                    'token1': ['Token 1', 'Token B', 'Quote Token'],
                    'fee_tier': ['Fee Tier', 'Fee', 'Pool Fee'],
                    'liquidity': ['Liquidity', 'Total Liquidity'],
                    'tvl': ['TVL', 'Total Value Locked'],
                    'position_value': ['Position Value', 'Value'],
                    'unclaimed_fees': ['Unclaimed Fees', 'Fees'],
                    'price_range': ['Price Range', 'Range'],
                    'current_price': ['Current Price', 'Price'],
                }

                for key, patterns in keywords.items():
                    for pattern in patterns:
                        if pattern in all_text and key not in data:
                            # Tenta encontrar o valor após o padrão
                            idx = all_text.find(pattern)
                            if idx != -1:
                                # Pega os próximos 100 caracteres
                                snippet = all_text[idx:idx+100]
                                data[key] = snippet[:50]  # Limita o tamanho

            except Exception as e:
                print(f"  ⚠️  Erro ao extrair dados com JavaScript: {e}")

            # 4. Adiciona dados de rede capturados
            if network_data:
                data['network_requests'] = network_data
                print(f"  📊 {len(network_data)} requisições de API capturadas")

                # Tenta extrair dados úteis das respostas de API
                for idx, req in enumerate(network_data):
                    req_data = req.get('data', {})
                    if isinstance(req_data, dict):
                        # Adiciona dados da API ao dataset principal
                        for k, v in req_data.items():
                            if isinstance(v, (str, int, float, bool)):
                                api_key = f'api_{idx}_{k}'
                                data[api_key] = str(v)

            print(f"  ✅ {len(data)} campos extraídos")

        except Exception as e:
            print(f"  ❌ Erro ao extrair dados: {e}")
            data['error'] = str(e)

        return data

    async def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extrai dados de múltiplas URLs

        Args:
            urls: Lista de URLs para extrair

        Returns:
            Lista de dicionários com os dados extraídos
        """
        async with async_playwright() as p:
            # Lança o navegador
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            # Cria um contexto com user-agent real
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            page = await context.new_page()

            try:
                for url in urls:
                    try:
                        data = await self.extract_page_data(page, url)
                        self.all_data.append(data)
                        # Aguarda entre requisições
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"❌ Erro ao processar {url}: {e}")
                        self.all_data.append({
                            'url': url,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
            finally:
                await browser.close()

        return self.all_data

    def save_to_csv(self, filename: str = 'revert_finance_data_playwright.csv'):
        """
        Salva os dados extraídos em um arquivo CSV

        Args:
            filename: Nome do arquivo CSV
        """
        if not self.all_data:
            print("Nenhum dado para salvar")
            return

        # Processa os dados para remover objetos complexos
        processed_data = []
        for item in self.all_data:
            processed_item = {}
            for key, value in item.items():
                if key == 'network_requests':
                    # Converte para JSON string
                    processed_item[key] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, (list, dict)):
                    processed_item[key] = json.dumps(value, ensure_ascii=False)
                else:
                    processed_item[key] = value
            processed_data.append(processed_item)

        # Converte para DataFrame
        df = pd.DataFrame(processed_data)

        # Salva em CSV
        output_path = f'revert-finance-scraper/{filename}'
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n✅ Dados salvos em: {output_path}")
        print(f"📊 Total de registros: {len(df)}")
        print(f"📋 Total de campos: {len(df.columns)}")

        return output_path


async def main():
    """Função principal"""

    if not PLAYWRIGHT_AVAILABLE:
        print("\n❌ Playwright não está instalado.")
        print("\nPara instalar, execute:")
        print("  pip install playwright pandas")
        print("  playwright install chromium")
        return

    # URLs fornecidas
    urls = [
        "https://revert.finance/#/uniswap-position/arbitrum/5066358",
        "https://revert.finance/#/uniswap-position/arbitrum/5003393",
        "https://revert.finance/#/uniswap-position/arbitrum/4990853",
        "https://revert.finance/#/uniswap-position/arbitrum/5020274",
        "https://revert.finance/#/uniswap-position/arbitrum/4807618",
        "https://revert.finance/#/uniswap-position/arbitrum/4883063",
        "https://revert.finance/#/uniswap-position/arbitrum/892272",
    ]

    print("=" * 80)
    print("🔍 Revert Finance Web Scraper (Playwright)")
    print("=" * 80)
    print(f"\n📌 Total de URLs para processar: {len(urls)}")

    # Cria o scraper
    scraper = RevertFinanceScraperPlaywright(headless=True)

    # Extrai os dados
    print("\n🚀 Iniciando extração de dados...")
    await scraper.scrape_multiple_urls(urls)

    # Salva em CSV
    scraper.save_to_csv('revert_finance_positions_playwright.csv')

    print("\n" + "=" * 80)
    print("✅ Extração concluída!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
