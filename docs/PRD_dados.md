# PRD de dados

Os dados da empresa são sintéticos, gerados por um script com semente
fixa. Rodar o script duas vezes deve produzir exatamente o mesmo banco.

Os dados terminam em uma data de referência fixa, definida na
configuração do gerador, e não no dia da execução. O valor inicial é
30 de novembro de 2026.

## O que os dados representam

Um marketplace brasileiro que conecta lojistas a clientes finais, com
24 meses de operação terminando na data de referência.

## Volumes aproximados

- 300 lojistas, 2 mil produtos em cerca de 20 categorias
- 25 mil clientes, 30 mil pedidos
- 20 mil avaliações, com nota de 1 a 5 e comentário em parte delas
- 1.500 leads de lojistas no funil comercial, dos quais cerca de 300
  viraram lojistas

## Conteúdo por área

- Vendas: pedidos, itens, pagamentos (forma e parcelas), frete, datas
  de compra, de entrega prometida e de entrega real.
- Produtos: catálogo, categoria, preço, avaliações por produto.
- Comercial: leads, canal de origem, etapa do funil, data de
  fechamento, lojista resultante.
- Diretoria: nada próprio; os indicadores derivam das três áreas.

## Padrões que precisam existir nos dados

1. Recompra baixa: só cerca de 5% dos clientes fazem um segundo pedido.
2. Atraso concentrado: cerca de 10% dos pedidos atrasam, a maioria em
   poucas rotas longas e em um grupo pequeno de lojistas.
3. Atraso derruba a nota: pedidos no prazo têm média perto de 4,3;
   atrasos acima de uma semana, perto de 1,8.
4. Nota ruim elimina a recompra: quem deu nota 1 ou 2 quase nunca
   volta.
5. Origem importa: lojistas vindos de um dos canais comerciais atrasam
   bem mais que os demais.
6. Sazonalidade: picos em novembro e dezembro, e crescimento leve mês
   a mês.

Os padrões 2 a 5 formam a resposta à pergunta "por que os clientes não
voltam?", e cada perfil enxerga só um pedaço dela.

## Regras

- Nomes, e-mails, documentos e endereços são fictícios. Nenhum dado
  real de pessoa.
- Cidades e estados brasileiros reais, com mais volume no Sudeste.
- Comentários de avaliação em português, coerentes com a nota.
- Incluir uma única avaliação com texto malicioso, que tenta dar
  instruções a um agente de IA, para o teste de segurança.
- Datas coerentes: entrega depois da compra, avaliação depois da
  entrega, fechamento do lead antes do primeiro pedido do lojista.
