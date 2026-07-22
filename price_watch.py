"""
Monitor de preços - PC Build
Verifica o preço de produtos cadastrados em products.json e envia
uma notificação no Telegram quando o preço cair abaixo do alvo definido.

Como funciona:
1. Lê a lista de produtos em products.json (url, seletor CSS do preço, preço alvo)
2. Faz o download da página de cada produto
3. Extrai o preço usando o seletor CSS configurado
4. Se o preço atual <= preço alvo, envia mensagem no Telegram

Uso local:
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN="seu_token_aqui"
    export TELEGRAM_CHAT_ID="seu_chat_id_aqui"
    python price_watch.py
"""

import json
import os
import re
import smtplib
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env na mesma pasta do script, se existir

HEADERS = {
    # User-Agent de navegador comum, evita bloqueio básico de bot em algumas lojas
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")  # e-mail que envia (ex: Gmail)
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")  # senha de app (não a senha normal)
EMAIL_TO = os.environ.get("EMAIL_TO")  # e-mail que recebe o alerta
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

PRODUCTS_FILE = Path(__file__).parent / "products.json"
STATE_FILE = Path(__file__).parent / "last_prices.json"


def parse_price_text(text: str) -> float | None:
    """Converte texto tipo 'R$ 1.349,00' ou '$639.99' em float."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", text).strip()
    if not cleaned:
        return None
    # Formato brasileiro: 1.349,00 -> 1349.00
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_price(url: str, selector: str) -> float | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[erro] falha ao acessar {url}: {exc}", file=sys.stderr)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    element = soup.select_one(selector)
    if element is None:
        print(f"[aviso] seletor '{selector}' não encontrou nada em {url}", file=sys.stderr)
        return None

    return parse_price_text(element.get_text())


def send_email(subject: str, body: str) -> bool:
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD or not EMAIL_TO:
        print("[aviso] EMAIL_ADDRESS, EMAIL_PASSWORD ou EMAIL_TO não configurados; pulando envio.")
        print(body)
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, [EMAIL_TO], msg.as_string())
        return True
    except smtplib.SMTPException as exc:
        print(f"[erro] falha ao enviar e-mail: {exc}", file=sys.stderr)
        return False


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    products = load_json(PRODUCTS_FILE, [])
    last_prices = load_json(STATE_FILE, {})

    if not products:
        print("Nenhum produto cadastrado em products.json.")
        return

    for product in products:
        name = product["name"]
        # aceita o formato novo "sources" (cada link com seu próprio seletor)
        # ou o formato antigo "urls" + "price_selector" único (compatibilidade)
        if "sources" in product:
            sources = product["sources"]
        else:
            shared_selector = product["price_selector"]
            sources = [{"url": u, "price_selector": shared_selector} for u in product.get("urls") or [product["url"]]]

        target_price = float(product["target_price"])

        print(f"Verificando: {name} ...")

        best_price = None
        best_url = None

        for source in sources:
            url = source["url"]
            selector = source["price_selector"]
            price = fetch_price(url, selector)
            time.sleep(2)  # evita bater muito rápido no mesmo host

            if price is None:
                continue

            print(f"  {url}\n    preço encontrado: R$ {price:.2f}")

            if best_price is None or price < best_price:
                best_price = price
                best_url = url

        if best_price is None:
            print(f"  [aviso] não consegui obter preço de nenhum link de '{name}'.")
            continue

        print(f"  melhor preço: R$ {best_price:.2f} (alvo: R$ {target_price:.2f})")

        state_key = name  # usa o nome do produto como chave, já que agora há várias URLs
        previous = last_prices.get(state_key)

        if best_price <= target_price:
            # só notifica de novo se não tiver sido notificado com sucesso antes pra esse preço
            if previous is None or previous > target_price:
                subject = f"🔔 {name} caiu de preço!"
                body = (
                    f"{name} caiu de preço!\n\n"
                    f"Melhor preço encontrado: R$ {best_price:.2f}\n"
                    f"Alvo definido: R$ {target_price:.2f}\n\n"
                    f"Link: {best_url}"
                )
                sent = send_email(subject, body)
                if sent:
                    last_prices[state_key] = best_price
                else:
                    print("  [aviso] e-mail não foi enviado; vou tentar de novo na próxima execução.")
            else:
                print("  já estava abaixo do alvo na última checagem, sem notificação repetida.")
                last_prices[state_key] = best_price
        else:
            # preço acima do alvo: atualiza o estado normalmente (nada pra notificar)
            last_prices[state_key] = best_price

    save_json(STATE_FILE, last_prices)


if __name__ == "__main__":
    main()