“””
EAC Appeal Status Monitor - WhatsApp via Twilio
Monitora o status do appeal a cada 1 hora e notifica via WhatsApp se mudar.

INSTALACAO:
pip install selenium webdriver-manager twilio

CONFIGURACAO TWILIO (WhatsApp):

1. Crie conta gratis em https://www.twilio.com/try-twilio
1. No console, va em Messaging > Try it out > Send a WhatsApp message
1. Vai aparecer um numero Twilio sandbox (ex: +14155238886)
1. Mande “join <codigo>” pro numero do Twilio pelo seu WhatsApp pra ativar
1. Pegue Account SID, Auth Token e o numero do sandbox no console
1. Preencha as variaveis abaixo
   “””

import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from twilio.rest import Client

# ============================================

# CONFIGURACAO - PREENCHA AQUI

# ============================================

# Twilio

TWILIO_ACCOUNT_SID = “SEU_ACCOUNT_SID”
TWILIO_AUTH_TOKEN = “SEU_AUTH_TOKEN”
TWILIO_WHATSAPP_FROM = “whatsapp:+14155238886”
MY_WHATSAPP_NUMBER = “whatsapp:+5511999999999”

# Monitor

CHECK_INTERVAL = 3600
REFERENCE_ID = “95727d1e-f75d-42bd-804b-78512bff11e8”
EAC_URL = f”https://easy.ac/support/contact/appeal?referenceId={REFERENCE_ID}”

# ============================================

logging.basicConfig(
level=logging.INFO,
format=”%(asctime)s - %(levelname)s - %(message)s”
)
logger = logging.getLogger(**name**)

last_status = None
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp(message: str):
“”“Envia mensagem via WhatsApp (Twilio).”””
try:
msg = twilio_client.messages.create(
body=message,
from_=TWILIO_WHATSAPP_FROM,
to=MY_WHATSAPP_NUMBER
)
logger.info(f”WhatsApp enviado! SID: {msg.sid}”)
except Exception as e:
logger.error(f”Erro ao enviar WhatsApp: {e}”)

def create_driver():
“”“Cria instancia do Chrome headless.”””
opts = Options()
opts.add_argument(”–headless=new”)
opts.add_argument(”–no-sandbox”)
opts.add_argument(”–disable-dev-shm-usage”)
opts.add_argument(”–disable-gpu”)
opts.add_argument(”–window-size=1920,1080”)
opts.add_argument(
“user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) “
“AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36”
)
svc = Service(ChromeDriverManager().install())
return webdriver.Chrome(service=svc, options=opts)

def check_status() -> str | None:
“”“Acessa a pagina do EAC, clica no botao e retorna o status.”””
driver = None
try:
driver = create_driver()
logger.info(f”Acessando {EAC_URL}”)
driver.get(EAC_URL)

```
    # Espera o botao "Check reference ID" aparecer e clica
    btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH,
            "//button[contains(text(), 'Check reference ID')]"
            " | //a[contains(text(), 'Check reference ID')]"
            " | //*[contains(text(), 'Check reference ID')]"
        ))
    )
    btn.click()
    logger.info("Botao 'Check reference ID' clicado")

    # Espera o status aparecer
    time.sleep(5)

    # Pega o texto da pagina
    page_text = driver.find_element(By.TAG_NAME, "body").text

    # Procura por status conhecidos
    status_keywords = [
        "Appeal Pending",
        "Appeal Accepted",
        "Appeal Denied",
        "Appeal Rejected",
        "Ban Reverted",
        "Ban Lifted",
        "Under Review",
        "Permanently Banned",
    ]

    found_status = None
    for kw in status_keywords:
        if kw.lower() in page_text.lower():
            found_status = kw
            break

    if not found_status:
        found_status = f"DESCONHECIDO: {page_text[-200:]}"

    logger.info(f"Status encontrado: {found_status}")
    return found_status

except Exception as e:
    logger.error(f"Erro ao checar status: {e}")
    return None
finally:
    if driver:
        driver.quit()
```

def main():
global last_status

```
logger.info("=" * 50)
logger.info("EAC Appeal Monitor (WhatsApp) iniciado!")
logger.info(f"Reference ID: {REFERENCE_ID}")
logger.info(f"Intervalo: {CHECK_INTERVAL}s ({CHECK_INTERVAL // 60} min)")
logger.info("=" * 50)

send_whatsapp(
    "EAC Monitor iniciado!\n\n"
    f"Reference ID: {REFERENCE_ID}\n"
    f"Checando a cada {CHECK_INTERVAL // 60} minutos\n"
    f"Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)

while True:
    try:
        logger.info(f"Checando status... ({datetime.now().strftime('%H:%M:%S')})")
        status = check_status()

        if status is None:
            logger.warning("Nao foi possivel obter o status")
            send_whatsapp(
                "Erro ao checar status\n"
                "Nao consegui acessar a pagina do EAC. Tentando de novo na proxima hora."
            )
        elif last_status is None:
            # Primeira checagem
            last_status = status
            send_whatsapp(
                f"Status atual do appeal:\n\n"
                f"Status: {status}\n"
                f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
        elif status != last_status:
            # STATUS MUDOU!
            old = last_status
            last_status = status
            send_whatsapp(
                "STATUS DO APPEAL MUDOU!\n\n"
                f"Antes: {old}\n"
                f"Agora: {status}\n\n"
                f"Link: {EAC_URL}\n"
                f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
        else:
            logger.info(f"Status inalterado: {status}")

    except Exception as e:
        logger.error(f"Erro no loop principal: {e}")

    logger.info(f"Proxima checagem em {CHECK_INTERVAL // 60} minutos...")
    time.sleep(CHECK_INTERVAL)
```

if **name** == “**main**”:
main()
