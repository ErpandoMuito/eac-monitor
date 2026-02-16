# EAC Appeal Status Monitor - WhatsApp via Twilio
# Monitora o status do appeal a cada 10 minutos e notifica via WhatsApp SEMPRE.
#
# INSTALACAO:
# pip install selenium webdriver-manager twilio
#
# CONFIGURACAO TWILIO (WhatsApp):
# 1. Crie conta gratis em https://www.twilio.com/try-twilio
# 2. No console, va em Messaging > Try it out > Send a WhatsApp message
# 3. Vai aparecer um numero Twilio sandbox (ex: +14155238886)
# 4. Mande "join <codigo>" pro numero do Twilio pelo seu WhatsApp pra ativar
# 5. Pegue Account SID, Auth Token e o numero do sandbox no console
# 6. Preencha as variaveis abaixo

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
TWILIO_ACCOUNT_SID = "SEU_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "SEU_AUTH_TOKEN"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
MY_WHATSAPP_NUMBER = "whatsapp:+5511999999999"

# Monitor
CHECK_INTERVAL = 600
REFERENCE_ID = "95727d1e-f75d-42bd-804b-78512bff11e8"
EAC_URL = "https://easy.ac/support/contact/appeal?referenceId=" + REFERENCE_ID

# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

last_status = None
attempt_count = 0
start_time = None
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def get_elapsed_time():
    if start_time is None:
        return "0min"
    delta = datetime.now() - start_time
    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(str(days) + "d")
    if hours > 0:
        parts.append(str(hours) + "h")
    parts.append(str(minutes) + "min")
    return " ".join(parts)


def send_whatsapp(message):
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=MY_WHATSAPP_NUMBER
        )
        logger.info("WhatsApp enviado! SID: " + msg.sid)
    except Exception as e:
        logger.error("Erro ao enviar WhatsApp: " + str(e))


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)


def check_status():
    driver = None
    try:
        driver = create_driver()
        logger.info("Acessando " + EAC_URL)
        driver.get(EAC_URL)

        btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(text(), 'Check reference ID')]"
                " | //a[contains(text(), 'Check reference ID')]"
                " | //*[contains(text(), 'Check reference ID')]"
            ))
        )
        btn.click()
        logger.info("Botao clicado")

        time.sleep(5)

        page_text = driver.find_element(By.TAG_NAME, "body").text

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
            found_status = "DESCONHECIDO: " + page_text[-200:]

        logger.info("Status encontrado: " + str(found_status))
        return found_status

    except Exception as e:
        logger.error("Erro ao checar status: " + str(e))
        return None
    finally:
        if driver:
            driver.quit()


def main():
    global last_status, attempt_count, start_time

    start_time = datetime.now()

    logger.info("=" * 50)
    logger.info("EAC Appeal Monitor iniciado!")
    logger.info("Reference ID: " + REFERENCE_ID)
    logger.info("Intervalo: " + str(CHECK_INTERVAL) + "s")
    logger.info("=" * 50)

    send_whatsapp(
        "EAC Monitor iniciado!\n\n"
        + "Reference ID: " + REFERENCE_ID + "\n"
        + "Checando a cada " + str(CHECK_INTERVAL // 60) + " minutos\n"
        + "Inicio: " + start_time.strftime("%d/%m/%Y %H:%M")
    )

    while True:
        try:
            attempt_count += 1
            elapsed = get_elapsed_time()

            logger.info("Tentativa #" + str(attempt_count) + " - " + elapsed)
            status = check_status()

            if status is None:
                send_whatsapp(
                    "Erro ao checar status\n"
                    + "Tentativa #" + str(attempt_count) + " - " + elapsed + "\n"
                    + "Nao consegui acessar a pagina. Tentando em 10 min."
                )
            elif last_status is not None and status != last_status:
                old = last_status
                last_status = status
                send_whatsapp(
                    "STATUS DO APPEAL MUDOU!\n\n"
                    + "ANTES: " + old + "\n"
                    + "AGORA: " + status + "\n\n"
                    + "Tentativa #" + str(attempt_count) + " - " + elapsed + "\n"
                    + "Link: " + EAC_URL + "\n"
                    + datetime.now().strftime("%d/%m/%Y %H:%M")
                )
            else:
                last_status = status
                send_whatsapp(
                    status + " - Tentativa #" + str(attempt_count) + " em " + elapsed + "\n"
                    + datetime.now().strftime("%d/%m/%Y %H:%M")
                )

        except Exception as e:
            logger.error("Erro no loop principal: " + str(e))

        logger.info("Proxima checagem em " + str(CHECK_INTERVAL // 60) + " minutos...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
