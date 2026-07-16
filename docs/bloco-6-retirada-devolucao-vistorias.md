# Bloco 6 — Retirada, devolução e vistorias

## Fluxo operacional

- Uma reserva somente vira locação ativa após vistoria de retirada aprovada e ao menos uma foto.
- Cliente, CNH e carreta são revalidados dentro da transação de retirada.
- A devolução exige checklist e foto, registra o horário real e calcula atraso por dia ou hora.
- Checklist reprovado ou marcação manual encaminha a carreta para `MAINTENANCE`; caso contrário, ela volta para `AVAILABLE`.
- Locação e carreta são atualizadas na mesma transação, com histórico e auditoria.

## Fotos privadas

- Formatos permitidos: JPEG, PNG e WebP, validados por assinatura do arquivo.
- Limite padrão: 8 MB por foto.
- Nomes enviados não definem o caminho do arquivo; cada objeto recebe uma chave aleatória.
- Arquivos ficam no volume privado `inspection_data` e só são entregues por endpoint autenticado.

No desenvolvimento o armazenamento é local e persistente no Docker. Produção deverá usar storage S3 compatível e privado, mantendo o mesmo contrato de autorização.
