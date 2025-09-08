FROM python:3.12-slim

# Системные зависимости
RUN apt-get update && \
    apt-get install -y build-essential libmariadb-dev curl tzdata && \
    rm -rf /var/lib/apt/lists/*

# Переменная окружения для временной зоны
ENV TZ=Europe/Moscow

# Рабочая директория
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Открываем порт
EXPOSE 8000

# Точка входа
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
