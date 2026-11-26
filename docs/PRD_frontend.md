# PULSO — Especificação visual do frontend

**Versão:** 1.0  
**Escopo:** exclusivamente identidade visual, layout, cores e experiência de interface.  
**Não inclui:** rotas, contratos de API, autenticação técnica, banco de dados, infraestrutura, regras de backend ou código de integração.

## 1. Direção criativa

Construir um SaaS de inteligência de negócios para marketplace que transmita clareza, confiabilidade e sofisticação sem parecer um dashboard genérico. A experiência deve ser **editorial, analítica, silenciosa e precisa**: muita hierarquia tipográfica, espaços bem resolvidos, linhas finas e poucos acentos de cor.

**Nome de interface:** `pulso.` — sempre em caixa baixa, com ponto final.  
**Tom:** profissional, acessível e contemporâneo.  
**Princípio:** os dados são protagonistas; efeitos visuais não competem com eles.

### Evitar
- Gradientes roxos/azuis, efeito glassmorphism e brilhos.
- Sombra pesada, cards dentro de cards, ícones decorativos sem função.
- Excesso de badges, muitas cores simultâneas, títulos enormes.
- Layout com aparência de template administrativo genérico.

## 2. Paleta de cores

### Cores centrais

| Token | Cor | Uso |
|---|---|---|
| `--bg-app` | `#F7F8F5` | Fundo geral, levemente esverdeado |
| `--surface` | `#FFFFFF` | Superfícies, tabelas e painéis |
| `--surface-muted` | `#F0F3EE` | Áreas secundárias, filtros e hover suave |
| `--brand-ink` | `#202C29` | Logo, sidebar destacada, títulos, CTAs escuros |
| `--text-primary` | `#222A26` | Texto principal |
| `--text-secondary` | `#69756E` | Descrições, labels e dados secundários |
| `--text-tertiary` | `#89948C` | Metadados e placeholders |
| `--border` | `#E2E8E1` | Divisórias e contornos leves |
| `--accent-lime` | `#D4F379` | Ações prioritárias e indicadores pontuais |
| `--accent-text` | `#202C29` | Texto sobre o verde-lima |

### Semântica e visualização

| Intenção | Cor |
|---|---|
| Sucesso | `#228061` |
| Atenção | `#B77932` |
| Erro | `#B64B4B` |
| Informação | `#4968C9` |
| Série 1 — verde | `#376B57` |
| Série 2 — azul | `#708DD1` |
| Série 3 — mostarda | `#C49A58` |
| Série 4 — cinza | `#A6B0A8` |

**Regra de uso:** 75–80% neutros, 15–20% verde-escuro/cinza e no máximo 5% de verde-lima nas áreas principais. Nunca usar o lime como texto fino em fundo branco. Priorizar contraste legível e verificar WCAG AA.

### Identificação dos perfis

A cor do produto permanece a mesma em todos os perfis. Só pequenos detalhes visuais distinguem a área:
- **Vendas:** verde `#376B57`.
- **Produtos:** azul `#4968C9`.
- **Comercial:** terracota `#B47B58`.
- **Diretoria:** dourado discreto `#A58A4B`.

Aplicar apenas em ícone, linha curta de destaque ou chip contextual; nunca trocar todo o tema do dashboard.

## 3. Tipografia

- **Fonte primária:** `Inter` ou `Geist`, com preferência por **Geist** para maior personalidade contemporânea.
- **Marca e títulos principais:** `Instrument Sans` (se disponível); fallback para Geist.
- **Números de KPIs:** fonte principal com `font-variant-numeric: tabular-nums`.
- **Pesos:** regular 400; medium 500; semibold 600. Evitar negrito 800–900.

| Elemento | Tamanho desktop | Peso | Observação |
|---|---:|---:|---|
| Título de página | 30–34 px | 600 | Linha 1.15, tracking levemente negativo |
| Título de seção | 18–20 px | 600 | Sem excesso de destaque |
| Título de card | 13–14 px | 500 | Contrastado, não gritante |
| KPI principal | 30–38 px | 600 | Tabular nums |
| Corpo de texto | 14–15 px | 400 | Altura de linha ~1.5 |
| Labels/metadados | 12–13 px | 500 | Cor secundária |

## 4. Grade, espaçamento e superfícies

- **Grid principal:** 12 colunas no desktop; largura máxima útil de 1440–1520 px, centrada.
- **Margem de conteúdo:** 32 px no desktop, 24 px em telas médias e 16 px no celular.
- **Espaçamentos:** escala de 4, 8, 12, 16, 24, 32, 40 e 48 px. Entre blocos importantes: 24–32 px.
- **Cards:** borda `1px solid #E2E8E1`, fundo branco, raio 12–14 px, padding 20–24 px.
- **Sombras:** quase imperceptíveis, usadas somente em menu flutuante, drawer e modal.
- **Botões:** altura 40–44 px, raio 10 px, ícones 16–18 px.
- **Inputs:** altura 42–44 px, contorno sutil e estado de foco claramente visível.

