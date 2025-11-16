.PHONY: help install run-selenium run-playwright clean

help:
	@echo "Revert Finance Web Scraper - Comandos disponíveis:"
	@echo ""
	@echo "  make install          - Instala todas as dependências"
	@echo "  make run-selenium     - Executa o scraper usando Selenium"
	@echo "  make run-playwright   - Executa o scraper usando Playwright"
	@echo "  make clean            - Remove arquivos gerados"
	@echo ""

install:
	@echo "📦 Instalando dependências..."
	@bash install.sh

run-selenium:
	@echo "🚀 Executando scraper com Selenium..."
	@python3 scraper.py

run-playwright:
	@echo "🚀 Executando scraper com Playwright..."
	@python3 scraper_playwright.py

clean:
	@echo "🧹 Limpando arquivos gerados..."
	@rm -f *.csv
	@rm -f debug_*.html
	@echo "✅ Limpeza concluída"
