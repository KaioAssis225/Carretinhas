# Plano de migração — protótipo Supabase → AssisCarretas

Ensaio e execução acontecem no Bloco 10. Este plano congela o dicionário de
mapeamento previsto em `03-banco-de-dados.md §3.7`.

## Origem
Quatro tabelas do projeto Supabase do protótipo `carreta-livre`:
`carretas`, `clientes`, `alugueis`, `vistorias`.

## Mapeamento de tabelas e campos

### carretas → trailers
| Origem | Destino | Transformação |
|---|---|---|
| codigo | code | direto |
| modelo | model | direto |
| comprimento/largura/altura | length_m/width_m/height_m | NUMERIC, validar > 0 |
| capacidade_carga | load_capacity_kg | NUMERIC |
| valor_diaria | daily_rate | NUMERIC(10,2) |
| status | status | `disponivel→AVAILABLE`, `alugada→RENTED`, `manutencao→MAINTENANCE` |
| — | hourly_rate, deposit_amount | NULL (não existiam) |

### clientes → clients
| Origem | Destino | Transformação |
|---|---|---|
| nome_completo | full_name | direto |
| cpf | cpf | remover máscara → 11 dígitos; validar dígitos verificadores |
| data_nascimento | birth_date | direto |
| cnh | cnh_number | somente dígitos; categoria/validade ficam NULL (não existiam) |
| telefone | phone | somente dígitos |
| endereco (texto livre) | address_street | melhor esforço; demais campos NULL |

### alugueis → rentals
| Origem | Destino | Transformação |
|---|---|---|
| carreta_id / cliente_id | trailer_id / client_id | preservar UUIDs |
| data_retirada | start_at | direto (timestamptz) |
| data_devolucao_prevista | expected_return_at | direto |
| data_devolucao_real | actual_return_at | direto |
| valor_total | total_expected e total_final | preço histórico — NÃO recalcular |
| tipo_periodo | period_type | `dias→DAYS`, `horas→HOURS` |
| quantidade_periodo | period_quantity | direto |
| status | status | `ativo→ACTIVE`, `finalizado→COMPLETED`, `cancelado→CANCELLED` |
| — | code | gerar sequencial na importação |
| — | created_by_user_id | usuário técnico "migracao@..." criado para a carga |
| — | daily_rate_snapshot | valor_diaria vigente da carreta na origem (aproximação documentada) |

### vistorias → inspections (+ inspection_photos)
| Origem | Destino | Transformação |
|---|---|---|
| aluguel_id | rental_id | preservar vínculo |
| tipo | type | `retirada→PICKUP`, `devolucao→RETURN` |
| observacoes | observations | direto |
| fotos (TEXT[]) | inspection_photos | 1 linha por item; baixar do storage antigo, revalidar MIME, gerar storage_key novo |
| — | checklist booleans | `true` com nota em observations ("migrado sem checklist") |
| — | responsible_name/performed_by | usuário técnico de migração |

## Atenções
- Locações ACTIVE migradas violando a EXCLUDE constraint (sobreposição
  pré-existente) devem ser listadas e resolvidas manualmente antes da carga.
- CPFs inválidos na origem: relatório de exceção, não importar silenciosamente.
- Executar em transação por lote; qualquer lote com erro é revertido inteiro.

## Reconciliação (critério de aceite)
1. Contagens por tabela: origem = destino (± exceções documentadas).
2. Soma de `valor_total` = soma de `total_final` dos migrados.
3. Amostra aleatória de 10 registros por tabela conferida manualmente.
4. Nenhuma carreta com dupla ocupação de agenda após a carga.
