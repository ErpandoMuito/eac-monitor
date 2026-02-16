# EAC Appeal Status Monitor - WhatsApp via Twilio

import os
import re
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from twilio.rest import Client

# ============================================
# CONFIGURACAO
# ============================================

TWILIO_ACCOUNT_SID = "ACd9391742c4758eca6a10fbd06a9602e6"
TWILIO_AUTH_TOKEN = "14c5db9d935f8bcd1faa86a612248501"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
MY_WHATSAPP_NUMBER = "whatsapp:+5511941465264"

CHECK_INTERVAL = 600
REFERENCE_ID = "95727d1e-f75d-42bd-804b-78512bff11e8"
EAC_URL = "https://easy.ac/en-US/support/contact/appeal?referenceId=" + REFERENCE_ID

# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def get_elapsed_time(start_time):
    total_seconds = int((datetime.now() - start_time).total_seconds())
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
    opts = uc.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        opts.binary_location = chrome_bin
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    kwargs = {"options": opts}
    if chromedriver_path:
        kwargs["driver_executable_path"] = chromedriver_path
    driver = uc.Chrome(**kwargs)
    driver.set_page_load_timeout(30)
    return driver


def check_status(driver):
    driver.get(EAC_URL)

    btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH,
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'), 'check reference id')]"
        ))
    )
    btn.click()
    time.sleep(5)

    page_text = driver.find_element(By.TAG_NAME, "body").text

    # Busca "Appeal [Status]" na pagina (ex: Appeal Pending, Appeal Reversed)
    # Ignora palavras que fazem parte de frases normais, nao sao status
    skip = {'be', 'is', 'are', 'was', 'were', 'has', 'have', 'had', 'the',
            'a', 'an', 'for', 'through', 'on', 'to', 'and', 'or', 'not',
            'can', 'will', 'may', 'should', 'could', 'would', 'if', 'when',
            'that', 'this', 'of', 'in', 'at', 'your', 'our', 'their'}
    for m in re.finditer(r'\bappeal\b\s*[:\-]?\s*(\w+)', page_text, re.IGNORECASE):
        if m.group(1).lower() not in skip:
            return "Appeal " + m.group(1).capitalize()

    return page_text.strip()[:500]


def main():
    start_time = datetime.now()
    attempt_count = 0
    last_status = None
    driver = None

    logger.info("EAC Appeal Monitor iniciado!")
    logger.info("Reference ID: " + REFERENCE_ID)

    while True:
        attempt_count += 1
        elapsed = get_elapsed_time(start_time)
        logger.info("Tentativa #" + str(attempt_count) + " - " + elapsed)

        try:
            if driver is None:
                driver = create_driver()

            status = check_status(driver)
            logger.info("Status: " + status)

            if last_status is not None and status != last_status:
                for i in range(5):
                    send_whatsapp(
                        "O APPEAL MUDOU! O APPEAL MUDOU!\n"
                        "AGORA E: " + status + "\n\n"
                        "Antes era: " + last_status + "\n"
                        "Tentativa #" + str(attempt_count) + " em " + elapsed + "\n"
                        + EAC_URL
                    )
                    if i < 4:
                        time.sleep(1)
            else:
                send_whatsapp(
                    status + " - Tentativa #" + str(attempt_count)
                    + " em " + elapsed
                )

            last_status = status

        except Exception as e:
            logger.error("Erro: " + str(e))
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
            send_whatsapp(
                "Erro na tentativa #" + str(attempt_count) + " em " + elapsed
                + "\nRecriando browser, proximo check em 10min."
            )

        logger.info("Proxima checagem em 10 min...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
