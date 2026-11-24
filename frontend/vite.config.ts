import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type Plugin } from "vite";

/**
 * No servidor de desenvolvimento, a configuração da aplicação vem do mesmo `backend/.env` que o
 * compose usa. No compose, quem serve `/configuracao.json` é o nginx (nginx/default.conf.template).
 */
function configuracaoDeDesenvolvimento(ambiente: Record<string, string>): Plugin {
  const configuracao = {
    enderecoDoProvedor: ambiente.ENDERECO_PUBLICO_DO_PROVEDOR ?? "http://localhost:8080",
    enderecoDaApi: ambiente.ENDERECO_DA_API ?? `http://127.0.0.1:${ambiente.API_PORT ?? "8000"}`,
    // O mesmo padrão de x-sessao no compose.yaml, que o provedor do ambiente usa.
    inatividadeDaSessaoEmSegundos: Number(ambiente.INATIVIDADE_DA_SESSAO_EM_SEGUNDOS ?? "1800"),
  };
  return {
    name: "configuracao-de-desenvolvimento",
    configureServer(servidor) {
      servidor.middlewares.use("/configuracao.json", (_requisicao, resposta) => {
        resposta.setHeader("Content-Type", "application/json");
        resposta.setHeader("Cache-Control", "no-store");
        resposta.end(JSON.stringify(configuracao));
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const pastaDoBackend = fileURLToPath(new URL("../backend", import.meta.url));
  const ambiente = { ...loadEnv(mode, pastaDoBackend, ""), ...process.env } as Record<
    string,
    string
  >;
  return {
    plugins: [react(), configuracaoDeDesenvolvimento(ambiente)],
    // Mesmo endereço e porta do contêiner do frontend: com os dois no ar, o Vite recusa subir em
    // vez de dividir `localhost` com o nginx (IPv6 de um lado, IPv4 do outro). Abra
    // http://localhost:5173, o único retorno que o provedor aceita (ENDERECO_DO_FRONTEND).
    server: { host: "127.0.0.1", port: 5173, strictPort: true },
    build: {
      rollupOptions: {
        input: {
          aplicacao: fileURLToPath(new URL("index.html", import.meta.url)),
          renovacao: fileURLToPath(new URL("renovacao.html", import.meta.url)),
        },
      },
    },
  };
});
