# Registro de decisões

Decisões técnicas tomadas durante a implementação, com justificativa.
Decisões de negócio pendentes ficam em aberto no Bloco 0 do
[06-plano-de-implementacao.md](../06-plano-de-implementacao.md) até aprovação.

## Bloco 1 — Fundações e ambiente (2026-07-13)

| # | Decisão | Justificativa |
|---|---|---|
| 1.1 | `carreta-livre-referencia/` excluída do git via `.gitignore` | O protótipo contém `.env` com chaves do Supabase; versioná-lo publicaria segredos. A pasta permanece intocada no disco, como manda o prompt mestre. |
| 1.2 | Linter do frontend é **oxlint** (default do template Vite atual) em vez de ESLint | Zero configuração extra, mais rápido, cobre as regras necessárias neste estágio. Pode ser trocado por ESLint se alguma regra específica fizer falta. |
| 1.3 | shadcn/ui **ainda não instalado**; Tailwind configurado com paleta neutra compatível | O Bloco 1 pede apenas layout e roteamento base. Componentes shadcn entram no Bloco 3/4 junto com as primeiras telas reais, evitando dependências sem uso. |
| 1.4 | `Dockerfile` fica em `backend/` (não em `infra/docker/`) | Mantém o contexto de build pequeno e o caminho simples no Compose e no CI. `infra/` recebe scripts de infraestrutura quando existirem. |
| 1.5 | Logging estruturado com `logging` da stdlib + formatter JSON próprio | Evita dependência extra (structlog) sem necessidade comprovada, conforme restrição de dependências do prompt mestre. |
| 1.6 | Configuração via `pydantic-settings` com prefixo `ASSISCARRETAS_` | Evita colisão de variáveis de ambiente e documenta o contrato de configuração. |
| 1.7 | Correlation ID: aceita apenas UUID válido vindo do cliente; caso contrário gera novo | Impede injeção de conteúdo arbitrário em logs através do header. |
| 1.8 | Portas do Compose vinculadas a `127.0.0.1` | PostgreSQL e API de desenvolvimento não ficam expostos na rede local. |
| 1.9 | Python 3.13 local/CI/Docker; `requires-python >= 3.12` | 3.13 é o disponível no ambiente; manter compatibilidade 3.12 dá folga para o deploy. |
