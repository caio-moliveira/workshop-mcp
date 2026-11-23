"""Operação de vendas: clientes, pedidos, itens, pagamentos e entregas.

Os padrões do PRD de dados nascem aqui, sem nenhuma coluna que os marque:

1. Recompra baixa: só cerca de 5% dos clientes fazem um segundo pedido.
2. Atraso concentrado em poucas rotas longas e em um grupo pequeno de lojistas.
5. Os lojistas que atrasam vêm, na maioria, de um mesmo canal (Mídia paga).
6. Picos em novembro e dezembro e crescimento leve mês a mês.
"""

import bisect
import calendar
import random
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from faker import Faker

from carga.calendario import MESES_DE_OPERACAO, Calendario, dias_entre, somar_meses
from carga.catalogo import Catalogo, Produto
from carga.comercial import Comercial, Lojista
from carga.documentos import cpf_ficticio
from carga.geografia import CIDADES, distancia_km

# O Brasil não tem horário de verão desde 2019: Brasília é sempre UTC-3.
FUSO_DE_BRASILIA = timezone(timedelta(hours=-3), "BRT")

PEDIDOS_PREVISTOS = 30_000

# Padrão 6: crescimento mês a mês e picos de fim de ano.
CRESCIMENTO_MENSAL = 0.02
FATOR_SAZONAL_POR_MES = {11: 1.75, 12: 1.9}
VARIACAO_MENSAL = 0.05

# Padrão 1: quem faz recompra. Cerca de 5% dos clientes com pedido aprovado.
CLIENTES_QUE_RECOMPRAM = 1_365
PROPORCAO_DE_QUEM_FAZ_TRES_PEDIDOS = 0.1
DIAS_MINIMOS_ENTRE_PEDIDOS = 20
DIAS_MINIMOS_ENTRE_O_PRIMEIRO_PEDIDO_E_A_REFERENCIA = 90
TENTATIVAS_DE_ACHAR_O_PROXIMO_PEDIDO = 50

# Padrões 2 e 5: um grupo pequeno de lojistas atrasa muito, quase todo de Mídia paga.
CANAL_DOS_LOJISTAS_QUE_ATRASAM = "Mídia paga"
LOJISTAS_QUE_ATRASAM_DO_CANAL = 27
LOJISTAS_QUE_ATRASAM_DE_OUTROS_CANAIS = 3
# Quem atrasa muito também vende muito: capta clientes com mídia paga em volume.
VOLUME_RELATIVO_DE_QUEM_ATRASA = 2.5
RISCO_RELATIVO_DE_ATRASO_DE_QUEM_ATRASA = 10.0
# Os demais lojistas do canal também atrasam um pouco mais que os de outros canais.
RISCO_RELATIVO_DE_ATRASO_DO_CANAL = 1.5

# Padrão 2: rotas longas atrasam mais. (distância máxima em km, risco relativo de atraso)
RISCO_RELATIVO_DE_ATRASO_POR_DISTANCIA: tuple[tuple[float, float], ...] = (
    (200, 0.6),
    (800, 0.9),
    (1500, 1.3),
    (2500, 2.0),
    (float("inf"), 2.8),
)

# Os riscos relativos (lojista e rota) são escalados para que a taxa esperada seja esta,
# qualquer que seja a semente.
TAXA_DE_ATRASO_ALVO = 0.10
CHANCE_MAXIMA_DE_ATRASO = 0.9

# Prazo prometido: uma base, mais um dia a cada tantos km, mais uma folga sorteada.
PRAZO_BASE_EM_DIAS = 3
KM_POR_DIA_DE_PRAZO = 350
FOLGA_MAXIMA_DO_PRAZO_EM_DIAS = 3

FRETE_BASE = 9.90
FRETE_POR_KM = 0.011
VARIACAO_MAXIMA_DO_FRETE = 6.0

QUANTIDADE_DE_ITENS_E_PESOS = ((1, 2, 3), (70, 22, 8))
QUANTIDADE_POR_ITEM_E_PESOS = ((1, 2), (85, 15))

