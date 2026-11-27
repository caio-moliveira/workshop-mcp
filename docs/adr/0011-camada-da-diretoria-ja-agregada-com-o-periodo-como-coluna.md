# Camada da Diretoria já agregada, com o período como coluna

A Diretoria consulta indicadores consolidados e não pode alcançar registros individuais dos outros perfis (RF-04), e essa garantia precisa valer no banco, como as demais (RS-04, ADR 0002). As camadas de Vendas, Produtos e Comercial são views linha a linha, agregadas depois pelas consultas da API; se a da Diretoria seguisse essa forma, o papel `diretoria` leria pedidos, clientes e avaliações. Decidimos que as views da Diretoria já saem agregadas, uma linha por grupo de uma dimensão fechada (ponto da série, canal do lojista, situação da primeira entrega, faixa da primeira nota, faixa de atraso), com o período como coluna: cada view traz as linhas dos quatro períodos, e a consulta só filtra o período pedido. O período precisa estar dentro da view porque taxa de recompra e retenção contam clientes distintos, e agregados mensais não se somam para formar um período. É a única camada que cruza as três áreas (canal do lojista, atraso, nota e recompra).

## Considered Options

- **Views linha a linha, com a agregação na API, como nos outros perfis**: rejeitado porque a credencial da Diretoria leria registros individuais, e o RF-04 passaria a depender só do código.
- **Funções com direito do dono, recebendo o período**: rejeitado porque esconde a camada atrás de código no banco e foge do padrão da ADR 0002, em que a permissão é de leitura num esquema de views. Só compensaria se o período fosse livre, e ele é uma enumeração de quatro valores.
- **Views materializadas**: rejeitado por ora. Exigem um passo de atualização depois da recarga, e o cruzamento inteiro das três áreas levou cerca de 20 ms na medição. O teste de tempo das rotas decide se isso muda.

## Consequences

Um período novo ou uma dimensão nova exigem mudar a carga, não só a API. Lojista, produto, rota e categoria não são dimensões: os dois primeiros são registros individuais, a rota tem grupos pequenos demais nos períodos curtos, e a categoria contaria o mesmo pedido em várias linhas (13,5% dos pedidos têm itens de mais de uma categoria). Não há regra de supressão de grupos pequenos: toda linha traz a contagem do grupo, e um teste exige que nenhuma tenha contagem 1 nos dados da carga. Os fatores de recompra omitem os grupos sem desfecho (primeiro pedido sem avaliação, em trânsito ou com prazo vencido), porque nos dados gerados quem faz recompra sempre avalia o primeiro pedido, e o grupo "sem avaliação" apareceria com 0% por artefato da carga, não por padrão de negócio.
