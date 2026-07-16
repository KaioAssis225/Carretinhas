# Bloco 5 — Agenda, preço e reservas

## Regras implementadas

- A cobrança usa a tarifa oficial da carreta no backend.
- Períodos incompletos são arredondados para cima por dia ou hora.
- Cobrança por hora exige tarifa horária própria; a diária nunca é dividida por 24.
- Desconto provisório máximo: `ATENDENTE` 5%, `GESTOR` 15% e `ADMIN` 100%.
- Todo desconto exige justificativa e fica gravado no snapshot da locação.
- Tarifas, caução, desconto e total ficam preservados mesmo se a carreta mudar de preço.
- O intervalo de agenda tem fim exclusivo: uma retirada pode começar exatamente no horário da devolução anterior.
- Reservas usam lock pessimista e a constraint `ex_rentals_agenda_sem_sobreposicao` do PostgreSQL.
- A criação aceita `Idempotency-Key` para que uma repetição de rede não gere duas reservas.

Os percentuais de desconto são uma decisão provisória porque o planejamento original deixou essa política em aberto. Devem ser confirmados com a operação antes da produção.

## Endpoints entregues

- `GET /api/v1/trailers/{id}/availability`
- `GET /api/v1/rentals`
- `GET /api/v1/rentals/agenda`
- `POST /api/v1/rentals/quote`
- `POST /api/v1/rentals`
- `GET /api/v1/rentals/{id}`
- `POST /api/v1/rentals/{id}/reserve`
