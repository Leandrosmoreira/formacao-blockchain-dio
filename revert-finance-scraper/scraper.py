#!/usr/bin/env python3
"""
Web Scraper para extrair dados de posições Uniswap do Revert Finance
Extrai dados de pools de liquidez e posições de usuários
"""

import time
import csv
from typing import List, Dict, Any
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd


class RevertFinanceScraper:
    """Scraper para extrair dados do Revert Finance"""

    def __init__(self, headless: bool = True):
        """
        Inicializa o scraper

        Args:
            headless: Se True, executa o navegador em modo headless (sem interface gráfica)
        """
        self.headless = headless
        self.driver = None
        self.all_data = []

    def setup_driver(self):
        """Configura o WebDriver do Chrome"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Instala e configura o ChromeDriver automaticamente
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)

    def wait_for_page_load(self, timeout: int = 30):
        """
        Aguarda o carregamento da página

        Args:
            timeout: Tempo máximo de espera em segundos
        """
        try:
            # Aguarda até que o body esteja presente
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # Aguarda um pouco mais para garantir que o JavaScript foi executado
            time.sleep(5)
        except TimeoutException:
            print(f"Timeout ao carregar a página após {timeout} segundos")

    def extract_text_safe(self, element, selector: str, by=By.CSS_SELECTOR) -> str:
        """
        Extrai texto de um elemento de forma segura

        Args:
            element: Elemento pai
            selector: Seletor CSS ou XPath
            by: Tipo de seletor (padrão: CSS_SELECTOR)

        Returns:
            Texto do elemento ou string vazia se não encontrado
        """
        try:
            return element.find_element(by, selector).text.strip()
        except (NoSuchElementException, AttributeError):
            return ""

    def extract_page_data(self, url: str) -> Dict[str, Any]:
        """
        Extrai todos os dados de uma página

        Args:
            url: URL da página a ser extraída

        Returns:
            Dicionário com os dados extraídos
        """
        print(f"\nExtraindo dados de: {url}")
        self.driver.get(url)
        self.wait_for_page_load()

        data = {
            'url': url,
            'position_id': url.split('/')[-1],
            'timestamp': datetime.now().isoformat(),
        }

        try:
            # Extrai o HTML completo da página para análise
            page_source = self.driver.page_source

            # Tenta extrair dados gerais visíveis na página
            # Procura por todos os elementos de texto visíveis
            body = self.driver.find_element(By.TAG_NAME, "body")

            # Extrai todas as tabelas
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            for idx, table in enumerate(tables):
                table_data = []
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if not cells:
                            cells = row.find_elements(By.TAG_NAME, "th")
                        if cells:
                            row_data = [cell.text.strip() for cell in cells]
                            if any(row_data):  # Ignora linhas vazias
                                table_data.append(row_data)

                    if table_data:
                        data[f'table_{idx+1}'] = table_data
                except Exception as e:
                    print(f"Erro ao extrair tabela {idx+1}: {e}")

            # Extrai informações específicas comuns em páginas Uniswap/DeFi
            # Procura por labels e valores
            labels_selectors = [
                "label", "dt", "th",
                "[class*='label']", "[class*='title']",
                "[class*='header']", "[class*='name']"
            ]

            values_selectors = [
                "dd", "td", "span", "div",
                "[class*='value']", "[class*='amount']",
                "[class*='balance']", "[class*='price']"
            ]

            # Tenta encontrar pares label-valor
            for label_sel in labels_selectors:
                try:
                    labels = self.driver.find_elements(By.CSS_SELECTOR, label_sel)
                    for label in labels:
                        label_text = label.text.strip()
                        if label_text and len(label_text) > 0 and len(label_text) < 100:
                            # Tenta encontrar o valor correspondente
                            try:
                                # Procura no próximo elemento irmão
                                value_element = self.driver.execute_script(
                                    "return arguments[0].nextElementSibling;", label
                                )
                                if value_element:
                                    value_text = value_element.text.strip()
                                    if value_text:
                                        key = label_text.lower().replace(' ', '_').replace(':', '')
                                        if key not in data:
                                            data[key] = value_text
                            except:
                                pass
                except:
                    pass

            # Extrai todos os divs com informações potencialmente úteis
            divs = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='info'], div[class*='detail'], div[class*='stat']")
            for div in divs:
                text = div.text.strip()
                if text and '\n' in text:
                    lines = text.split('\n')
                    if len(lines) == 2:
                        key = lines[0].lower().replace(' ', '_').replace(':', '')
                        if key and len(key) < 50:
                            data[key] = lines[1]

            # Procura especificamente por informações comuns em pools Uniswap
            keywords = [
                'token', 'pair', 'pool', 'fee', 'liquidity', 'volume',
                'price', 'tvl', 'apr', 'apy', 'position', 'range',
                'tick', 'amount', 'value', 'balance', 'unclaimed',
                'collected', 'network', 'chain'
            ]

            all_text = body.text

            print(f"Dados extraídos: {len(data)} campos encontrados")

            # Salva um snapshot do HTML para debug
            with open(f'revert-finance-scraper/debug_{data["position_id"]}.html', 'w', encoding='utf-8') as f:
                f.write(page_source)

        except Exception as e:
            print(f"Erro ao extrair dados: {e}")
            data['error'] = str(e)

        return data

    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extrai dados de múltiplas URLs

        Args:
            urls: Lista de URLs para extrair

        Returns:
            Lista de dicionários com os dados extraídos
        """
        self.setup_driver()

        try:
            for url in urls:
                try:
                    data = self.extract_page_data(url)
                    self.all_data.append(data)
                    # Aguarda entre requisições para evitar rate limiting
                    time.sleep(3)
                except Exception as e:
                    print(f"Erro ao processar {url}: {e}")
                    self.all_data.append({
                        'url': url,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
        finally:
            if self.driver:
                self.driver.quit()

        return self.all_data

    def save_to_csv(self, filename: str = 'revert_finance_data.csv'):
        """
        Salva os dados extraídos em um arquivo CSV

        Args:
            filename: Nome do arquivo CSV
        """
        if not self.all_data:
            print("Nenhum dado para salvar")
            return

        # Converte para DataFrame do pandas
        df = pd.DataFrame(self.all_data)

        # Salva em CSV
        output_path = f'revert-finance-scraper/{filename}'
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\nDados salvos em: {output_path}")
        print(f"Total de registros: {len(df)}")
        print(f"Total de campos: {len(df.columns)}")

        return output_path


def main():
    """Função principal"""

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
    print("Revert Finance Web Scraper")
    print("=" * 80)
    print(f"\nTotal de URLs para processar: {len(urls)}")

    # Cria o scraper
    scraper = RevertFinanceScraper(headless=True)

    # Extrai os dados
    print("\nIniciando extração de dados...")
    scraper.scrape_multiple_urls(urls)

    # Salva em CSV
    scraper.save_to_csv('revert_finance_positions.csv')

    print("\n" + "=" * 80)
    print("Extração concluída!")
    print("=" * 80)


if __name__ == "__main__":
    main()