PROPORCAO_DE_PAGAMENTOS_RECUSADOS = 0.04
CARTAO_DE_CREDITO = "Cartão de crédito"
FORMAS_DE_PAGAMENTO_E_PESOS = ((CARTAO_DE_CREDITO, "Pix", "Boleto"), (60, 30, 10))
APROVADO = "Aprovado"
RECUSADO = "Recusado"

EM_TRANSITO = "Em trânsito"
PRAZO_VENCIDO = "Prazo vencido"
ENTREGUE_NO_PRAZO = "Entregue no prazo"
ENTREGUE_COM_ATRASO = "Entregue com atraso"

DOMINIOS_DE_EMAIL = ("email.example", "correio.example", "caixa.example")
# Um número no e-mail evita endereços repetidos entre clientes homônimos.
SUFIXOS_DE_EMAIL = 1000


@dataclass(frozen=True)
class Cliente:
    id: int
    nome: str
    email: str
    cpf: str
    endereco: str
    cidade: str
    uf: str


@dataclass(frozen=True)
class Pedido:
    id: int
    cliente_id: int
    lojista_id: int
    momento_compra: datetime
    valor_frete: Decimal


@dataclass(frozen=True)
class ItemPedido:
    pedido_id: int
    numero: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal


@dataclass(frozen=True)
class Pagamento:
    pedido_id: int
    forma: str
    parcelas: int
    valor: Decimal
    situacao: str


@dataclass(frozen=True)
class Entrega:
    pedido_id: int
    data_prometida: date
    data_entrega: date | None
    situacao: str


@dataclass(frozen=True)
class Vendas:
    clientes: list[Cliente]
    pedidos: list[Pedido]
    itens: list[ItemPedido]
    pagamentos: list[Pagamento]
    entregas: list[Entrega]


@dataclass(frozen=True)
class _PedidoAEntregar:
    pedido_id: int
    dia_da_compra: date
    distancia: float
    risco_relativo_de_atraso: float


@dataclass(frozen=True)
class _SorteioDeLojistas:
    """Sorteia o lojista de um pedido entre os que já tinham fechado no dia da compra."""

    datas_de_fechamento: list[date]
    lojistas: list[int]
    pesos_acumulados: list[float]

    @classmethod
    def criar(
        cls,
        comercial: Comercial,
        produtos_do_lojista: dict[int, list[Produto]],
        que_atrasam: set[int],
    ) -> "_SorteioDeLojistas":
        # O peso de cada lojista é o tamanho do seu catálogo.
        fechamentos = sorted(
            (lead.data_fechamento, lead.lojista_id) for lead in comercial.leads_fechados
        )
        pesos_acumulados: list[float] = []
        acumulado = 0.0
        for _, lojista_id in fechamentos:
            peso = len(produtos_do_lojista[lojista_id])
            if lojista_id in que_atrasam:
                peso *= VOLUME_RELATIVO_DE_QUEM_ATRASA
            acumulado += peso
            pesos_acumulados.append(acumulado)
        return cls(
            datas_de_fechamento=[data for data, _ in fechamentos],
            lojistas=[lojista_id for _, lojista_id in fechamentos],
            pesos_acumulados=pesos_acumulados,
        )

    def sortear(self, rng: random.Random, dia_da_compra: date) -> int:
        # Só vende quem já fechou: o fechamento é anterior ao dia da compra.
        ativos = bisect.bisect_left(self.datas_de_fechamento, dia_da_compra)
        return rng.choices(self.lojistas[:ativos], cum_weights=self.pesos_acumulados[:ativos])[0]


