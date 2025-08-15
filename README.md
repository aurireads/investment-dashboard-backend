### Visão Geral do Projeto

Este projeto é um backend de API construído com FastAPI para um painel de controlo de investimentos. A API foi projetada para ser de alto desempenho e fácil de usar, com recursos que incluem autenticação JWT, controle de acesso baseado em funções, atualizações de preços em tempo real via WebSockets, e acompanhamento detalhado de portfólio e comissões.

### Tecnologias Principais

  * **FastAPI**: Framework web de alta velocidade para a construção da API.
  * **SQLAlchemy**: ORM assíncrono para interação com a base de dados.
  * **PostgreSQL**: Base de dados relacional para armazenar os dados.
  * **Redis**: Utilizado para cache e como broker para o Celery.
  * **Celery**: Sistema de enfileiramento de tarefas para processamento em segundo plano, como a atualização diária e em tempo real dos preços dos ativos.
  * **uvicorn**: Servidor ASGI para executar a aplicação.
  * **Poetry**: Ferramenta de gestão de dependências.

### Estrutura do Projeto

O backend está organizado em módulos lógicos:

  * `app/api/v1/`: Contém os endpoints da API para diferentes áreas, como autenticação, clientes, painel de controlo, ativos e desempenho.
  * `app/core/`: Inclui a configuração central, a ligação à base de dados, e a lógica de segurança e JWT.
  * `app/models/`: Define os modelos de base de dados para utilizadores, clientes, consultores, ativos e alocações.
  * `app/schemas/`: Contém os schemas de dados para validação de requisições e formatação de respostas.
  * `app/services/`: Módulos para lógica de negócio específica, como integração com a API do Yahoo Finance para dados de preços e funcionalidade de exportação.
  * `app/tasks/`: Tarefas do Celery para atualizações agendadas de preços.
  * `app/utils/`: Funções de utilidade, como cálculos de retorno e limitação de taxa.
  * `app/websockets/`: Lógica para gerir as ligações WebSocket para atualizações de dados em tempo real.
  * `alembic/`: Contém as configurações e scripts para migrações de base de dados.

### Configuração e Execução

O projeto usa Docker para orquestrar os serviços (backend, base de dados e redis).

1.  **Variáveis de Ambiente**: Crie um ficheiro `.env` na raiz do projeto. Pode usar o ficheiro `.env.example` como modelo. As variáveis de ambiente incluem:

      * `DATABASE_URL`: URL de conexão assíncrona para a base de dados PostgreSQL.
      * `DATABASE_URL_SYNC`: URL de conexão síncrona para a base de dados (usada para o Alembic).
      * `REDIS_URL`: URL de conexão para o Redis.
      * `SECRET_KEY`: Chave secreta para JWT.
      * `PROJECT_NAME`: Nome do projeto.
      * `API_V1_STR`: Prefixo para a versão da API.
      * `DEBUG`: Ativa ou desativa o modo de depuração.

2.  **Executar com Docker Compose**: Para iniciar todos os serviços, execute o seguinte comando na raiz do projeto:

    ```sh
    docker-compose up --build
    ```

    O Docker irá construir as imagens, iniciar os serviços e executar as migrações da base de dados antes de iniciar o backend.

3.  **Aceder à API**: A API estará disponível em `http://localhost:8000`.

      * A documentação interativa (Swagger UI) pode ser encontrada em `http://localhost:8000/api/v1/docs`.
      * A documentação Redoc está disponível em `http://localhost:8000/api/v1/redoc`.

### Tarefas e Automação

  * **Migrações de Base de Dados**: O projeto usa `alembic` para gerir as migrações de base de dados. As migrações são aplicadas automaticamente no início do serviço `backend` usando `alembic upgrade head`.
  * **Atualização de Preços**: O Celery é usado para agendar tarefas em segundo plano.
      * `update_all_daily_prices`: Atualiza os preços de fecho diários para todos os ativos a cada 24 horas.
      * `update_all_realtime_prices`: Atualiza os preços em tempo real a cada 5 segundos e transmite as atualizações via WebSocket.

### Endpoints da API

  * `/api/v1/auth/`: Endpoints de autenticação, incluindo login e obtenção do perfil do utilizador.
  * `/api/v1/clients/`: Endpoints para gerir clientes, consultores e portfólios.
  * `/api/v1/dashboard/`: Endpoints para obter métricas e estatísticas para o painel de controlo.
  * `/api/v1/assets/`: Endpoints para gerir ativos e obter dados de desempenho.
  * `/api/v1/allocations/`: Endpoints para gerir as alocações dos clientes em ativos.
  * `/api/v1/info/`: Retorna informações detalhadas sobre a API, seus endpoints e recursos.

Para mais detalhes sobre as dependências do projeto, consulte `pyproject.toml` ou `requirements.txt`.
