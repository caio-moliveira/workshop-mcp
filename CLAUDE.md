## Fluxo de branches

- Toda branch de trabalho é criada a partir de `homolog`.
- Todo pull request de branch de trabalho tem `homolog` como destino (`gh pr create --base homolog`).
- Somente `homolog` abre pull request para `main`.
- Nunca fazer commit ou push direto em `main` ou `homolog`.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues (caio-moliveira/workshop-mcp). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