def _momentos_de_compra(rng: random.Random, calendario: Calendario) -> list[datetime]:
    """Os momentos de todas as compras, em ordem, com crescimento e picos de fim de ano."""
    meses: list[tuple[list[date], float]] = []
    for indice in range(MESES_DE_OPERACAO):
        inicio = somar_meses(calendario.inicio_da_janela, indice)
        fim = min(somar_meses(inicio, 1) - timedelta(days=1), calendario.data_referencia)
        dias = dias_entre(inicio, fim)
        peso = (1 + CRESCIMENTO_MENSAL) ** indice * FATOR_SAZONAL_POR_MES.get(inicio.month, 1.0)
        peso *= rng.uniform(1 - VARIACAO_MENSAL, 1 + VARIACAO_MENSAL)
        # Um último mês incompleto, se a referência cair no meio dele, recebe a parte dos dias.
        peso *= len(dias) / calendar.monthrange(inicio.year, inicio.month)[1]
        meses.append((dias, peso))

    soma_dos_pesos = sum(peso for _, peso in meses)
    momentos: list[datetime] = []
    for dias, peso in meses:
        for _ in range(round(PEDIDOS_PREVISTOS * peso / soma_dos_pesos)):
            dia = rng.choice(dias)
            segundos = rng.randint(0, 24 * 3600 - 1)
            momento = datetime.combine(dia, time(), FUSO_DE_BRASILIA)
            momentos.append(momento + timedelta(seconds=segundos))
    momentos.sort()
    return momentos


def _clientes_por_pedido(
    rng: random.Random, momentos: list[datetime], recusados: list[bool], referencia: date
) -> tuple[list[int], set[int]]:
    """Distribui os pedidos entre clientes.

    Devolve, para cada pedido, um número que identifica o seu cliente, e as posições dos
    primeiros pedidos de quem faz recompra. Os pedidos seguintes são sempre aprovados e
    vêm depois de um intervalo mínimo.
    """
    total = len(momentos)
    dias = [m.date() for m in momentos]
    cliente_do_pedido: list[int | None] = [None] * total
    limite = referencia - timedelta(days=DIAS_MINIMOS_ENTRE_O_PRIMEIRO_PEDIDO_E_A_REFERENCIA)
    elegiveis = [i for i in range(total) if not recusados[i] and dias[i] <= limite]

    primeiros = rng.sample(elegiveis, CLIENTES_QUE_RECOMPRAM)
    for cliente, posicao in enumerate(primeiros):
        cliente_do_pedido[posicao] = cliente

    for cliente, posicao in enumerate(primeiros):
        pedidos_do_cliente = 3 if rng.random() < PROPORCAO_DE_QUEM_FAZ_TRES_PEDIDOS else 2
        anterior = posicao
        for _ in range(pedidos_do_cliente - 1):
            inicio = bisect.bisect_left(
                dias, dias[anterior] + timedelta(days=DIAS_MINIMOS_ENTRE_PEDIDOS)
            )
            if inicio >= total:
                break
            for _tentativa in range(TENTATIVAS_DE_ACHAR_O_PROXIMO_PEDIDO):
                candidato = rng.randrange(inicio, total)
                if cliente_do_pedido[candidato] is None and not recusados[candidato]:
                    cliente_do_pedido[candidato] = cliente
                    anterior = candidato
                    break

    # Cada pedido restante é o único pedido de um cliente novo.
    proximo_cliente = CLIENTES_QUE_RECOMPRAM
    clientes: list[int] = []
    for cliente in cliente_do_pedido:
        if cliente is None:
            cliente = proximo_cliente
            proximo_cliente += 1
        clientes.append(cliente)
    return clientes, set(primeiros)


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _novo_cliente(rng: random.Random, fake: Faker, cliente_id: int, cpfs: set[str]) -> Cliente:
    nome = fake.name()
    usuario = re.sub(r"[^a-z]+", ".", _sem_acento(nome).lower()).strip(".")
    cpf = cpf_ficticio(rng)
    while cpf in cpfs:
        cpf = cpf_ficticio(rng)
    cpfs.add(cpf)
    cidade = rng.choices(CIDADES, weights=[c.peso for c in CIDADES])[0]
    return Cliente(
        id=cliente_id,
        nome=nome,
        email=f"{usuario}{cliente_id % SUFIXOS_DE_EMAIL}@{rng.choice(DOMINIOS_DE_EMAIL)}",
        cpf=cpf,
        endereco=fake.street_address(),
        cidade=cidade.nome,
        uf=cidade.uf,
    )


