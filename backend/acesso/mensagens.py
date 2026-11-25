"""Os textos genéricos de erro que a API e o servidor MCP devolvem a quem chama.

Um texto só por situação, igual nos dois serviços. Nenhum diz qual verificação falhou, ecoa o
valor recebido ou cita nomes internos (RS-08): o motivo fica só no log de quem respondeu. Cada
serviço embala o texto no formato do seu protocolo.
"""

# Token ausente ou recusado, na API. O servidor MCP responde o 401 do FastMCP (RFC 6750).
NAO_AUTENTICADO = "Não autenticado."
# O perfil não tem acesso aos dados pedidos: não diz se eles existem (RF-11).
ACESSO_NEGADO = "Acesso negado."
# A ferramenta que não existe e a de outro perfil, no servidor MCP: quem chama não fica sabendo
# que ela existe, e o nome pedido não volta na mensagem.
FERRAMENTA_DESCONHECIDA = "Ferramenta desconhecida."
# Não descreve a validação nem o esquema e não ecoa o valor.
PARAMETRO_INVALIDO = "Parâmetro inválido."
# O provedor ou o banco fora do ar não é negação nem token inválido: quem chama não deve mandar o
# usuário ao login.
SERVICO_INDISPONIVEL = "Serviço indisponível."
# O usuário passou do limite de frequência do servidor MCP: não diz qual é o limite.
MUITAS_CHAMADAS = "Muitas chamadas em pouco tempo. Tente de novo em instantes."
# Qualquer falha não prevista.
ERRO_INTERNO = "Erro interno."

# A pergunta ao assistente não pôde ser respondida: sem modelo configurado, ou o modelo ou o
# servidor MCP falharam no meio da resposta. Não cita provedor, modelo nem ferramenta.
ASSISTENTE_INDISPONIVEL = "O assistente está indisponível no momento. Tente de novo mais tarde."
# A pergunta passou do tempo máximo. Não diz qual é o tempo nem o que demorou.
TEMPO_ESGOTADO = "O assistente demorou demais para responder. Tente de novo."
# A pergunta precisou de mais chamadas de ferramenta do que o teto: a resposta para no que já
# saiu, com este aviso no fim. Não diz qual é o teto.
CONSULTAS_DEMAIS = (
    "A resposta parou aqui: a pergunta precisou de consultas demais. "
    "Tente uma pergunta mais específica."
)
