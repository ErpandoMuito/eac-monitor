FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y wget gnupg xvfb \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:99

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY eac_monitor.py .
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & sleep 1 && python eac_monitor.py"]
