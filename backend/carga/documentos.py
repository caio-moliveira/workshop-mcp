"""Documentos fictícios: formato plausível, mas nunca válidos."""

import random

_PESOS_PRIMEIRO_DIGITO = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_SEGUNDO_DIGITO = (6, *_PESOS_PRIMEIRO_DIGITO)


def _digito_verificador(digitos: list[int], pesos: tuple[int, ...]) -> int:
    resto = sum(d * p for d, p in zip(digitos, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_ficticio(rng: random.Random) -> str:
    """Um CNPJ de 14 dígitos com o primeiro dígito verificador errado de propósito.

    Um CNPJ que não passa na validação não pode pertencer a uma empresa real.
    """
    base = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(11)]
    correto = _digito_verificador(base, _PESOS_PRIMEIRO_DIGITO)
    errado = (correto + rng.randint(1, 9)) % 10
    segundo = _digito_verificador([*base, errado], _PESOS_SEGUNDO_DIGITO)
    return "".join(str(d) for d in [*base, errado, segundo])


_PESOS_DO_CPF_PRIMEIRO = (10, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_DO_CPF_SEGUNDO = (11, *_PESOS_DO_CPF_PRIMEIRO)


def cpf_ficticio(rng: random.Random) -> str:
    """Um CPF de 11 dígitos com o primeiro dígito verificador errado de propósito."""
    base = [rng.randint(0, 9) for _ in range(9)]
    correto = _digito_verificador(base, _PESOS_DO_CPF_PRIMEIRO)
    errado = (correto + rng.randint(1, 9)) % 10
    segundo = _digito_verificador([*base, errado], _PESOS_DO_CPF_SEGUNDO)
    return "".join(str(d) for d in [*base, errado, segundo])
