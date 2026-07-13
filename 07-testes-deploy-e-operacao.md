# 7. Testes, deploy e operação

## 7.1 Estratégia de testes

### Backend unitário

- Cálculo por dia/hora e arredondamento.
- Descontos e limites por papel.
- Sobreposição de intervalos.
- Transições de status.
- Atraso e cobranças adicionais.
- Validação de cliente, CNH e carreta.

### Backend integrado

- Repositórios com PostgreSQL real de teste.
- Migrations para frente e, quando seguro, rollback.
- Concorrência ao reservar a mesma carreta.
- Transações de retirada/devolução.
- RBAC e proteção contra IDOR.
- Uploads válidos e maliciosos.

### Frontend

- Formulários, validações e mensagens.
- Estados de carregamento, vazio e erro.
- Navegação protegida.
- Componentes de agenda, locação e vistoria.
- Acessibilidade básica automatizada.

### Ponta a ponta

Fluxos prioritários:

1. Login → cadastrar cliente → cadastrar carreta → reservar.
2. Reserva → vistoria de retirada → locação ativa.
3. Locação ativa → vistoria de devolução → cobrança → conclusão.
4. Avaria → manutenção → bloqueio → conclusão → disponibilidade.
5. Usuário sem permissão tentando preço, cliente de terceiros ou auditoria.

## 7.2 Critérios mínimos de qualidade

- Toda regra financeira possui teste unitário.
- Toda rota crítica possui teste de autorização.
- Bugs de produção recebem teste de regressão.
- Pipeline bloqueia merge quando lint, tipos, testes ou build falham.
- Cobertura é indicador, não substituto de cenários relevantes.

## 7.3 Pipeline planejado

1. Instalar dependências de forma reproduzível.
2. Verificar formatação, lint e tipos.
3. Executar testes unitários e integrados.
4. Construir frontend e imagem do backend.
5. Analisar dependências e segredos.
6. Publicar artefatos imutáveis.
7. Aplicar migrations controladas.
8. Fazer smoke test pós-deploy.

## 7.4 Deploy

Configuração semelhante ao Ilya:

- frontend em serviço de hospedagem estática/CDN;
- backend em plataforma de containers;
- PostgreSQL gerenciado;
- arquivos em storage S3 compatível;
- Redis gerenciado somente quando jobs forem ativados.

Requisitos:

- domínios e CORS definidos por ambiente;
- HTTPS obrigatório;
- migrations executadas uma única vez por release;
- health checks de vida e prontidão;
- rollback de aplicação sem perder compatibilidade com o schema;
- variáveis de ambiente documentadas, sem valores reais no repositório.

## 7.5 Observabilidade

- Logs estruturados com `correlation_id`.
- Métricas: latência, taxa de erro, logins falhos, reservas conflitantes, jobs falhos.
- Alertas para indisponibilidade, erro elevado, banco/armazenamento e backup.
- Monitoramento de negócio: locações atrasadas e devoluções próximas.
- Rastreamento de erros no frontend e backend sem anexar PII desnecessária.

## 7.6 Backup e recuperação

- Backup automático do PostgreSQL com retenção definida.
- Versionamento/retensão adequada dos arquivos de vistoria e documentos.
- Teste periódico de restauração em ambiente isolado.
- RPO e RTO aprovados pelo negócio.
- Runbook de perda de banco, indisponibilidade de storage e segredo comprometido.

## 7.7 Operação e suporte

Runbooks necessários:

- usuário bloqueado ou sessão comprometida;
- correção autorizada de locação;
- carreta presa em estado incorreto;
- falha de upload/documento;
- indisponibilidade do sistema;
- restauração de backup;
- incidente de dados pessoais;
- rollback de release.

## 7.8 Homologação final

Antes da produção, o responsável do negócio deve executar uma bateria com dados fictícios:

- reserva normal e conflito de agenda;
- locação por dia e por hora;
- desconto dentro e fora do limite;
- cancelamento antes da retirada;
- devolução no prazo e atrasada;
- devolução com avaria e manutenção;
- cliente/CNH inválidos;
- tentativa de ação por cada perfil;
- contrato, vistoria, recibo e relatório;
- uso em celular no fluxo de pátio.

O aceite deve registrar versão, data, participantes, cenários aprovados e pendências aceitas.

