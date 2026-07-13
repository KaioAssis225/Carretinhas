# Setup de desenvolvimento

## Pré-requisitos

- Python 3.12+ (desenvolvido com 3.13)
- Node.js 22+ (desenvolvido com 24)
- Docker Desktop (PostgreSQL e API em containers)
- Git

## Primeira execução

```bash
# 1. Variáveis de ambiente
cp .env.example .env   # ajuste os valores; o .env nunca é commitado

# 2. Banco + API em containers
docker compose up -d --build
# API: http://localhost:8000/api/v1/health — OpenAPI em http://localhost:8000/docs

# 3. Frontend em modo dev
cd frontend
npm ci
npm run dev
# http://localhost:5173
```

Alternativa sem Docker para a API:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Verificações de qualidade

Backend (dentro de `backend/`, com o venv ativo):

```bash
ruff check .          # lint
ruff format --check . # formatação
mypy                  # tipos (modo strict)
pytest                # testes
```

Frontend (dentro de `frontend/`):

```bash
npm run lint       # oxlint
npm run typecheck  # tsc
npm run test       # vitest
npm run build      # build de produção
```

O pipeline de CI (`.github/workflows/ci.yml`) executa exatamente esses passos
e bloqueia merge em caso de falha.

## Convenções já ativas no Bloco 1

- Toda resposta de erro da API segue
  `{ "error": { "code", "message", "correlation_id", "details?" } }`.
- Toda resposta HTTP carrega o header `X-Correlation-ID`; envie-o de volta ao
  reportar problemas.
- Logs do backend são JSON estruturado em stdout; nunca registrar senha,
  token, CPF ou CNH completos.
- O frontend fala com a API somente através de `src/api/client.ts`.
- `carreta-livre-referencia/` está fora do versionamento (contém `.env` do
  protótipo) e não deve ser alterada.
