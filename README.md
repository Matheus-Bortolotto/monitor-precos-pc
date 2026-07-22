# Monitor de preços - PC Build

Verifica o preço de produtos específicos e avisa por e-mail quando o preço
cair abaixo do valor definido. Roda automaticamente 2x por dia via GitHub Actions.

## Testar localmente antes de subir pro GitHub (opcional, recomendado)

1. Copie o arquivo `.env.example` e renomeie a cópia para `.env`
2. Preencha o `.env` com seu e-mail, senha de app e destinatário
3. Rode:
   ```
   pip install -r requirements.txt
   python price_watch.py
   ```
4. O script lê o `.env` automaticamente — não precisa configurar variável de ambiente manualmente

**Importante**: o `.env` tem sua senha de app dentro dele. O arquivo `.gitignore`
já está configurado pra nunca subir esse arquivo pro GitHub — mesmo assim,
confira antes de fazer upload que ele não está marcado pra ir junto.

## Passo 1 — Criar uma senha de app do Gmail (gratuito, 3 minutos)

O Gmail não deixa mais usar sua senha normal em scripts — é preciso gerar uma
"senha de app" específica pra isso. Se você não usa Gmail, qualquer outro
provedor com suporte a SMTP funciona (Outlook, Yahoo, etc.) — só muda o
`SMTP_SERVER` no passo 3.

1. Entre em https://myaccount.google.com/security
2. Ative a **verificação em duas etapas**, se ainda não tiver ativado (obrigatório pra gerar senha de app)
3. Acesse https://myaccount.google.com/apppasswords
4. Dê um nome (ex: "monitor de preços") e clique em criar
5. O Google vai te mostrar uma senha de 16 letras, tipo `abcd efgh ijkl mnop` — copia e guarda (sem os espaços)

## Passo 2 — Subir esse projeto no GitHub

1. Crie um repositório novo no GitHub (pode ser público ou privado — público não gasta minutos)
2. Faça upload de toda essa pasta `price_watch/` pro repositório (incluindo a pasta `.github/`)

## Passo 3 — Cadastrar os "secrets" (senhas seguras do GitHub)

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

Cadastre três secrets:
- `EMAIL_ADDRESS` → o e-mail que vai enviar o alerta (ex: `seuemail@gmail.com`)
- `EMAIL_PASSWORD` → a senha de app do Passo 1 (as 16 letras, sem espaço)
- `EMAIL_TO` → o e-mail que vai receber o alerta (pode ser o mesmo `EMAIL_ADDRESS`, ou outro)

Se não usar Gmail, cadastre também `SMTP_SERVER` (ex: `smtp-mail.outlook.com`) e,
se a porta não for 587, `SMTP_PORT`.

## Passo 4 — Editar products.json com seus produtos reais

Cada produto tem uma lista de **`sources`** — um link por loja, cada um com
seu **próprio seletor de preço** (Kabum, Pichau e Mercado Livre têm
estruturas de página diferentes, então não dá pra usar o mesmo seletor pros
três). O script verifica todas as fontes e usa o **menor preço encontrado**
entre elas.

Exemplo:
```json
{
  "name": "Nome do produto",
  "target_price": 500.00,
  "sources": [
    { "url": "https://www.kabum.com.br/produto/x", "price_selector": "h4.text-4xl.text-secondary-500" },
    { "url": "https://www.pichau.com.br/produto-x", "price_selector": "NAO_CONFIRMADO" }
  ]
}
```

**Seletores já confirmados** (baseado em inspeção real de página):
- **Kabum**: `h4.text-4xl.text-secondary-500`
- **Mercado Livre**: `.andes-money-amount__fraction`

**Ainda não confirmados** (marcados como `"NAO_CONFIRMADO"` no arquivo):
- **Pichau** — em todos os produtos que têm link da Pichau

Um seletor marcado como `"NAO_CONFIRMADO"` simplesmente não encontra o preço
e o script pula aquele link (sem travar) — mas ele nunca conta como "menor
preço" até você confirmar o seletor certo. Uma vez confirmado num produto da
Pichau, o mesmo seletor deve funcionar em todos os outros produtos da
Pichau, já que costuma ser a mesma classe no site inteiro.

### Como descobrir o `price_selector` de cada loja

O seletor CSS indica onde fica o preço na página. Ele muda de loja pra loja e
pode mudar quando o site é atualizado. Pra descobrir:

1. Abra a página do produto no Chrome
2. Clique com botão direito em cima do preço → "Inspecionar"
3. Procure a classe CSS do elemento que contém o preço (ex: `class="finalPrice"`)
4. Use esse valor no campo `price_selector`, com um ponto na frente: `.finalPrice`

Isso é o ponto mais frágil do script — se a loja mudar o layout do site, o
seletor para de funcionar e você vai ver um aviso no log do GitHub Actions
("seletor não encontrou nada"). Nesse caso, é só repetir os passos acima
pra achar o novo seletor.

## Passo 5 — Testar

No GitHub, vá em **Actions → Verificar preços → Run workflow** pra rodar manualmente
e confirmar que está tudo certo antes de esperar o horário agendado.

## Resumo de custo

- GitHub Actions: gratuito (repositório público = ilimitado; privado = 2.000 min/mês grátis, e esse script usa poucos minutos por execução)
- Envio de e-mail via Gmail SMTP: 100% gratuito, sem limite prático pro seu uso