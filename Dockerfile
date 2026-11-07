FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY litagent ./litagent
ENV PORT=8080
CMD ["python", "-m", "litagent.server"]
