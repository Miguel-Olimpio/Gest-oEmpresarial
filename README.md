# AppGestãoEmpresarial

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## IDEALIZAÇÃO DO PROJETO

O **AppGestãoEmpresarial** foi desenvolvido para ajudar pequenos negócios a acompanharem vendas, fluxo de caixa, custos, colaboradores e informações úteis para o contador de forma simples e local.

A proposta do app é oferecer uma visão prática da rotina financeira da empresa, sem exigir sistemas caros, servidores ou bancos de dados complexos. A persistência é feita em planilhas Excel locais, permitindo que a empresa mantenha seus registros em uma estrutura acessível e fácil de transportar.

> **Versão demo:** esta versão pública demonstra a estrutura e o fluxo principal do projeto. Dados reais, planilhas geradas, PDFs, backups e builds não são enviados ao GitHub.

## SOBRE O APP

O AppGestãoEmpresarial é uma aplicação desktop/local em Python com Tkinter e ttkbootstrap.

Ele foi pensado para pequenos empreendedores que precisam registrar entradas, custos, fluxo de caixa e informações básicas de colaboradores, além de gerar um relatório em PDF para apoio contábil.

## FUNCIONALIDADES

- Dashboard com indicadores do mês.
- Gráficos de despesas e produtividade.
- Registro de vendas e entradas.
- Cadastro de máquinas de cartão.
- Conferência de recebíveis.
- Fluxo de caixa.
- Cadastro de custos fixos.
- Cadastro de custos variáveis.
- Cadastro de colaboradores e sócios.
- Cálculo de salários e pró-labore em custos fixos.
- Geração de PDF para contador.
- Banco de dados local em Excel.
- Backups locais.
- Estrutura preparada para PyInstaller.

## LAYOUT E MODO DE USAR

### 1. Acompanhe o Dashboard

O Dashboard centraliza indicadores essenciais do mês, gráficos e alertas educativos para apoiar a tomada de decisão.

![imageGestao1](https://github.com/user-attachments/assets/02748839-7918-4bb5-a6dc-3e42ac3e0501)

### 2. Registre vendas e entradas

Na área de vendas, o usuário registra entradas em dinheiro, vendas por máquina de cartão, condições de recebimento e conferência dos valores previstos.

![imageGestao2](https://github.com/user-attachments/assets/0744cb8a-7e86-414c-ab2f-7dc3fe0e7144)

### 3. Controle o fluxo de caixa

O fluxo de caixa reúne lançamentos manuais e recebíveis previstos, ajudando a empresa a visualizar entradas, saídas e saldo do período.

![imageGestao3](https://github.com/user-attachments/assets/5f27b949-6c07-4cd6-b6d7-8f6c391fa1c2)

### 4. Organize custos fixos e variáveis

O app permite registrar custos fixos mensais, custos variáveis e taxas automáticas relacionadas às vendas por cartão.

![imageGestao4](https://github.com/user-attachments/assets/b03b92d4-9058-4a2b-8c90-976941d7ff3d)

### 5. Cadastre colaboradores e gere PDF para contador

O cadastro de colaboradores e sócios permite compor custos fixos com salários e pró-labore. No Dashboard, também é possível gerar um PDF mensal para envio ao contador.

![imageGestao5](https://github.com/user-attachments/assets/b74eecf5-e61e-4d5b-bc08-b77f1ddfc8ba)

## BANCO DE DADOS LOCAL

O app cria e utiliza planilhas locais em:

```text
data/
```

Arquivos principais:

```text
data/financeiro.xlsx
data/vendas.xlsx
data/colaboradores.xlsx
data/audit_log.xlsx
```

Pastas criadas/esperadas:

```text
data/
pdfs/
pdfs/contador/
backups/
icon/
```

Esses arquivos não são versionados no GitHub.

## PDF PARA CONTADOR

No Dashboard, selecione o mês em `MM/AAAA` e clique em:

```text
Gerar PDF para contador
```

O arquivo é salvo em:

```text
pdfs/contador/relatorio_contador_MM_AAAA.pdf
```

O relatório inclui resumo do mês, vendas, entradas, fluxo de caixa, custos fixos, custos variáveis e recebíveis de máquina de cartão.

## TECNOLOGIAS UTILIZADAS

## Back end

- Python
- openpyxl
- pandas
- ReportLab

## Front end

- Tkinter
- ttkbootstrap
- Matplotlib

## Testes e empacotamento

- pytest
- PyInstaller

## COMO EXECUTAR O PROJETO

Pré-requisitos:

- Python 3.10 ou superior.

```bash
# clonar repositório
git clone https://github.com/Miguel-Olimpio/Gest-oEmpresarial.git

# entrar na pasta
cd Gest-oEmpresarial

# criar ambiente virtual opcional
python -m venv .venv

# ativar ambiente virtual no Windows
.venv\Scripts\activate

# instalar dependências
pip install -r requirements.txt

# executar app
python main.py
```

## TESTES

Para rodar os testes:

```bash
python -m pytest tests -q
```

## GERAR EXECUTÁVEL

Coloque o ícone em:

```text
icon/icon.ico
```

Comando recomendado:

```bash
pyinstaller --clean --noconfirm GestaoEmpresarial.spec
```

O executável será gerado em:

```text
dist/GestaoEmpresarial/GestaoEmpresarial.exe
```

Estrutura esperada para entrega:

```text
GestaoEmpresarial/
  GestaoEmpresarial.exe
  data/
  pdfs/
  backups/
  icon/
```

## OBSERVAÇÕES SOBRE ARQUIVOS GRANDES

O repositório não inclui:

- planilhas de dados;
- PDFs gerados;
- backups;
- builds do PyInstaller;
- arquivos `.zip`;
- dados reais ou de teste.

Esses arquivos devem ser criados localmente pela execução do app.

## ESTRUTURA DO PROJETO

```text
app/
  config/
  models/
  repositories/
  services/
  ui/
  utils/
  pdf/
tests/
icon/
main.py
requirements.txt
GestaoEmpresarial.spec
gerar_executavel.bat
```

## AUTOR

Miguel Olimpio de Paula Netto

## LICENÇA

Este projeto está sob licença MIT.
