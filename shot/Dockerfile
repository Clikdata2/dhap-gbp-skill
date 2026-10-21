# DHAP proof service: Chromium for signed-out screenshots (Playwright's official image, pinned to the library version).
FROM mcr.microsoft.com/playwright/python:v1.64.0-noble
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py proof_popup.py ./
ENV PYTHONUNBUFFERED=1
CMD exec functions-framework --target=app --port=${PORT:-8080}
