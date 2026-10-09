# Triagem de vagas — instruções (leia antes de qualquer arquivo)

Você vai me ajudar a fazer a **triagem de vagas de emprego** comparando cada vaga com o meu perfil profissional, descrito no **arquivo mestre de competências** que está anexado nesta conversa (ou nos arquivos deste Projeto). Use **somente** o arquivo mestre como fonte sobre mim.

## O que vou enviar

- **{{TOTAL_LOTES}} arquivos de lote**, com **{{TOTAL_VAGAS}} vagas no total**, da semana de {{SEMANA_LEGIVEL}}.
- Nomes, na ordem: `{{PRIMEIRO_LOTE}}` até `{{ULTIMO_LOTE}}`.
- Vou enviar **um lote por mensagem**. Cada lote é um JSON com os campos `lote`, `total_lotes`, `total_vagas`, um `lembrete` e a lista `vagas` (cada vaga tem `job_id`, `titulo`, `empresa`, `local`, `modelo`, `postada`, `link` e `about`, que é a descrição completa).

## O que fazer com cada vaga

1. **`aderencia`** — número inteiro de **0 a 100**: o quanto a vaga combina comigo. Considere, nesta ordem de peso:
   - requisitos obrigatórios que eu atendo ou não (um requisito obrigatório que eu não tenho pesa muito);
   - senioridade e escopo do cargo em relação à minha experiência;
   - stack/tecnologias e domínio de negócio;
   - idioma exigido;
   - modelo de trabalho (presencial / híbrido / remoto) e localização.
   - **A aderência NÃO considera salário**: nem a faixa salarial da vaga nem o meu salário mínimo podem aumentar ou diminuir a nota.
   Seja criterioso: **{{LIMIAR}} ou menos significa que eu não deveria me candidatar** (essas vagas serão descartadas automaticamente).
2. **`salario_min`, `salario_ideal`, `salario_max`** — minha **pretensão de salário-base** para esta vaga, em valor **mensal bruto**, moeda **BRL**, como números inteiros (sem pontos, vírgulas ou símbolos). Baseie-se no cargo, na senioridade, na empresa/porte, na localização e no meu perfil.
   - **Fontes:** consulte o **Glassdoor**, priorizando a **mesma empresa e o mesmo cargo**; cruze com o guia salarial da **Robert Half** e com outras referências disponíveis (pesquisas de mercado, outros sites de salários). Se não conseguir acessar alguma fonte, diga isso no `resumo` em vez de estimar como se tivesse acessado.
   - **Salário-base × remuneração total:** os campos `salario_*` são **somente o salário-base**. A remuneração total (base + bônus/PLR e variáveis, em valor mensal) vai escrita no `resumo`.
   - **Qualidade dos dados:** no `resumo`, aponte dados antigos (informe o ano), amostras pequenas e inconsistências entre as fontes.
   - **Meu salário mínimo é {{SALARIO_MINIMO}}** (CLT mensal). Use apenas como contexto. **Nunca** use esse valor automaticamente como `salario_min`: informe a faixa estimada real da vaga, **mesmo que fique abaixo** do meu mínimo.
   - **Regra fixa: a pretensão é SEMPRE em regime CLT**, mesmo que a vaga seja PJ, cooperado ou outro regime. **Não** converta para PJ — eu mesmo faço a conversão na hora de me candidatar.
   - Se a vaga informar uma faixa salarial em PJ (ou em outra moeda/período), use-a apenas como referência e devolva o **equivalente CLT mensal em BRL**.
3. **`moeda`** — sempre `"BRL"`.
4. **`resumo`** — texto curto, nesta ordem:
   - **Aderência:** 1 a 2 frases com o principal motivo da nota (o que mais combina e o que mais pesa contra);
   - **Salário:** remuneração total estimada (base + variáveis, mensal), fontes usadas e alertas (dados antigos, amostras pequenas, inconsistências, fontes que não foi possível acessar).

## Empresas a ignorar

- **Regra fixa:** vagas destas empresas recebem **sempre `aderencia` 0**, independentemente da descrição: **{{EMPRESAS_BLOQUEADAS}}**. No `resumo`, escreva apenas "Empresa a ignorar".

## Arquivo de resultado (acumulado)

- Mantenha **um único arquivo** chamado **`{{ARQUIVO_RESULTADO}}`**.
- A cada lote recebido, **incremente** esse arquivo com as vagas do lote — **não** apague as anteriores e **não** repita `job_id`.
- Ao terminar cada lote, responda apenas: `lote X/{{TOTAL_LOTES}} concluído — K vagas no arquivo` (sem repetir o conteúdo).
- Se você **não conseguir criar/atualizar arquivos** nesta conversa, então responda, para cada lote, **somente o array JSON daquele lote** dentro de um bloco de código — eu importo um por um.

## Formato obrigatório do resultado

Um **array JSON**, um objeto por vaga, **exatamente** com estes campos:

```json
[
  {
    "job_id": "4468360366",
    "aderencia": 82,
    "salario_min": 18000,
    "salario_ideal": 21000,
    "salario_max": 24000,
    "moeda": "BRL",
    "resumo": "Combina com liderança técnica Java e cloud; pesa contra exigir inglês fluente."
  }
]
```

Regras:
- Copie o **`job_id` exatamente como está no lote** (é um texto; não arredonde, não altere).
- Uma entrada para **cada** vaga de **cada** lote — mesmo que a aderência seja muito baixa.
- **Sem** comentários, campos extras ou texto dentro do JSON.

## Conferência final (depois do lote {{TOTAL_LOTES}})

1. Confira que `{{ARQUIVO_RESULTADO}}` tem **exatamente {{TOTAL_VAGAS}} itens** e que todo `job_id` de todos os lotes aparece **uma única vez**.
2. Se faltar alguma vaga, liste os `job_id` que faltam e avalie-os antes de finalizar.
3. Disponibilize o arquivo `{{ARQUIVO_RESULTADO}}` para download.

Se entendeu, responda apenas: **"Pronto. Pode enviar o {{PRIMEIRO_LOTE}}."**
