# 1. Levantamento do sistema e definição de escopo

## 1.1 Projeto de referência: carreta-livre

O repositório analisado é um MVP criado com:

- React 18, TypeScript e Vite;
- Tailwind CSS e shadcn/ui;
- React Router;
- TanStack React Query;
- Supabase/PostgreSQL acessado diretamente pelo frontend.

### Funcionalidades existentes

- Dashboard com total de carretas, disponíveis, alugadas e em manutenção.
- Lista de carretas disponíveis e em uso.
- Cadastro, edição e exclusão de carretas.
- Cadastro, edição e exclusão de clientes.
- Criação de locação em quatro passos: período, carreta, cliente e confirmação.
- Locação por dias ou horas.
- Cálculo estimado no frontend usando diária ou diária dividida por 24.
- Finalização da locação, registrando devolução e liberando a carreta.
- Cadastro rápido de cliente durante uma nova locação.

### Banco atual

O protótipo possui quatro tabelas:

| Tabela | Finalidade |
|---|---|
| `carretas` | Inventário, dimensões, capacidade, diária e status. |
| `clientes` | Identificação, CPF, nascimento, CNH, telefone e endereço. |
| `alugueis` | Período, valor, status e vínculos com cliente/carreta. |
| `vistorias` | Vistoria de retirada/devolução, observações e fotos. |

As políticas RLS atuais permitem todas as operações publicamente. Isso é aceitável apenas como protótipo local e deve ser removido antes de qualquer uso real.

### Lacunas identificadas

- Sem login, usuários ou controle de acesso.
- Regras críticas e cálculo de preço executados no navegador.
- Ausência de prevenção transacional contra dupla reserva.
- Exclusões em cascata podem apagar histórico de locações e vistorias.
- Sem histórico de alterações, trilha de auditoria ou autoria das ações.
- Sem cadastro de manutenção, bloqueios por período ou calendário real de disponibilidade.
- Sem contrato, caução, pagamento, multas, avarias ou fechamento financeiro.
- Fotos de vistoria estão modeladas apenas como lista de textos.
- Sem testes automatizados, observabilidade e estratégia documentada de backup.
- Dados pessoais sensíveis ficam expostos a qualquer cliente que possua as chaves públicas do Supabase.

## 1.2 Referência arquitetural: Projeto Ilya

O AssisCarretas adotará os seguintes padrões documentados no Ilya:

- monorepo organizado em `backend`, `frontend`, `infra` e `docs`;
- FastAPI como camada de API e regras de negócio;
- React + TypeScript + Vite no frontend;
- PostgreSQL e SQLAlchemy com migrations Alembic;
- Docker Compose para desenvolvimento;
- schemas de entrada/saída separados dos modelos de persistência;
- autenticação JWT com refresh token seguro;
- RBAC validado obrigatoriamente no backend;
- React Query para estado remoto no frontend;
- histórico e auditoria para operações críticas;
- upload validado de arquivos e armazenamento externo em produção;
- pontos de controle entre blocos de implementação;
- segurança, LGPD, testes e operação tratados como partes do produto.

## 1.3 Escopo do AssisCarretas

### MVP operacional

- Autenticação e gestão básica de usuários.
- Dashboard operacional.
- Gestão de clientes.
- Gestão de carretas.
- Agenda e disponibilidade por intervalo de tempo.
- Criação, consulta, cancelamento e finalização de locações.
- Vistorias de retirada e devolução com fotos.
- Registro de manutenção e bloqueio automático da carreta.
- Cálculo de valores no backend.
- Contrato/recibo em PDF.
- Auditoria e proteção de dados pessoais.

### Evoluções posteriores

- Assinatura eletrônica.
- Caução e integração com gateway de pagamento.
- Cobrança de atraso, combustível, limpeza e avarias.
- Notificações por e-mail ou WhatsApp.
- Multiunidade/filiais.
- Portal do cliente.
- Integração contábil ou emissão fiscal.
- Aplicativo/PWA com captura offline de vistoria.

## 1.4 Perfis de usuário propostos

| Perfil | Responsabilidade principal |
|---|---|
| `ADMIN` | Configuração, usuários, acesso total e auditoria. |
| `GESTOR` | Operação completa, preços, manutenção, relatórios e cancelamentos. |
| `ATENDENTE` | Clientes, consultas, reservas, retirada e devolução. |
| `VISTORIADOR` | Vistorias e registro de avarias, sem acesso financeiro amplo. |
| `VIEWER` | Consulta interna, sem alterações. |

## 1.5 Fora do escopo inicial

- Marketplace público de carretas.
- Rastreamento GPS/telemetria.
- Emissão automática de nota fiscal.
- Contabilidade completa.
- Frota de veículos automotores além de carretas/reboques.
- Aplicativo nativo iOS/Android.

