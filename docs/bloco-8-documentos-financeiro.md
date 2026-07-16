# Bloco 8 — Documentos e financeiro básico

## Escopo entregue

- contrato, termo de retirada, termo de devolução e recibo em PDF;
- cobranças de locação, atraso, desconto, limpeza, avaria e ajuste;
- registro manual de pagamentos por dinheiro, PIX, cartão, transferência ou outro método;
- saldo, total cobrado e total pago por locação;
- armazenamento privado dos PDFs com hash SHA-256 e versão;
- preparação para gateway por meio de referência externa opcional, sem dependência do domínio.

## Snapshots e documentos

Cada documento guarda um snapshot JSON imutável com os dados vigentes da locação, cliente, carreta, cobranças, pagamentos e, nos termos, a vistoria correspondente. Alterações posteriores não modificam documentos já emitidos.

O PDF é armazenado fora do banco em storage privado. A tabela mantém somente a chave interna, versão, hash, snapshot e metadados. O download exige autenticação e papel financeiro autorizado.

Regras específicas:

- o termo de retirada exige vistoria de retirada;
- o termo de devolução exige vistoria de devolução;
- o recibo exige pelo menos um pagamento confirmado;
- cada nova emissão recebe versão sequencial por tipo e locação.

## Cobranças

Locação, desconto comercial e atraso são originados automaticamente dos snapshots e cálculos da locação. Limpeza, avaria, desconto adicional e ajuste são lançamentos manuais de `ADMIN` ou `GESTOR`.

O saldo é calculado como cobranças positivas menos descontos e pagamentos confirmados. Pagamentos superiores ao saldo são rejeitados.

## Idempotência

Criação de cobrança manual, pagamento e documento exige `Idempotency-Key`.

- repetir a mesma operação com a mesma chave devolve o registro original;
- reutilizar a chave com dados diferentes retorna conflito;
- gerar ou reprocessar documento não recria cobranças automáticas;
- cobranças automáticas possuem chaves de origem únicas por locação.

## Permissões

- `ADMIN` e `GESTOR`: leitura financeira, cobranças, pagamentos e documentos;
- `ATENDENTE`: leitura financeira e geração/download de documentos;
- `VISTORIADOR` e `VIEWER`: sem acesso aos valores e documentos financeiros.

Todas as operações críticas geram auditoria sem registrar CPF completo, conteúdo do documento ou dados de pagamento sensíveis.