## 5. Estrutura global

### Sidebar

- Largura expandida: 232–248 px. Colapsada: 68–72 px.
- Fundo branco, divisória direita fina; não fazer uma barra escura dominante.
- Topo: monograma verde-escuro com detalhe lime + palavra `pulso.`.
- Navegação vertical com ícone à esquerda, texto curto e item ativo sobre fundo `#F0F3EE`.
- Ícones lineares, 18–20 px, mesmo peso visual.
- Rodapé: avatar com iniciais, nome curto e perfil atual.
- No mobile: navegação em drawer.

### Topbar

- Altura aproximada: 64–72 px; fundo acompanha o app.
- Esquerda: breadcrumb discreto ou contexto da área.
- Direita: período selecionado, indicador do perfil e avatar.
- Sem barra de busca global se ela não tiver função clara.

### Cabeçalho de conteúdo

- Microtexto superior: nome do setor ou contexto.
- Título forte, de uma linha quando possível.
- Subtítulo curto e orientado ao trabalho.
- Filtros discretos alinhados à direita (período e agrupamento).

## 6. Dashboard de cada perfil

Manter a mesma arquitetura de página para todos, mas trocar os nomes e tipos de visualização:

### Vendas
- KPIs: pedidos realizados, receita, atrasos, pagamentos aprovados.
- Gráfico principal: evolução de pedidos e receita por período.
- Gráfico secundário: distribuição dos status de entrega.
- Tabela: pedidos recentes / status de entrega.
- Pergunta sugerida no chat: **“O que está causando os atrasos?”**

### Produtos
- KPIs: Produtos no catálogo, nota média, produtos mal avaliados, avaliações recebidas.
- Gráfico principal: distribuição de avaliações por faixa de nota.
- Gráfico secundário: categorias com maior volume de reclamações.
- Tabela: produtos e suas avaliações.
- Pergunta sugerida: **“Quais categorias concentram as piores notas?”**

### Comercial
- KPIs: leads, novos lojistas, conversão, principal canal.
- Gráfico principal: funil de captação até conversão.
- Gráfico secundário: novos lojistas por canal.
- Tabela: desempenho dos canais.
- Pergunta sugerida: **“Qual canal traz os leads que mais convertem?”**

### Diretoria
- KPIs: receita consolidada, recompra, satisfação e retenção.
- Gráfico principal: painel comparativo de tendência dos indicadores.
- Gráfico secundário: fatores correlacionados à recompra, já apresentados de forma consolidada.
- Tabela: resumo executivo por dimensão de negócio.
- Pergunta sugerida: **“Por que os clientes compram uma vez e não voltam?”**

### Composição de página sugerida

1. Cabeçalho com título, descrição e seletor de período.
2. Linha com **quatro cartões de KPI**: valor em destaque, legenda e pequena variação.
3. Linha analítica principal: gráfico largo (aprox. 8/12 colunas) + gráfico complementar (4/12).
4. Tabela de dados ocupando largura total.
5. Bloco discreto de convite ao chat, sem ocupar o papel do gráfico principal.

## 7. Padrões de gráficos e tabelas

### Gráficos

- Fundo branco, sem borda grossa.
- Linhas de grade horizontais finas em `#E9EDE7`; eliminar grades verticais quando possível.
- Legendas discretas no topo ou abaixo do título.
- Priorizar **linhas, barras e barras empilhadas**. Usar donuts com moderação.
- Tooltips brancos, raio 10 px, sombra suave, valores organizados.
- Eixos e rótulos em cinza secundário, 12 px.
- Usar séries consistentes entre gráficos, não cores aleatórias.
- Evitar animações longas, 3D e degradês em barras.

### Tabelas

- Cabeçalho levemente destacado, texto 12 px semibold e cor secundária.
- Linhas de 52–56 px, divisórias horizontais tênues.
- Alinhamento: textos à esquerda; valores numéricos à direita.
- Status como chips de baixo contraste, nunca como badges saturadas grandes.
- Hover de linha discreto; menu de ações só quando necessário.
- Vazio com uma explicação clara e breve, sem ilustração gigantesca.

## 8. Assistente de IA

### Chat lateral (drawer)

- Aberto na direita, largura de 400–440 px no desktop.
- Fundo branco, borda esquerda fina e sombra suave.
- Header: ícone pequeno, título **Assistente PULSO**, contexto/perfil em texto secundário e botão fechar.
- Conversa com largura confortável, bubbles discretos: mensagens do usuário em `#F0F3EE`; respostas do assistente sem caixa pesada, com tipografia direta.
- Perguntas sugeridas em chips simples, 1–3 por contexto.
- Composer fixo na base: textarea de 1–5 linhas, atalho de envio e botão de ação em verde-escuro.
- Rodapé e estados informativos sem excesso de texto.

### Chat expandido

