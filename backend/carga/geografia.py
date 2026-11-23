"""Cidades brasileiras reais, com peso que concentra o volume no Sudeste."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Cidade:
    nome: str
    uf: str
    peso: float


CIDADES: tuple[Cidade, ...] = (
    # Sudeste
    Cidade("São Paulo", "SP", 20),
    Cidade("Campinas", "SP", 4),
    Cidade("Guarulhos", "SP", 3),
    Cidade("Santo André", "SP", 2),
    Cidade("Ribeirão Preto", "SP", 2),
    Cidade("Sorocaba", "SP", 2),
    Cidade("São José dos Campos", "SP", 2),
    Cidade("Santos", "SP", 2),
    Cidade("Osasco", "SP", 2),
    Cidade("Rio de Janeiro", "RJ", 10),
    Cidade("Niterói", "RJ", 2),
    Cidade("Duque de Caxias", "RJ", 1.5),
    Cidade("Nova Iguaçu", "RJ", 1.5),
    Cidade("Belo Horizonte", "MG", 6),
    Cidade("Uberlândia", "MG", 2),
    Cidade("Contagem", "MG", 1.5),
    Cidade("Juiz de Fora", "MG", 1.5),
    Cidade("Vitória", "ES", 1.5),
    Cidade("Vila Velha", "ES", 1),
    # Sul
    Cidade("Curitiba", "PR", 4),
    Cidade("Londrina", "PR", 1.5),
    Cidade("Maringá", "PR", 1),
    Cidade("Porto Alegre", "RS", 4),
    Cidade("Caxias do Sul", "RS", 1.5),
    Cidade("Florianópolis", "SC", 2),
    Cidade("Joinville", "SC", 2),
    Cidade("Blumenau", "SC", 1),
    # Nordeste
    Cidade("Salvador", "BA", 4),
    Cidade("Feira de Santana", "BA", 1),
    Cidade("Recife", "PE", 3.5),
    Cidade("Fortaleza", "CE", 3.5),
    Cidade("São Luís", "MA", 1.5),
    Cidade("Natal", "RN", 1.5),
    Cidade("João Pessoa", "PB", 1.5),
    Cidade("Maceió", "AL", 1.5),
    Cidade("Teresina", "PI", 1.2),
    Cidade("Aracaju", "SE", 1.2),
    # Centro-Oeste
    Cidade("Brasília", "DF", 4),
    Cidade("Goiânia", "GO", 3),
    Cidade("Campo Grande", "MS", 1.5),
    Cidade("Cuiabá", "MT", 1.5),
    # Norte
    Cidade("Manaus", "AM", 2.5),
    Cidade("Belém", "PA", 2.5),
    Cidade("Porto Velho", "RO", 0.8),
    Cidade("Palmas", "TO", 0.6),
    Cidade("Macapá", "AP", 0.5),
    Cidade("Boa Vista", "RR", 0.5),
    Cidade("Rio Branco", "AC", 0.5),
)


# Coordenadas aproximadas das capitais, usadas para a distância entre estados.
CAPITAIS: dict[str, tuple[float, float]] = {
    "AC": (-9.97, -67.81),
    "AL": (-9.67, -35.74),
    "AP": (0.03, -51.07),
    "AM": (-3.12, -60.02),
    "BA": (-12.97, -38.50),
    "CE": (-3.73, -38.52),
    "DF": (-15.79, -47.88),
    "ES": (-20.32, -40.34),
    "GO": (-16.69, -49.26),
    "MA": (-2.53, -44.30),
    "MT": (-15.60, -56.10),
    "MS": (-20.47, -54.62),
    "MG": (-19.92, -43.94),
    "PA": (-1.46, -48.50),
    "PB": (-7.12, -34.86),
    "PR": (-25.43, -49.27),
    "PE": (-8.05, -34.88),
    "PI": (-5.09, -42.80),
    "RJ": (-22.91, -43.17),
    "RN": (-5.79, -35.21),
    "RS": (-30.03, -51.23),
    "RO": (-8.76, -63.90),
    "RR": (2.82, -60.67),
    "SC": (-27.60, -48.55),
    "SP": (-23.55, -46.63),
    "SE": (-10.91, -37.07),
    "TO": (-10.18, -48.33),
}

# Distância nominal de uma entrega dentro do mesmo estado.
DISTANCIA_DENTRO_DO_ESTADO_KM = 150.0


def distancia_km(uf_origem: str, uf_destino: str) -> float:
    """Distância em linha reta entre as capitais de dois estados."""
    if uf_origem == uf_destino:
        return DISTANCIA_DENTRO_DO_ESTADO_KM
    (lat1, lon1), (lat2, lon2) = CAPITAIS[uf_origem], CAPITAIS[uf_destino]
    fi1, fi2 = math.radians(lat1), math.radians(lat2)
    dfi, dlambda = fi2 - fi1, math.radians(lon2 - lon1)
    a = math.sin(dfi / 2) ** 2 + math.cos(fi1) * math.cos(fi2) * math.sin(dlambda / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))
