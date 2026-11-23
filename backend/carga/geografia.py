"""Cidades brasileiras reais, com peso que concentra o volume no Sudeste."""

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
