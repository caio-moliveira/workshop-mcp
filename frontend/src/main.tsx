import "@fontsource-variable/geist";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "./estilos/global.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { Aplicacao } from "./Aplicacao";
import { ErrorState } from "./componentes/ErrorState";
import { carregarConfiguracao } from "./configuracao";
import { criarGerenciador } from "./sessao/gerenciador";
import { Sessao } from "./sessao/sessao";

const elemento = document.getElementById("raiz");
if (!elemento) throw new Error("index.html sem o elemento #raiz");
const raiz = createRoot(elemento);

try {
  const configuracao = await carregarConfiguracao();
  const sessao = new Sessao(
    criarGerenciador(configuracao.enderecoDoProvedor),
    configuracao.enderecoDaApi,
    configuracao.inatividadeDaSessaoEmSegundos,
  );
  raiz.render(
    <StrictMode>
      <Aplicacao sessao={sessao} />
    </StrictMode>,
  );
  void sessao.iniciar();
} catch {
  raiz.render(
    <ErrorState
      titulo="Não foi possível abrir o pulso."
      descricao="A configuração da aplicação não pôde ser carregada. Tente de novo em instantes."
      acao="Tentar de novo"
      aoAcionar={() => window.location.reload()}
    />,
  );
}
