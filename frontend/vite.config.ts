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
    // O provedor só devolve o usuário para http://localhost:5173 (ENDERECO_DO_FRONTEND).
    server: { host: "localhost", port: 5173, strictPort: true },
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
