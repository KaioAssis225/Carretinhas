# Dicionário de dados — schema do MVP

Gerado a partir da migration inicial (`20260714_7337dbec3b13`). Convenções
globais: PK `id UUID`; `created_at`/`updated_at` em UTC mantidos pelo banco;
dinheiro em `NUMERIC(10,2)`; enums como `VARCHAR + CHECK` (não nativos);
histórico é inativado (`is_active`), nunca apagado em cascata.

## users
| Coluna | Tipo | Notas |
|---|---|---|
| name | varchar(120) | |
| email | varchar(254) | único |
| hashed_password | varchar(255) | Argon2id |
| role | varchar(20) | ADMIN, GESTOR, ATENDENTE, VISTORIADOR, VIEWER |
| is_active | bool | default true |
| must_change_password | bool | default false |
| last_login_at | timestamptz | nulo até o primeiro login |

## refresh_tokens
| Coluna | Tipo | Notas |
|---|---|---|
| user_id | uuid → users | ON DELETE CASCADE (remoção controlada de conta) |
| token_hash | varchar(64) | único; token em claro nunca é persistido |
| expires_at / revoked_at | timestamptz | revogação de sessão |
| user_agent / ip_prefix | varchar | dados mínimos de sessão, sem PII extra |

## clients
| Coluna | Tipo | Notas |
|---|---|---|
| full_name | varchar(150) | indexado para busca |
| cpf | varchar(11) | único; CHECK 11 dígitos; mascarado na exibição |
| birth_date | date | maioridade validada na aplicação |
| cnh_number / cnh_category / cnh_expires_at | varchar/date | opcionais; exigidos na retirada |
| phone / email | varchar | email opcional |
| address_* | varchar | CEP, logradouro, número, complemento, bairro, cidade, UF |
| notes | text | acesso restrito |
| is_active | bool | cliente inativo não inicia locação |

## trailers
| Coluna | Tipo | Notas |
|---|---|---|
| code | varchar(20) | único |
| model / description | varchar/text | |
| plate / renavam | varchar | opcionais; placa única quando preenchida |
| length_m / width_m / height_m | numeric(6,2) | CHECK > 0 |
| load_capacity_kg | numeric(8,2) | CHECK > 0 |
| daily_rate | numeric(10,2) | CHECK > 0 |
| hourly_rate | numeric(10,2) | opcional — tarifa própria, nunca diária/24 |
| deposit_amount | numeric(10,2) | caução informativa no MVP |
| status | varchar(20) | AVAILABLE, RESERVED, RENTED, MAINTENANCE, INACTIVE — resumo; disponibilidade real considera agenda |
| is_active | bool | |

## rentals
| Coluna | Tipo | Notas |
|---|---|---|
| code | varchar(20) | único, sequencial gerado pelo serviço |
| client_id / trailer_id | uuid | ON DELETE RESTRICT — histórico não some |
| created_by / pickup_by / return_by _user_id | uuid → users | responsáveis |
| start_at / expected_return_at | timestamptz | CHECK devolução > retirada |
| actual_return_at | timestamptz | hora real da devolução |
| period_type / period_quantity | varchar/int | memória comercial (DAYS/HOURS) |
| *_snapshot | numeric(10,2) | diária/hora/caução congeladas na contratação |
| discount_amount | numeric(10,2) | CHECK ≥ 0; limites por papel na aplicação |
| total_expected / total_final | numeric(10,2) | calculados só no backend |
| status | varchar(20) | DRAFT, RESERVED, ACTIVE, OVERDUE, COMPLETED, CANCELLED |
| cancel_reason / notes | text | |

**Constraint especial:** `ex_rentals_agenda_sem_sobreposicao` — EXCLUDE
(btree_gist) impede duas locações RESERVED/ACTIVE/OVERDUE sobrepostas para a
mesma carreta, no próprio banco, mesmo sob concorrência. Intervalo fim-exclusivo:
devolver 8h e retirar 8h não conflita.

## inspections
| Coluna | Tipo | Notas |
|---|---|---|
| rental_id | uuid → rentals | RESTRICT |
| type | varchar(10) | PICKUP ou RETURN; único por locação+tipo |
| structure/tires/lights/coupling/documents_ok, is_clean | bool | checklist |
| mileage_km | numeric(9,1) | opcional |
| observations / responsible_name | text/varchar | |
| performed_by_user_id / performed_at | uuid/timestamptz | |

## inspection_photos
| Coluna | Tipo | Notas |
|---|---|---|
| inspection_id | uuid → inspections | CASCADE (filha direta) |
| storage_key | varchar(255) | único; nome aleatório no storage privado |
| original_name / mime_type / size_bytes / sha256 | — | MIME verificado por magic bytes; CHECK size > 0 |
| category | varchar(50) | ex.: frente, engate, avaria |

## maintenance_orders
| Coluna | Tipo | Notas |
|---|---|---|
| trailer_id | uuid → trailers | RESTRICT |
| type / description / priority | — | prioridade LOW/MEDIUM/HIGH |
| starts_at / expected_end_at / completed_at | timestamptz | CHECK fim > início |
| estimated_cost / final_cost | numeric(10,2) | CHECK ≥ 0 |
| status | varchar(15) | OPEN, IN_PROGRESS, COMPLETED, CANCELLED |
| created_by / assigned_to _user_id | uuid → users | |

## rental_history (imutável)
rental_id, user_id (SET NULL), action, old_status, new_status, details JSONB, created_at.

## audit_logs (imutável)
actor_user_id (SET NULL), action, entity_type, entity_id, result, ip_prefix,
correlation_id, details JSONB, created_at. Nunca conter senha, token ou
CPF/CNH completos.

## Índices de agenda e busca
- `ix_rentals_trailer_agenda` (trailer_id, start_at, expected_return_at, status)
- `ix_maintenance_trailer_agenda` (idem para manutenção)
- `ix_clients_full_name`, `uq_clients_cpf`, `uq_trailers_code`, `uq_rentals_code`
- `ix_audit_logs_entity` (entity_type, entity_id, created_at)
