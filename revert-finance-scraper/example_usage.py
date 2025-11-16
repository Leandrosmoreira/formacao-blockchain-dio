#!/usr/bin/env python3
"""
Exemplo de uso do scraper do Revert Finance
Mostra como usar o scraper programaticamente
"""

from scraper import RevertFinanceScraper


def example_single_url():
    """Exemplo: Extrair dados de uma única URL"""
    print("Exemplo 1: Extração de uma única URL")
    print("-" * 50)

    url = "https://revert.finance/#/uniswap-position/arbitrum/5066358"

    scraper = RevertFinanceScraper(headless=True)
    scraper.setup_driver()

    try:
        data = scraper.extract_page_data(url)
        print(f"\nDados extraídos: {data}")
    finally:
        scraper.driver.quit()


def example_multiple_urls():
    """Exemplo: Extrair dados de múltiplas URLs"""
    print("\nExemplo 2: Extração de múltiplas URLs")
    print("-" * 50)

    urls = [
        "https://revert.finance/#/uniswap-position/arbitrum/5066358",
        "https://revert.finance/#/uniswap-position/arbitrum/5003393",
    ]

    scraper = RevertFinanceScraper(headless=True)
    data = scraper.scrape_multiple_urls(urls)

    print(f"\nTotal de registros extraídos: {len(data)}")

    # Salva em CSV
    scraper.save_to_csv('example_output.csv')


def example_custom_urls():
    """Exemplo: Usar URLs personalizadas"""
    print("\nExemplo 3: URLs personalizadas")
    print("-" * 50)

    # Adicione suas próprias URLs aqui
    custom_urls = [
        "https://revert.finance/#/uniswap-position/arbitrum/YOUR_POSITION_ID",
    ]

    scraper = RevertFinanceScraper(headless=True)
    data = scraper.scrape_multiple_urls(custom_urls)

    # Processa os dados
    for item in data:
        print(f"\nPosition ID: {item.get('position_id')}")
        print(f"URL: {item.get('url')}")
        print(f"Campos extraídos: {len(item)}")

    scraper.save_to_csv('custom_output.csv')


if __name__ == "__main__":
    print("=" * 50)
    print("Exemplos de Uso do Revert Finance Scraper")
    print("=" * 50)

    # Descomente o exemplo que deseja executar:

    # example_single_url()
    example_multiple_urls()
    # example_custom_urls()

    print("\n✅ Exemplos concluídos!")
