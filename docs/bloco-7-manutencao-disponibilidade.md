# Bloco 7 — Manutenção e disponibilidade

## Objetivo

Controlar ordens de manutenção, custos, bloqueios de agenda, encaminhamentos por avaria e alertas operacionais sem permitir dupla alocação de uma carreta.

## Fluxo da ordem

Estados permitidos:

- `OPEN`: ordem criada e ainda não iniciada;
- `IN_PROGRESS`: execução iniciada e carreta em `MAINTENANCE`;
- `COMPLETED`: serviço concluído, com data e custo final registrados;
- `CANCELLED`: ordem cancelada sem apagar o histórico.

Transições válidas:

- `OPEN -> IN_PROGRESS`;
- `OPEN -> COMPLETED`;
- `IN_PROGRESS -> COMPLETED`;
- `OPEN -> CANCELLED`;
- `IN_PROGRESS -> CANCELLED`.

Ordens concluídas ou canceladas são imutáveis. Toda criação, alteração e transição gera registro de auditoria com usuário, data, ação e entidade.

## Regras de agenda e disponibilidade

- Uma ordem aberta ou em andamento bloqueia o intervalo da carreta na agenda.
- Não é possível criar, alterar ou iniciar manutenção sobreposta a uma reserva ou locação ativa.
- Uma nova reserva também não pode se sobrepor a uma manutenção aberta ou em andamento.
- Ao iniciar a execução, a carreta passa para `MAINTENANCE`.
- Ao concluir ou cancelar, a carreta só é liberada se não houver outra manutenção bloqueante.
- A liberação recompõe o estado operacional: `RENTED` para locação ativa/atrasada, `RESERVED` para reserva futura e `AVAILABLE` quando não existe alocação.
- Carretas inativas permanecem `INACTIVE` após o encerramento da ordem.

## Encaminhamento após devolução

Uma vistoria de devolução que registre avaria ou indique manutenção cria automaticamente uma ordem aberta. Ordens originadas por avaria recebem prioridade alta e mantêm a carreta bloqueada para novas reservas.

## Custos e histórico técnico

A ordem aceita custo estimado durante o planejamento e exige custo final não negativo no encerramento. O histórico técnico pode ser consultado por ordem e preserva todas as ações de forma auditável.

## Alertas operacionais

O painel de manutenção apresenta:

- devoluções atrasadas;
- retiradas reservadas para as próximas 24 horas;
- manutenções abertas ou em andamento;
- manutenções bloqueantes de alta prioridade.

## Permissões

- `ADMIN` e `GESTOR`: criam, alteram, iniciam, concluem e cancelam ordens;
- `VISTORIADOR`: consulta e atualiza somente a descrição técnica;
- `ATENDENTE` e `VIEWER`: acesso de leitura conforme as políticas da API.
