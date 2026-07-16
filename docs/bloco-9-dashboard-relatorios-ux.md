# Bloco 9 — Dashboard, relatórios e UX final

## Indicadores

O dashboard apresenta o estado operacional atual:

- carretas por situação;
- locações ativas e atrasadas;
- retiradas e devoluções previstas nas próximas 24 horas;
- manutenções abertas ou em andamento.

Para `ADMIN`, `GESTOR` e `ATENDENTE`, também apresenta valores agregados do período selecionado. Os demais perfis recebem `financial: null`, de forma que o dado não é apenas ocultado no frontend: ele não é enviado pela API.

Os indicadores financeiros são reconciliados com o mesmo serviço usado pelo relatório financeiro:

- contratado: valor líquido das locações criadas no período;
- recebido: pagamentos confirmados das locações do período;
- saldo: diferença não negativa entre contratado e recebido.

## Relatórios e filtros

O relatório operacional aceita período, status e paginação. A exportação CSV utiliza os mesmos filtros.

O relatório financeiro e a consulta de auditoria são exclusivos de `ADMIN` e `GESTOR`. O período máximo por consulta é de 367 dias para limitar custo e evitar extrações excessivas.

## Proteção das exportações

O CSV operacional contém somente código da locação, código da carreta, status e datas operacionais. Não são exportados:

- nome do cliente;
- CPF ou CNH;
- telefone, e-mail ou endereço;
- identificadores internos de cliente;
- observações ou conteúdo de documentos.

Campos textuais iniciados por caracteres interpretáveis como fórmula recebem prefixo seguro antes da gravação no CSV.

## Experiência e acessibilidade

- estados explícitos de carregamento, vazio e erro;
- filtros utilizáveis por teclado;
- alvos interativos com altura mínima de 44 pixels;
- foco visível em links, botões e campos;
- link “Pular para o conteúdo”;
- cards responsivos e tabelas extensas com rolagem horizontal controlada;
- contraste baseado na paleta primária e cores sem uso exclusivo para transmitir estado.
- renovação de sessão deduplicada para impedir rotação concorrente do cookie durante recargas.

## Rotas

- `GET /api/v1/dashboard`;
- `GET /api/v1/reports/operations`;
- `GET /api/v1/reports/operations/export.csv`;
- `GET /api/v1/reports/financial`;
- `GET /api/v1/reports/financial/export.csv`;
- `GET /api/v1/reports/audit`.