- Área de conversa central com largura legível de 760–860 px.
- Cabeçalho editorial e sugestões iniciais em linhas, não uma grade de cards exuberantes.
- Quando houver resposta longa, usar subtítulos, tabelas compactas e listas curtas.
- Bloco retrátil **Como esta resposta foi obtida**: visual técnico discreto, com nome da ferramenta, status e tempo; sem mostrar segredos.
- Loading: indicador sutil de atividade + texto de status, nunca animação chamativa.

## 9. Tela de login e painel de demonstração

### Login (somente layout)

- Composição assimétrica 55/45.
- Lado esquerdo em verde-escuro: marca `pulso.`, frase de valor e um pequeno detalhe gráfico abstrato.
- Lado direito com formulário centrado em um bloco estreito (máx. 360–400 px).
- Campos e botão alinhados, sem imagens stock, sem gradientes.
- No mobile, empilhar e simplificar o painel de marca.

### Painel visual de segurança (para o apresentador)

- Linguagem visual de **console de auditoria elegante**, não terminal hacker.
- Matriz limpa com colunas **Cenário**, **Perfil**, **Resultado** e **Detalhes**.
- Permitido: ícone check e texto verde escuro; negado: ícone de bloqueio e texto vermelho discreto.
- Pequenos cartões-resumo de testes concluídos, permitidos e negados.
- Detalhe expandido do teste pode aparecer em drawer, sem popups excessivos.

## 10. Interações e estados visuais

- **Hover:** mudança sutil de fundo/borda em 120–160 ms.
- **Focus:** anel visível e consistente, sem depender só de cor.
- **Entrada de painéis:** 160–220 ms com leve opacidade; respeitar `prefers-reduced-motion`.
- **Skeleton:** blocos retangulares discretos, proporcionais aos gráficos e linhas da tabela.
- **Erro:** mensagem objetiva com ícone e ação clara, sem cobrir a página inteira.
- **Vazio:** título pequeno, explicação curta e orientação contextual.
- **Negado:** visual sério e neutro, evitando mensagens alarmistas.

## 11. Responsividade

| Faixa | Comportamento |
|---|---|
| Desktop ≥ 1280 px | Sidebar expandida, 4 KPIs em linha, gráficos 8/4 |
| Laptop 1024–1279 px | Sidebar recolhível, KPIs 2×2 quando necessário |
| Tablet 768–1023 px | Sidebar em ícones/drawer, gráficos empilhados ou 6/6 |
| Mobile < 768 px | 1 coluna, margens 16 px, KPIs 2×2 (ou 1 coluna estreita), drawer de chat em tela cheia |

Não reduzir texto excessivamente para encaixar componentes. Prefira reorganizar a grade. Tabelas extensas podem ter rolagem horizontal controlada e destaque das colunas essenciais.

## 12. Componentes visuais a padronizar

`AppShell`, `Sidebar`, `Topbar`, `PageHeading`, `ProfileIndicator`, `PeriodFilter`, `KpiCard`, `TrendBadge`, `ChartPanel`, `DataTable`, `StatusChip`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `AssistantDrawer`, `ChatComposer`, `SuggestedQuestion`, `ToolTraceDisclosure`, `SecurityTestTable`.

Para cada componente, manter variações de densidade, estados hover/focus/disabled e espaçamento consistente. Não inventar uma aparência diferente para cada dashboard.

## 13. Critérios de aceite visuais

- [ ] O produto tem identidade própria e consistente, sem aparência de template genérico.
- [ ] Os quatro perfis compartilham o mesmo design system e se diferenciam apenas nos dados e microacentos.
- [ ] KPIs, gráficos e tabelas têm hierarquia visual clara.
- [ ] A sidebar não rouba atenção do conteúdo.
- [ ] O chat lateral não descaracteriza o dashboard; expandido, oferece leitura confortável.
- [ ] O verde-lima destaca somente ações e sinais importantes.
- [ ] Há estados de carregamento, vazio, erro, negação e foco.
- [ ] A interface funciona de 320 px até desktop amplo sem sobreposição relevante.
- [ ] Cores de texto e controles atendem ao contraste e navegação por teclado previstos.
- [ ] Nenhum módulo usa gradientes, vidro fosco ou efeitos visuais desnecessários.

## 14. Prompt visual de implementação

> Construa a interface **pulso.**, um SaaS editorial de analytics para marketplace, com React, Tailwind e componentes consistentes. **Implemente apenas o frontend visual com dados fictícios**, sem lógica de backend. Use fundo `#F7F8F5`, superfícies brancas, marca verde-escuro `#202C29`, destaque lime `#D4F379`, bordas `#E2E8E1`, tipografia Geist/Instrument Sans, sidebar branca recolhível, topbar discreta, KPIs com números tabulares, gráficos minimalistas, tabelas densas e elegantes, chat lateral e modo expandido, quatro perfis visuais (Vendas, Produtos, Comercial e Diretoria) e painel visual de demonstração de segurança. Priorize clareza, hierarquia tipográfica, responsividade e microinterações suaves. Evite gradientes, sombras fortes, glassmorphism, cards em excesso e estilo genérico de dashboard de IA.
