# LinkeSearch

Sistema local que reúne as vagas da aba **Jobs** do LinkedIn (a busca "Show all" gerada pelas suas preferências de carreira) numa lista única, **sem paginação**, **ordenada pela data de postagem** (mais recente primeiro) e com status claros de **Visualizada** e **Apply clicado**.

- **backend/**: Python, FastAPI e Playwright. Coleta as vagas e grava a memória semanal em SQLite (o `sqlite3` já vem no Python).
- **frontend/**: Next.js, TypeScript e Tailwind. Tem três telas: login, comandos e vagas (lista à esquerda, detalhe à direita).

## Instalação (uma vez)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..\frontend
npm install
```

O navegador usado é o **Google Chrome instalado**, com um **perfil separado** em `.data/browser-profile`. O seu perfil normal do Chrome não é tocado. Para usar o Chromium do Playwright, rode `playwright install chromium` e defina `LINKESEARCH_BROWSER_CHANNEL=` (vazio) no `backend/.env`.

## Uso

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

1. **Login**: na primeira vez, "Conectar ao LinkedIn" abre o Chrome para você logar (Google SSO funciona). Depois disso a sessão fica salva e a tela segue direto.
2. **Comandos**:
   - **Buscar NOVAS vagas**: busca as vagas das últimas 24h. Pode ser cancelada no meio, e o que já foi lido fica gravado. Se a última busca foi há mais de 24h, sugere uma janela maior, em passos de 12h (26h → 36h).
   - **Consultar vagas LIDAS**: escolhe uma semana gravada e abre sem fazer nova busca.
   - **Limpar vagas**: escolhe uma semana e exclui o arquivo, com confirmação.
3. **Vagas**: filtros por Visualizada, Apply clicado e data de postagem (2/4/6/12/24h), mais o filtro **"Não listar vagas ignoradas"**, que vem marcado. Os botões são Aplicar e Reset. **🚫 Ignorar vaga** esconde a vaga sem apagá-la do arquivo. Só você marca isso: vagas vindas do LinkedIn (novas, atualizadas ou repostadas) nunca chegam ignoradas, e a sua marcação é mantida nas buscas seguintes. Para desfazer, desmarque o filtro e use "Voltar a listar". Abrir uma vaga marca como visualizada aqui. Clicar no APPLY abre o link externo da empresa e registra o clique.

## Memória semanal

`.data/memory/vagas_AAAAMMDD.db`: um arquivo por semana, com a data do **domingo**. No domingo a busca cria o arquivo novo; nos demais dias, incrementa o do último domingo. Vagas repetidas não são duplicadas, nem entre semanas. Se o status no LinkedIn mudar (Viewed/Applied), a "data em que foi localizada" é atualizada. `.data/state.json` guarda a última execução.

## Como os dados são obtidos

| Dado | Origem | Quando |
|---|---|---|
| Lista (título, empresa, local, Viewed/Applied, "Posted X ago") | página de resultados renderizada (headless), `&start=25` por página | na busca |
| Data de postagem das vagas cujo card mostra "Viewed"/"Applied" no lugar da data | `GET /jobs/view/<id>/` (HTML, sem executar JS) | na busca |
| Link externo do Apply | `GET /jobs/view/<id>/` | ao abrir a vaga (fica salvo) |
| About completo | componente interno `aboutTheJob` do LinkedIn (stream RSC convertido em HTML seguro) | ao abrir a vaga (fica salvo) |

- O coletor **nunca clica** nas vagas. Abrir uma vaga no LinkedIn a marca como "Viewed", e isso falsearia o status. Os detalhes vêm por requisição HTTP direta, que não registra visualização.
- A busca das suas preferências costuma trazer mais de 200 vagas em 24h. Por isso a busca lê só a lista (~2–5 min) e grava a cada página, e o About e o Apply são carregados (~2s) quando você abre a vaga.
- "Repostada" indica que a empresa republicou uma vaga antiga. O LinkedIn a inclui nas últimas 24h com o rótulo "Reposted".

## Segurança

- A API escuta só em `127.0.0.1`, e o CORS aceita apenas `http://localhost:3000`.
- O cookie de sessão fica só no perfil `.data/browser-profile`. Ele nunca é enviado ao frontend nem gravado em log. "Deslogar" limpa apenas o cache da aplicação e mantém o cookie.
- O About é sanitizado duas vezes: allowlist de tags no backend e DOMPurify no frontend. Os links de Apply só abrem se forem `http(s)`, com `rel="noopener noreferrer"`.
- `.data/` está no `.gitignore`.

> ⚠ Automatizar o LinkedIn vai contra os Termos de Uso dele. O sistema reduz o risco com uso sob demanda, pausas aleatórias e volume baixo, mas o risco não é zero.

## Testes

```powershell
cd backend; .venv\Scripts\python -m pytest
```
