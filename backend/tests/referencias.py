"""Fontes de verdade independentes do gerador, usadas pelos testes."""

REGIAO_POR_UF = {
    **dict.fromkeys(["SP", "RJ", "MG", "ES"], "Sudeste"),
    **dict.fromkeys(["PR", "SC", "RS"], "Sul"),
    **dict.fromkeys(["BA", "PE", "CE", "MA", "RN", "PB", "AL", "PI", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
    **dict.fromkeys(["AM", "PA", "RO", "TO", "AP", "RR", "AC"], "Norte"),
}


def cnpj_valido(cnpj: str) -> bool:
    """Validação oficial dos dois dígitos verificadores do CNPJ."""
    if len(cnpj) != 14 or not cnpj.isdigit():
        return False
    numeros = [int(c) for c in cnpj]
    for tamanho in (12, 13):
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        resto = sum(n * p for n, p in zip(numeros[:tamanho], pesos, strict=True)) % 11
        if numeros[tamanho] != (0 if resto < 2 else 11 - resto):
            return False
    return True
