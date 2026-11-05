<div align="center">
◈ DevOps Monitor
Plataforma Inteligente de Monitoramento de Serviços de Rede

Monitoramento • Observabilidade • Segurança • DevOps

<br>






<br>

Sobre •
Funcionalidades •
Arquitetura •
Tecnologias •
Instalação •
Roadmap

<br>

Status: 🚧 Em desenvolvimento

</div>
📌 Sobre o Projeto

O DevOps Monitor é uma plataforma web desenvolvida para centralizar o monitoramento de serviços de rede, permitindo acompanhar disponibilidade, desempenho, métricas operacionais e indicadores de segurança por meio de dashboards interativos.

A aplicação busca oferecer uma visão consolidada da infraestrutura monitorada, facilitando a identificação de falhas, degradações de desempenho e comportamentos potencialmente suspeitos.

O sistema contará com mecanismos de coleta periódica de métricas, armazenamento de informações históricas, classificação de alertas e envio de notificações por e-mail.

O projeto está sendo desenvolvido como parte do trabalho final da disciplina Redes de Computadores e Internet, do Instituto Brasileiro de Ensino, Desenvolvimento e Pesquisa (IDP).
🎯 Objetivos

    Desenvolver uma plataforma centralizada de monitoramento de serviços de rede.

    Implementar dashboards interativos para visualização de métricas.

    Monitorar disponibilidade e desempenho de diferentes serviços.

    Implementar mecanismos de identificação e classificação de alertas.

    Desenvolver notificações automáticas por e-mail.

    Incorporar recursos adicionais de monitoramento de segurança.

    Aplicar conceitos de redes de computadores, desenvolvimento web e observabilidade.

⚙️ Funcionalidades
📊 Monitoramento de Serviços
Serviço	Indicadores
🌐 HTTP/HTTPS	Disponibilidade, latência, requisições e erros
🗄️ Database	Disponibilidade, consultas, conexões e desempenho
🌍 DNS	Tempo de resolução, consultas e falhas
✉️ SMTP	Disponibilidade, latência e erros de comunicação
🚨 Sistema de Alertas

A plataforma utilizará três níveis de classificação:
Nível	Estado	Descrição
🟢	Normal	Serviço operando dentro dos parâmetros esperados
🟡	Atenção	Identificação de degradação ou comportamento anormal
🔴	Crítico	Serviço indisponível ou condição crítica identificada

Os alertas poderão gerar notificações automáticas por e-mail, de acordo com a gravidade do incidente.
🔐 Monitoramento de Segurança

    Identificação de anomalias de tráfego.

    Monitoramento de tentativas de autenticação malsucedidas.

    Detecção de alterações em arquivos de configuração.

    Monitoramento de vulnerabilidades conhecidas.

🏗️ Arquitetura

A aplicação será organizada em módulos independentes, responsáveis pela coleta, processamento, armazenamento e visualização das informações.

flowchart TD
    A[Serviços Monitorados] --> B[Módulo de Monitoramento]

    B --> C[Coleta de Métricas]

    C --> D[Backend - FastAPI]

    D --> E[(Banco de Dados)]

    D --> F[Sistema de Alertas]

    F --> G[Notificações por E-mail]

    E --> H[API REST]

    H --> I[Frontend - Dashboard]

    J[Módulo de Segurança] --> D

Fluxo de funcionamento

    Os módulos de monitoramento verificam os serviços cadastrados.

    As métricas coletadas são encaminhadas ao backend.

    O backend processa e armazena os resultados.

    O sistema de alertas avalia as métricas e identifica possíveis incidentes.

    Notificações são enviadas conforme a classificação dos alertas.

    O frontend apresenta os dados em dashboards interativos.

🛠️ Tecnologias
Backend

<div>
<img src="https://skillicons.dev/icons?i=python,fastapi" />
</div>

    Python: linguagem principal da aplicação.

    FastAPI: desenvolvimento da API REST.

    SQLite: armazenamento inicial das métricas.

Frontend

<div>
<img src="https://skillicons.dev/icons?i=html,css,js" />
</div>

    HTML5: estrutura das páginas.

    CSS3: estilização e responsividade.

    JavaScript: interatividade e integração com a API.

    Chart.js: construção de gráficos e dashboards.

Desenvolvimento e Versionamento

<div>
<img src="https://skillicons.dev/icons?i=git,github,vscode" />
</div>

    Git

    GitHub

    Visual Studio Code

📁 Estrutura do Projeto

DevOps-Monitor/
│
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       └── services/
│
├── frontend/
│   ├── css/
│   ├── js/
│   └── assets/
│
├── monitoramento/
│   ├── web/
│   ├── database/
│   ├── dns/
│   ├── smtp/
│   └── utils/
│
├── alertas/
│
├── seguranca/
│
├── testes/
│
├── docs/
│
├── dados/
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt

🚀 Instalação
Pré-requisitos

    Python 3.10 ou superior

    Git

    Visual Studio Code (recomendado)

1. Clone o repositório

git clone https://github.com/SEU-USUARIO/DevOps-Monitor.git

2. Acesse o diretório

cd DevOps-Monitor

3. Crie um ambiente virtual

python3 -m venv .venv

4. Ative o ambiente virtual

source .venv/bin/activate

5. Instale as dependências

pip install -r requirements.txt

    A aplicação estará disponível para execução após a implementação dos módulos iniciais.

🗺️ Roadmap

    Configuração inicial do repositório.

    Implementação da estrutura do backend.

    Configuração do banco de dados.

    Monitoramento HTTP/HTTPS.

    Monitoramento de bancos de dados.

    Monitoramento DNS.

    Monitoramento SMTP.

    Implementação da API REST.

    Desenvolvimento do dashboard consolidado.

    Desenvolvimento dos dashboards individuais.

    Implementação do sistema de alertas.

    Integração com notificações por e-mail.

    Implementação dos recursos de segurança.

    Desenvolvimento dos testes automatizados.

    Documentação técnica.

    Testes de integração.

    Preparação da apresentação final.

🧪 Testes

A aplicação contará com testes automatizados para validar:

    Funcionamento dos módulos de monitoramento.

    Processamento e armazenamento de métricas.

    Comunicação entre frontend e backend.

    Classificação dos alertas.

    Funcionamento das notificações.

    Recursos de segurança.

Os testes serão desenvolvidos utilizando Pytest.
📚 Documentação

A documentação técnica será organizada no diretório docs/, incluindo:

    Arquitetura da aplicação.

    Guia de instalação e configuração.

    Runbooks operacionais.

    Playbooks de resposta a incidentes.

    Procedimentos de monitoramento.

🎓 Contexto Acadêmico

Instituição: Instituto Brasileiro de Ensino, Desenvolvimento e Pesquisa — IDP

Disciplina: Redes de Computadores e Internet

Professora: Lorena Borges

Projeto: Trabalho Final — Plataforma de Monitoramento para DevOps
👨‍💻 Desenvolvedores

Projeto acadêmico desenvolvido para aplicação prática de conceitos relacionados a:

    Redes de computadores.

    Desenvolvimento de sistemas.

    Monitoramento de infraestrutura.

    Segurança de redes.

    Observabilidade e DevOps.

<div align="center">
◈ DevOps Monitor

Monitoramento inteligente. Infraestrutura confiável.

<br>


</div>