def _lojistas_que_atrasam(
    rng: random.Random, comercial: Comercial, calendario: Calendario
) -> set[int]:
    """Um grupo pequeno de lojistas que entrou cedo e atrasa muito."""
    meio_da_janela = somar_meses(calendario.inicio_da_janela, MESES_DE_OPERACAO // 2)
    candidatos_do_canal: list[int] = []
    candidatos_de_outros: list[int] = []
    for lead in comercial.leads_fechados:
        if lead.data_fechamento >= meio_da_janela:
            continue
        if lead.canal == CANAL_DOS_LOJISTAS_QUE_ATRASAM:
            candidatos_do_canal.append(lead.lojista_id)
        else:
            candidatos_de_outros.append(lead.lojista_id)
    candidatos_do_canal.sort()
    candidatos_de_outros.sort()
    return set(rng.sample(candidatos_do_canal, LOJISTAS_QUE_ATRASAM_DO_CANAL)) | set(
        rng.sample(candidatos_de_outros, LOJISTAS_QUE_ATRASAM_DE_OUTROS_CANAIS)
    )


def _itens_do_pedido(
    rng: random.Random, pedido_id: int, catalogo_do_lojista: list[Produto]
) -> list[ItemPedido]:
    quantidades, pesos = QUANTIDADE_DE_ITENS_E_PESOS
    quantidade_de_itens = min(rng.choices(quantidades, weights=pesos)[0], len(catalogo_do_lojista))
    itens: list[ItemPedido] = []
    for numero, produto in enumerate(rng.sample(catalogo_do_lojista, quantidade_de_itens), 1):
        quantidade = rng.choices(*QUANTIDADE_POR_ITEM_E_PESOS)[0]
        itens.append(ItemPedido(pedido_id, numero, produto.id, quantidade, produto.preco))
    return itens


def _frete(rng: random.Random, distancia: float) -> Decimal:
    valor = FRETE_BASE + distancia * FRETE_POR_KM + rng.uniform(0, VARIACAO_MAXIMA_DO_FRETE)
    return Decimal(f"{valor:.2f}")


def _pagamento(rng: random.Random, pedido_id: int, valor: Decimal, recusado: bool) -> Pagamento:
    forma = rng.choices(*FORMAS_DE_PAGAMENTO_E_PESOS)[0]
    situacao = RECUSADO if recusado else APROVADO
    return Pagamento(pedido_id, forma, _parcelas(rng, forma, valor), valor, situacao)


def _parcelas(rng: random.Random, forma: str, valor: Decimal) -> int:
    if forma != CARTAO_DE_CREDITO:
        return 1
    if valor < 150:
        return rng.randint(1, 2)
    if valor < 600:
        return rng.randint(1, 6)
    return rng.randint(1, 12)


def _risco_relativo_de_atraso(
    distancia: float, lojista_id: int, que_atrasam: set[int], do_canal_que_atrasa: set[int]
) -> float:
    risco = next(r for limite, r in RISCO_RELATIVO_DE_ATRASO_POR_DISTANCIA if distancia < limite)
    if lojista_id in que_atrasam:
        risco *= RISCO_RELATIVO_DE_ATRASO_DE_QUEM_ATRASA
    elif lojista_id in do_canal_que_atrasa:
        risco *= RISCO_RELATIVO_DE_ATRASO_DO_CANAL
    return risco


def _entrega(
    rng: random.Random, pedido: _PedidoAEntregar, chance_de_atraso: float, referencia: date
) -> Entrega:
    dia_da_compra = pedido.dia_da_compra
    prazo = (
        PRAZO_BASE_EM_DIAS
        + round(pedido.distancia / KM_POR_DIA_DE_PRAZO)
        + rng.randint(0, FOLGA_MAXIMA_DO_PRAZO_EM_DIAS)
    )
    prometida = dia_da_compra + timedelta(days=prazo)
    if rng.random() < chance_de_atraso:
        # Metade dos atrasos passa de uma semana.
        dias_de_atraso = rng.randint(1, 7) if rng.random() < 0.5 else rng.randint(8, 25)
        real = prometida + timedelta(days=dias_de_atraso)
        situacao = ENTREGUE_COM_ATRASO
    else:
        real = dia_da_compra + timedelta(days=rng.randint(max(1, prazo // 2), prazo))
        situacao = ENTREGUE_NO_PRAZO
    if real > referencia:
        real = None
        situacao = PRAZO_VENCIDO if prometida < referencia else EM_TRANSITO
    return Entrega(pedido.pedido_id, prometida, real, situacao)


def gerar_vendas(
    rng: random.Random,
    fake: Faker,
    calendario: Calendario,
    comercial: Comercial,
    catalogo: Catalogo,
) -> Vendas:
    referencia = calendario.data_referencia
    momentos = _momentos_de_compra(rng, calendario)
    recusados = [rng.random() < PROPORCAO_DE_PAGAMENTOS_RECUSADOS for _ in momentos]
    cliente_de_cada_pedido, primeiros_de_quem_recompra = _clientes_por_pedido(
        rng, momentos, recusados, referencia
    )

    lojista_por_id: dict[int, Lojista] = {lojista.id: lojista for lojista in comercial.lojistas}
    produtos_do_lojista: dict[int, list[Produto]] = {}
    for produto in catalogo.produtos:
        produtos_do_lojista.setdefault(produto.lojista_id, []).append(produto)
    que_atrasam = _lojistas_que_atrasam(rng, comercial, calendario)
    do_canal_que_atrasa = {
        lead.lojista_id
        for lead in comercial.leads_fechados
        if lead.canal == CANAL_DOS_LOJISTAS_QUE_ATRASAM
    }
    sorteio_de_lojistas = _SorteioDeLojistas.criar(comercial, produtos_do_lojista, que_atrasam)

    clientes: list[Cliente] = []
    cliente_id_de: dict[int, int] = {}
    cpfs: set[str] = set()
    pedidos: list[Pedido] = []
    itens: list[ItemPedido] = []
    pagamentos: list[Pagamento] = []
    a_entregar: list[_PedidoAEntregar] = []

    for posicao, momento in enumerate(momentos):
        pedido_id = posicao + 1
        dia = momento.date()
        numero_do_cliente = cliente_de_cada_pedido[posicao]
        if numero_do_cliente not in cliente_id_de:
            clientes.append(_novo_cliente(rng, fake, len(clientes) + 1, cpfs))
            cliente_id_de[numero_do_cliente] = clientes[-1].id
        cliente = clientes[cliente_id_de[numero_do_cliente] - 1]

        lojista_id = sorteio_de_lojistas.sortear(rng, dia)
        distancia = distancia_km(lojista_por_id[lojista_id].uf, cliente.uf)

        itens_do_pedido = _itens_do_pedido(rng, pedido_id, produtos_do_lojista[lojista_id])
        itens += itens_do_pedido
        frete = _frete(rng, distancia)
        pedidos.append(Pedido(pedido_id, cliente.id, lojista_id, momento, frete))

        valor = sum((i.preco_unitario * i.quantidade for i in itens_do_pedido), frete)
        pagamentos.append(_pagamento(rng, pedido_id, valor, recusados[posicao]))
        if recusados[posicao]:
            continue

        if posicao in primeiros_de_quem_recompra:
            # Quem faz recompra teve a primeira entrega no prazo.
            risco = 0.0
        else:
            risco = _risco_relativo_de_atraso(
                distancia, lojista_id, que_atrasam, do_canal_que_atrasa
            )
        a_entregar.append(_PedidoAEntregar(pedido_id, dia, distancia, risco))

    escala = (
        TAXA_DE_ATRASO_ALVO * len(a_entregar) / sum(p.risco_relativo_de_atraso for p in a_entregar)
    )
    entregas = [
        _entrega(
            rng,
            pedido,
            min(CHANCE_MAXIMA_DE_ATRASO, pedido.risco_relativo_de_atraso * escala),
            referencia,
        )
        for pedido in a_entregar
    ]
    return Vendas(clientes, pedidos, itens, pagamentos, entregas)
