# EAC Appeal Status Monitor - WhatsApp via Twilio

import os
import re
import time
import logging
from datetime import datetime
import requests
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

TWOCAPTCHA_KEY = os.environ.get("TWOCAPTCHA_KEY", "")

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
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=opts, use_subprocess=True)
    driver.set_page_load_timeout(60)
    return driver


def solve_hcaptcha(sitekey, page_url):
    resp = requests.post("https://2captcha.com/in.php", data={
        "key": TWOCAPTCHA_KEY,
        "method": "hcaptcha",
        "sitekey": sitekey,
        "pageurl": page_url,
        "json": 1
    })
    data = resp.json()
    if data["status"] != 1:
        raise Exception("2Captcha submit: " + str(data))
    task_id = data["request"]
    logger.info("2Captcha task: " + task_id)

    for _ in range(60):
        time.sleep(5)
        resp = requests.get("https://2captcha.com/res.php", params={
            "key": TWOCAPTCHA_KEY,
            "action": "get",
            "id": task_id,
            "json": 1
        })
        data = resp.json()
        if data["status"] == 1:
            return data["request"]
        if data["request"] != "CAPCHA_NOT_READY":
            raise Exception("2Captcha solve: " + str(data))

    raise Exception("2Captcha timeout")


def find_appeal_status(page_text):
    skip = {'an', 'be', 'is', 'are', 'was', 'were', 'has', 'have', 'had',
            'the', 'a', 'for', 'through', 'on', 'to', 'and', 'or', 'not',
            'can', 'will', 'may', 'should', 'could', 'would', 'if', 'when',
            'that', 'this', 'of', 'in', 'at', 'your', 'our', 'their'}
    for m in re.finditer(r'\bappeal\b\s*[:\-]?\s*(\w+)', page_text, re.IGNORECASE):
        if m.group(1).lower() not in skip:
            return "Appeal " + m.group(1).capitalize()
    return None


def extract_sitekey(driver):
    """Tenta extrair o hCaptcha sitekey de varias formas."""
    # Tenta no HTML direto
    m = re.search(r'data-sitekey="([^"]+)"', driver.page_source)
    if m:
        return m.group(1)
    # Tenta via iframe do hCaptcha
    m = re.search(r'hcaptcha\.com/captcha/v1/([a-f0-9\-]+)', driver.page_source)
    if m:
        return m.group(1)
    # Tenta via elemento DOM
    try:
        el = driver.find_element(By.CSS_SELECTOR, '[data-sitekey]')
        return el.get_attribute('data-sitekey')
    except Exception:
        pass
    # Tenta via JavaScript
    try:
        return driver.execute_script(
            "var el = document.querySelector('[data-sitekey]'); "
            "return el ? el.getAttribute('data-sitekey') : null;"
        )
    except Exception:
        pass
    return None


def check_status(driver):
    driver.get(EAC_URL)
    time.sleep(5)

    # Espera ate 15s pelo hCaptcha carregar e extrai sitekey
    sitekey = None
    for _ in range(5):
        sitekey = extract_sitekey(driver)
        if sitekey:
            break
        time.sleep(3)

    if sitekey:
        logger.info("hCaptcha sitekey: " + sitekey)
    else:
        logger.warning("hCaptcha sitekey NAO encontrado no HTML")

    # Resolve hCaptcha via 2Captcha se a key estiver configurada
    captcha_token = None
    if sitekey and TWOCAPTCHA_KEY:
        try:
            captcha_token = solve_hcaptcha(sitekey, EAC_URL)
            logger.info("hCaptcha resolvido!")

            # Injeta o token nos campos de resposta do captcha
            driver.execute_script("""
                var token = arguments[0];
                document.querySelectorAll(
                    '[name="h-captcha-response"], [name="g-recaptcha-response"]'
                ).forEach(function(el) { el.innerHTML = token; el.value = token; });
            """, captcha_token)
        except Exception as e:
            logger.error("Erro 2Captcha: " + str(e))
    elif not TWOCAPTCHA_KEY:
        logger.warning("TWOCAPTCHA_KEY nao configurada - hCaptcha nao sera resolvido")

    # Clica no botao Check reference ID
    btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH,
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'), 'check reference id')]"
        ))
    )
    btn.click()

    # Se o captcha foi resolvido, tenta chamar o callback do hCaptcha
    if captcha_token:
        time.sleep(2)
        driver.execute_script("""
            var token = arguments[0];
            var el = document.querySelector('[data-callback]');
            if (el) {
                var fn = el.getAttribute('data-callback');
                if (fn && window[fn]) window[fn](token);
            }
        """, captcha_token)

    # Espera ate 60s pelo status do appeal aparecer
    try:
        WebDriverWait(driver, 60).until(
            lambda d: find_appeal_status(
                d.find_element(By.TAG_NAME, "body").text
            ) is not None
        )
    except Exception:
        pass

    page_text = driver.find_element(By.TAG_NAME, "body").text
    logger.info("Texto da pagina: " + page_text[:1000])

    status = find_appeal_status(page_text)
    if status:
        return status

    return "SEM STATUS - " + page_text.strip()[:300]


def main():
    start_time = datetime.now()
    attempt_count = 0
    last_status = None
    driver = None

    logger.info("EAC Appeal Monitor iniciado!")
    logger.info("Reference ID: " + REFERENCE_ID)
    if not TWOCAPTCHA_KEY:
        logger.warning("TWOCAPTCHA_KEY nao definida! Setar no ambiente do Render.")

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
