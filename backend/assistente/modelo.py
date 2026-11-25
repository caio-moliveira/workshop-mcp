"""O modelo de linguagem do assistente, escolhido pela configuração (RF-16)."""

import logging
import os

from pydantic_ai.exceptions import UserError
from pydantic_ai.models import Model, infer_model

registro = logging.getLogger("assistente")

# No formato `provedor:modelo` do PydanticAI. A chave fica na variável que o provedor espera
# (ANTHROPIC_API_KEY no padrão), lida pelo próprio provedor.
MODELO_PADRAO = "anthropic:claude-haiku-5-5"


def modelo_do_ambiente() -> Model | None:
    """O modelo de MODELO_DO_ASSISTENTE, ou o padrão quando ela falta.

    Sem a chave do provedor, ou com um modelo desconhecido, não há modelo: a API sobe assim
    mesmo, e a rota do assistente responde que ele está indisponível.
    """
    nome = os.environ.get("MODELO_DO_ASSISTENTE") or MODELO_PADRAO
    try:
        return infer_model(nome)
    except UserError as erro:
        registro.warning("assistente indisponível: %s", erro)
        return None
