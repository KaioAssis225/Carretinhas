# Aceite operacional — Bloco 9

## Registro técnico

| Critério | Evidência | Situação |
|---|---|---|
| Indicadores reconciliam com o banco | Teste automatizado compara dashboard e relatório financeiro | Aprovado tecnicamente |
| Exportação protege dados pessoais | Teste verifica ausência de nome, CPF e cabeçalhos pessoais | Aprovado tecnicamente |
| Permissões financeiras | Testes de API para gestor, atendente e viewer | Aprovado tecnicamente |
| Desktop e celular | Revisão responsiva e acessível no navegador local | Aprovado tecnicamente |
| Suíte completa | Backend, frontend, lint, tipos e build | Aprovado tecnicamente |

## Roteiro de validação operacional

1. Entrar como administrador ou gestor.
2. Conferir os totais do dashboard com as locações conhecidas.
3. Alterar o período e confirmar a atualização dos valores.
4. Abrir Relatórios, filtrar por status e exportar o CSV operacional.
5. Confirmar que o CSV não contém informações pessoais do cliente.
6. Exportar o financeiro e conferir cobrado, pago e saldo.
7. Repetir o fluxo em largura de celular e usando apenas teclado.
8. Entrar com perfil sem permissão financeira e confirmar que os valores não aparecem.

## Decisão operacional

- Status: **AGUARDANDO ACEITE DO RESPONSÁVEL OPERACIONAL**
- Responsável: ______________________________________
- Data: ____/____/________
- Decisão: [ ] Aceito  [ ] Aceito com ressalvas  [ ] Reprovado
- Observações: ______________________________________

O STOP & REVIEW 9 somente deve ser convertido em aceite formal depois do preenchimento desta seção pelo responsável operacional.
