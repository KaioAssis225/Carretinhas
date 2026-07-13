# 5. Segurança, LGPD e RBAC

## 5.1 Autenticação

- Senhas com Argon2id e parâmetros revisados periodicamente.
- Access token JWT curto mantido em memória.
- Refresh token rotativo em cookie `HttpOnly`, `Secure` e `SameSite` adequado.
- Tokens persistidos somente por hash e revogáveis.
- Rate limit no login e atrasos progressivos contra força bruta.
- Sessões encerradas ao desativar usuário ou trocar credenciais críticas.
- Segredos somente em variáveis de ambiente/serviço de segredos.

## 5.2 Matriz de permissões resumida

| Recurso/ação | ADMIN | GESTOR | ATENDENTE | VISTORIADOR | VIEWER |
|---|:---:|:---:|:---:|:---:|:---:|
| Usuários e papéis | Total | Não | Não | Não | Não |
| Clientes: consultar | Sim | Sim | Sim | Limitado | Sim |
| Clientes: criar/editar | Sim | Sim | Sim | Não | Não |
| Carretas: consultar | Sim | Sim | Sim | Sim | Sim |
| Carretas: criar/editar | Sim | Sim | Limitado | Não | Não |
| Reservar locação | Sim | Sim | Sim | Não | Não |
| Aplicar desconto | Total | Dentro da política | Limite baixo | Não | Não |
| Retirada/devolução | Sim | Sim | Sim | Vistoria | Não |
| Manutenção | Sim | Sim | Consulta | Atualiza vistoria técnica | Consulta |
| Relatório financeiro | Sim | Sim | Limitado | Não | Conforme autorização |
| Auditoria | Sim | Consulta | Não | Não | Não |

As permissões devem ser detalhadas por ação no backend. Esconder botão no frontend melhora a experiência, mas não protege a API.

## 5.3 Segurança da API

- CORS limitado às origens conhecidas.
- Headers de segurança e HTTPS obrigatório em produção.
- Limites de payload, paginação e upload.
- Validação estrita com campos desconhecidos rejeitados quando apropriado.
- Respostas de erro não incluem stack trace, SQL ou segredo.
- Proteção contra IDOR: toda consulta valida autorização sobre o recurso.
- Controle transacional e idempotência para reservas, devoluções e pagamentos.
- Dependências atualizadas e análise de vulnerabilidades no pipeline.

## 5.4 Uploads

- Extensões não são confiáveis; validar magic bytes e MIME real.
- Limitar quantidade, tamanho e resolução.
- Gerar nomes internos aleatórios e impedir caminhos fornecidos pelo usuário.
- Armazenar fora da pasta pública da aplicação.
- URLs temporárias/assinadas para documentos privados.
- Remover metadados desnecessários de imagens quando possível.
- Antivírus ou varredura assíncrona antes de disponibilizar arquivos de maior risco.

## 5.5 LGPD

Dados tratados incluem CPF, CNH, nascimento, endereço, telefone, fotos e histórico contratual. O projeto deve documentar:

- finalidade de cada dado coletado;
- base legal aplicável, validada pelo responsável jurídico;
- tempo de retenção por categoria;
- quem pode consultar e alterar;
- procedimento para correção, exportação, anonimização ou eliminação quando legalmente possível;
- processo de resposta a incidente.

Medidas práticas:

- minimização: coletar apenas o necessário;
- mascaramento de CPF/CNH em listas;
- logs sem dados pessoais integrais;
- criptografia em trânsito e backups protegidos;
- acesso de produção individualizado;
- ambientes de teste com dados sintéticos;
- histórico contratual preservado pelo prazo legal, sem exclusão casual.

## 5.6 Auditoria

Registrar, no mínimo:

- login bem-sucedido/falhado sem expor credenciais;
- criação, alteração, inativação e consulta sensível de cliente;
- mudança de tarifa/status da carreta;
- criação, desconto, cancelamento, retirada e devolução de locação;
- criação/alteração de cobrança ou pagamento;
- geração/assinatura de documento;
- alterações de usuário e papel.

Logs de auditoria não podem ser editados pela interface comum. A retenção deve ser definida com operação e jurídico.

## 5.7 Checklist antes de produção

- Nenhuma política pública equivalente a `FOR ALL USING (true)`.
- Nenhum segredo commitado.
- Contas e senhas de seed desativadas em produção.
- Backup restaurado com sucesso em teste.
- Pentest focado em autenticação, IDOR, uploads e manipulação de preço.
- Matriz RBAC validada com testes automatizados.
- Termos de privacidade e retenção aprovados pelo responsável do negócio.

