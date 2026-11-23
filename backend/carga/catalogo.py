"""Catálogo: categorias e produtos, cada produto vendido por um lojista."""

import random
from dataclasses import dataclass
from decimal import Decimal

from carga.comercial import Lojista

PRODUTOS_PREVISTOS = 2000


@dataclass(frozen=True)
class ModeloDeCategoria:
    nome: str
    itens: tuple[str, ...]
    variantes: tuple[str, ...]
    preco_minimo: int
    preco_maximo: int
    peso: float


CATEGORIAS: tuple[ModeloDeCategoria, ...] = (
    ModeloDeCategoria(
        "Eletrônicos",
        ("Fone de ouvido", "Caixa de som", "Smart TV", "Soundbar", "Câmera de segurança"),
        ("Bluetooth", "sem fio", "Wi-Fi", "compacto", "Pro"),
        80,
        3500,
        1.4,
    ),
    ModeloDeCategoria(
        "Informática",
        ("Notebook", "Mouse", "Teclado", "Monitor", "SSD", "Roteador"),
        ("gamer", "sem fio", "mecânico", "Full HD", "1 TB", "dual band"),
        40,
        6000,
        1.2,
    ),
    ModeloDeCategoria(
        "Celulares e acessórios",
        ("Smartphone", "Capinha", "Carregador", "Película", "Fone com fio"),
        ("128 GB", "turbo", "de vidro", "USB-C", "antiqueda"),
        20,
        4500,
        1.5,
    ),
    ModeloDeCategoria(
        "Eletrodomésticos",
        ("Air fryer", "Liquidificador", "Micro-ondas", "Aspirador de pó", "Cafeteira"),
        ("110 V", "220 V", "inox", "digital", "compacto"),
        90,
        2800,
        1.3,
    ),
    ModeloDeCategoria(
        "Casa e decoração",
        ("Luminária", "Quadro decorativo", "Vaso", "Espelho", "Tapete"),
        ("moderno", "rústico", "redondo", "grande", "minimalista"),
        25,
        900,
        1.2,
    ),
    ModeloDeCategoria(
        "Cama, mesa e banho",
        ("Jogo de lençol", "Toalha de banho", "Edredom", "Travesseiro", "Toalha de mesa"),
        ("casal", "solteiro", "algodão", "queen", "300 fios"),
        30,
        600,
        1.0,
    ),
    ModeloDeCategoria(
        "Móveis",
        ("Rack", "Escrivaninha", "Cadeira", "Estante", "Sofá"),
        ("de madeira", "retrátil", "de escritório", "3 lugares", "branco"),
        150,
        4000,
        0.8,
    ),
    ModeloDeCategoria(
        "Moda feminina",
        ("Vestido", "Blusa", "Saia", "Calça jeans", "Bolsa"),
        ("floral", "de linho", "midi", "cintura alta", "de couro"),
        40,
        450,
        1.3,
    ),
    ModeloDeCategoria(
        "Moda masculina",
        ("Camiseta", "Camisa social", "Bermuda", "Jaqueta", "Calça chino"),
        ("básica", "slim", "de algodão", "corta-vento", "estampada"),
        35,
        500,
        1.1,
    ),
    ModeloDeCategoria(
        "Calçados",
        ("Tênis", "Sandália", "Bota", "Sapatênis", "Chinelo"),
        ("de corrida", "casual", "de couro", "infantil", "confort"),
        30,
        700,
        1.1,
    ),
    ModeloDeCategoria(
        "Beleza e perfumaria",
        ("Perfume", "Hidratante", "Shampoo", "Base", "Kit de maquiagem"),
        ("100 ml", "vegano", "sem sulfato", "matte", "importado"),
        20,
        650,
        1.2,
    ),
    ModeloDeCategoria(
        "Saúde e bem-estar",
        ("Termômetro", "Medidor de pressão", "Suplemento", "Massageador", "Balança"),
        ("digital", "de pulso", "em pó", "elétrico", "corporal"),
        30,
        500,
        0.8,
    ),
    ModeloDeCategoria(
        "Esporte e lazer",
        ("Bicicleta", "Halteres", "Tapete de yoga", "Barraca", "Bola"),
        ("aro 29", "2 kg", "antiderrapante", "4 pessoas", "oficial"),
        30,
        2500,
        0.9,
    ),
    ModeloDeCategoria(
        "Brinquedos",
        ("Quebra-cabeça", "Boneca", "Carrinho", "Jogo de tabuleiro", "Blocos de montar"),
        ("1000 peças", "articulada", "de controle remoto", "educativo", "infantil"),
        25,
        450,
        0.9,
    ),
    ModeloDeCategoria(
        "Bebês",
        ("Carrinho de bebê", "Mamadeira", "Cadeirinha para carro", "Body", "Babá eletrônica"),
        ("dobrável", "anticólica", "isofix", "de algodão", "com vídeo"),
        20,
        1800,
        0.7,
    ),
    ModeloDeCategoria(
        "Livros",
        ("Romance", "Livro de receitas", "Biografia", "Livro infantil", "Box de ficção"),
        ("edição de bolso", "capa dura", "ilustrado", "nacional", "edição especial"),
        20,
        250,
        0.9,
    ),
    ModeloDeCategoria(
        "Papelaria",
        ("Caderno", "Kit de canetas", "Agenda", "Mochila escolar", "Estojo"),
        ("universitário", "coloridas", "2027", "com rodinhas", "grande"),
        10,
        300,
        0.7,
    ),
    ModeloDeCategoria(
        "Automotivo",
        ("Pneu", "Som automotivo", "Capa de banco", "Aspirador automotivo", "Kit de limpeza"),
        ("aro 15", "Bluetooth", "universal", "12 V", "completo"),
        30,
        1200,
        0.8,
    ),
    ModeloDeCategoria(
        "Ferramentas e construção",
        ("Furadeira", "Parafusadeira", "Jogo de chaves", "Escada", "Serra circular"),
        ("de impacto", "a bateria", "40 peças", "de alumínio", "1400 W"),
        35,
        1500,
        0.8,
    ),
    ModeloDeCategoria(
        "Pet shop",
        ("Ração", "Cama para pet", "Arranhador", "Coleira", "Areia sanitária"),
        ("15 kg", "grande", "para gatos", "ajustável", "biodegradável"),
        15,
        400,
        0.9,
    ),
)


