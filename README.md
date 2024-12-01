# Sistema de Certificação do Cadastro Ambiental Rural (CAR)

## Visão Geral
Este projeto tem como foco a **automação do processo de emissão de certificados para o Cadastro Ambiental Rural (CAR)**, garantindo eficiência e controle rigoroso das gerações realizadas. Desenvolvido para a **Secretaria de Estado de Meio Ambiente e Sustentabilidade (SEMAS/PA)**, o sistema permite:
- Geração de certificados de forma automatizada;
- Armazenamento das informações detalhadas de cada emissão;
- Documentação completa dos metadados de cada operação, incluindo o usuário responsável.

## Principais Funcionalidades
- **Geração automatizada de certificados** em PDF para imóveis rurais validados, com números de série únicos.
- **Armazenamento no banco de dados** das informações de cada emissão, permitindo auditorias detalhadas por lote.
- **Documentação de metadados**, incluindo data de emissão, número de certificados gerados e responsável pela operação.
- **Sistema de login e controle de acesso**, com registro de ações realizadas pelos usuários.
- **Relatórios e auditorias** sobre o status dos imóveis, incluindo tentativas de certificação para imóveis suspensos ou cancelados.

## Resultados Esperados
- **Automatização do processo de emissão de certificados**, reduzindo erros e aumentando a agilidade.
- **Registro completo de metadados**, possibilitando auditorias detalhadas.
- **Maior transparência** no processo de certificação, com controle sobre as ações realizadas.
- **Eficiência na gestão de dados** dos imóveis rurais validados no estado do Pará.

## Demonstrações

### **1. Página Inicial e Login**
Demonstração da interface inicial e processo de login: [Assistir no Vimeo](https://player.vimeo.com/video/1035004919?h=805fa5024b)

### **2. Geração de Certificados por CPF/CNPJ**
Demonstração da funcionalidade de geração de certificados por CPF ou CNPJ: [Assistir no Vimeo](https://player.vimeo.com/video/1035004850?h=86aba52290)

### **3. Geração de Certificados por Lista**
Demonstração da funcionalidade de geração de certificados por lista: [Assistir no Vimeo](https://player.vimeo.com/video/1035004865?h=2d347da33e)


## Tecnologias Utilizadas
- **Backend**: Flask (Python)
- **Banco de Dados**: PostgreSQL
- **Geração de PDFs**: ReportLab
- **Frontend**: HTML, CSS, e Bootstrap
- **Autenticação**: Sistema de login com Flask e sessões protegidas
- **Controle de Versão**: Git e GitHub

## Como Executar
1. **Clone este repositório**:
   ```bash
   git clone https://github.com/samuel-c-santos/sistema-certificacao-car.git
   cd sistema-certificacao-car
   ```

2. **Instale as dependências**:
   Certifique-se de ter o Python 3.9+ instalado e execute:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente**:
   Crie um arquivo `.env` com as seguintes informações (exemplo):
   ```
   DATABASE_URI=postgresql://usuario:senha@host/banco
   SECRET_KEY=sua_chave_secreta
   ```

4. **Execute o servidor**:
   ```bash
   python app.py
   ```
   O sistema estará disponível em `http://localhost:5000`.

## Licença
Este projeto é de uso exclusivo da **SEMAS/PA** e foi adaptado para demonstração. Informações sensíveis foram substituídas por placeholders para proteger os dados da instituição.

---

**Autor**: Samuel C. Santos  
[GitHub](https://github.com/samuel-c-santos) | [LinkedIn](https://www.linkedin.com/in/samuelsantos-amb/)
```
