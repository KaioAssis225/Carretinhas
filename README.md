# AssisCarretas — Planejamento técnico

Este diretório contém somente a especificação e o plano de implementação do **AssisCarretas**. Nenhum código do sistema foi criado aqui.

O planejamento combina:

- o domínio e os fluxos existentes no repositório `KaioAssis225/carreta-livre`;
- a arquitetura de produção documentada no Projeto Ilya;
- reforços necessários para transformar o protótipo em um sistema seguro, auditável e preparado para evolução.

## Documentos

1. [01-levantamento-e-escopo.md](01-levantamento-e-escopo.md) — o que existe no projeto de referência e o escopo proposto.
2. [02-arquitetura-tecnica.md](02-arquitetura-tecnica.md) — arquitetura, tecnologias, estrutura de diretórios e decisões técnicas.
3. [03-banco-de-dados.md](03-banco-de-dados.md) — entidades, relacionamentos, estados, integridade e evolução do banco.
4. [04-modulos-regras-e-api.md](04-modulos-regras-e-api.md) — módulos funcionais, regras de negócio e contratos de API planejados.
5. [05-seguranca-lgpd-e-rbac.md](05-seguranca-lgpd-e-rbac.md) — autenticação, papéis, permissões, proteção de dados e auditoria.
6. [06-plano-de-implementacao.md](06-plano-de-implementacao.md) — execução dividida em blocos com dependências e pontos de controle.
7. [07-testes-deploy-e-operacao.md](07-testes-deploy-e-operacao.md) — estratégia de testes, ambientes, publicação, observabilidade e operação.
8. [PROMPT-MESTRE-GEMINI.md](PROMPT-MESTRE-GEMINI.md) — prompt completo para conduzir a implementação com o Gemini por blocos e revisões.

## Decisão central

O repositório de referência usa React diretamente com Supabase. No AssisCarretas, o frontend continuará em React/TypeScript, mas as operações críticas passarão por uma API FastAPI. O PostgreSQL continuará como banco principal. Isso segue o padrão do Ilya e impede que cálculo de preço, disponibilidade, encerramento de locação e autorização dependam do navegador.

## Limites deste planejamento

- Não há código de frontend, backend, banco, infraestrutura ou testes.
- Não há migrations executáveis nem arquivos de configuração com segredos.
- Os nomes de rotas e campos são contratos propostos; podem ser refinados antes da implementação.
- Pagamentos online, emissão fiscal e assinatura eletrônica ficam previstos como extensões, não como parte obrigatória do primeiro MVP.
