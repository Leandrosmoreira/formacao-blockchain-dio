# Revert Finance Web Scraper

Web scraper para extrair dados de posições Uniswap do Revert Finance e exportar para CSV.

## Descrição

Este scraper extrai dados de pools de liquidez e posições de usuários do Revert Finance (Arbitrum), incluindo:

- Informações da pool (tokens, fees, etc.)
- Dados da posição do usuário
- Métricas de liquidez
- Valores e balanços
- Tabelas com dados históricos
- Requisições de API interceptadas (modo Playwright)

## Dois Scrapers Disponíveis

### 1. scraper.py (Selenium)
- Usa Selenium WebDriver
- Mais estável e amplamente usado
- Requer Chrome/Chromium instalado
- Bom para sites simples

### 2. scraper_playwright.py (Playwright) - **Recomendado**
- Usa Playwright (mais moderno)
- Pode interceptar requisições de rede/API
- Mais rápido e eficiente
- Melhor para SPAs modernas

## Requisitos

- Python 3.8+
- **Opção 1 (Selenium):** Google Chrome ou Chromium instalado
- **Opção 2 (Playwright):** Instalação automática de navegadores

## Instalação Rápida

Use o script de instalação automática:

```bash
chmod +x install.sh
./install.sh
```

Ou instale manualmente:

```bash
# Cria ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instala dependências
pip install -r requirements.txt

# Para Playwright (opcional mas recomendado):
playwright install chromium
```

## Uso

### Usando Makefile (Recomendado)

```bash
# Ver comandos disponíveis
make help

# Instalar dependências
make install

# Executar scraper com Selenium
make run-selenium

# Executar scraper com Playwright
make run-playwright

# Limpar arquivos gerados
make clean
```

### Uso Direto

Execute o scraper com as URLs pré-configuradas:

```bash
# Usando Selenium
python scraper.py

# Usando Playwright (recomendado)
python scraper_playwright.py
```

Isso irá:
1. Abrir cada URL fornecida
2. Aguardar o carregamento do JavaScript
3. Extrair todos os dados visíveis
4. Interceptar requisições de API (modo Playwright)
5. Salvar em CSV

### Personalização

Para adicionar ou modificar URLs, edite a lista `urls` no arquivo `scraper.py`:

```python
urls = [
    "https://revert.finance/#/uniswap-position/arbitrum/5066358",
    "https://revert.finance/#/uniswap-position/arbitrum/5003393",
    # Adicione mais URLs aqui
]
```

### Modo de Depuração

Para ver o navegador em ação (modo não-headless), modifique a linha no `scraper.py`:

```python
scraper = RevertFinanceScraper(headless=False)
```

## URLs Configuradas

As seguintes posições Uniswap no Arbitrum estão configuradas para extração:

1. Position 5066358
2. Position 5003393
3. Position 4990853
4. Position 5020274
5. Position 4807618
6. Position 4883063
7. Position 892272

## Arquivos Gerados

- `revert_finance_positions.csv` - Arquivo CSV com todos os dados extraídos
- `debug_[position_id].html` - Arquivos HTML para depuração (um por posição)

## Estrutura do CSV

O arquivo CSV gerado contém:

- `url` - URL da posição
- `position_id` - ID da posição
- `timestamp` - Data/hora da extração
- `table_N` - Dados das tabelas encontradas (N = 1, 2, 3...)
- Campos dinâmicos extraídos da página (tokens, valores, fees, etc.)

## Limitações

- O scraper depende da estrutura HTML da página, que pode mudar
- Sites com proteção anti-bot podem bloquear a extração
- Aguarda 3 segundos entre requisições para evitar rate limiting
- Algumas páginas podem requerer mais tempo de carregamento

## Solução de Problemas

### Erro: ChromeDriver não encontrado

O scraper usa `webdriver-manager` para instalar automaticamente o ChromeDriver. Se houver problemas:

1. Certifique-se de que o Google Chrome está instalado
2. Ou instale o Chromium:

```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# macOS
brew install chromium
```

### Erro: Timeout ao carregar página

Aumente o timeout na função `wait_for_page_load()`:

```python
self.wait_for_page_load(timeout=60)  # Aumenta para 60 segundos
```

### Dados não foram extraídos corretamente

1. Verifique os arquivos `debug_*.html` para ver o HTML original
2. Execute em modo não-headless para visualizar o navegador
3. Aumente o tempo de espera após carregar a página

## Contribuindo

Para melhorias e correções de bugs, sinta-se à vontade para contribuir.

## Licença

MIT License