@dataclass(frozen=True)
class Categoria:
    id: int
    nome: str


@dataclass(frozen=True)
class Produto:
    id: int
    nome: str
    categoria_id: int
    lojista_id: int
    preco: Decimal


@dataclass(frozen=True)
class Catalogo:
    categorias: list[Categoria]
    produtos: list[Produto]


def _preco(rng: random.Random, modelo: ModeloDeCategoria) -> Decimal:
    """Preço com mais itens baratos que caros, terminado em ,90 ou ,99."""
    fracao = rng.random() ** 2
    reais = int(modelo.preco_minimo + fracao * (modelo.preco_maximo - modelo.preco_minimo))
    return Decimal(f"{reais}.{rng.choice(('90', '99'))}")


def _especialidades(
    rng: random.Random, pesos: list[float], obrigatoria: int | None = None
) -> list[int]:
    """As 1 a 3 categorias em que um lojista vende."""
    quantidade = rng.randint(1, 3)
    escolhidas = [] if obrigatoria is None else [obrigatoria]
    while len(escolhidas) < quantidade:
        candidata = rng.choices(range(len(pesos)), weights=pesos)[0]
        if candidata not in escolhidas:
            escolhidas.append(candidata)
    return escolhidas


def gerar_catalogo(rng: random.Random, lojistas: list[Lojista]) -> Catalogo:
    categorias = [Categoria(i, m.nome) for i, m in enumerate(CATEGORIAS, start=1)]
    pesos_das_categorias = [m.peso for m in CATEGORIAS]

    especialidades = [
        _especialidades(rng, pesos_das_categorias, obrigatoria=posicao)
        if posicao < len(CATEGORIAS)
        else _especialidades(rng, pesos_das_categorias)
        for posicao in range(len(lojistas))
    ]
    # Poucos lojistas concentram o catálogo.
    tamanho_relativo = [rng.paretovariate(1.5) for _ in lojistas]

    # Todo lojista tem ao menos um produto; o restante segue o porte.
    vendedor_de_cada_produto = list(range(len(lojistas)))
    vendedor_de_cada_produto += rng.choices(
        range(len(lojistas)),
        weights=tamanho_relativo,
        k=PRODUTOS_PREVISTOS - len(vendedor_de_cada_produto),
    )

    produtos: list[Produto] = []
    for posicao, vendedor in enumerate(vendedor_de_cada_produto):
        if posicao < len(CATEGORIAS):
            # O primeiro produto dos 20 primeiros lojistas garante toda categoria no catálogo.
            indice_categoria = especialidades[vendedor][0]
        else:
            indice_categoria = rng.choice(especialidades[vendedor])
        modelo = CATEGORIAS[indice_categoria]
        nome = f"{rng.choice(modelo.itens)} {rng.choice(modelo.variantes)}"
        produtos.append(
            Produto(
                id=posicao + 1,
                nome=nome,
                categoria_id=indice_categoria + 1,
                lojista_id=lojistas[vendedor].id,
                preco=_preco(rng, modelo),
            )
        )
    return Catalogo(categorias=categorias, produtos=produtos)
