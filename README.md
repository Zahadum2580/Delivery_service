# 📦 Delivery Service

Сервис для обработки и доставки заказов. Поддерживает асинхронное взаимодействие с БД, очередями и кэшем.

## ✨ Возможности
- 📦 Отправка и обработка посылок через **RabbitMQ**
- 🗄️ Хранение данных в **PostgreSQL** и **MongoDB**
- ⚡ Быстрый доступ к данным через **Redis**
- 🌐 REST API на **FastAPI**
- 📊 Метрики и статистика доставки

## 🚀 Стек технологий
- **Python 3.12**
- **FastAPI**
- **SQLAlchemy**
- **PostgreSQL**
- **MongoDB (Motor)**
- **Redis (asyncio)**
- **RabbitMQ (aio-pika)**
- **Docker + docker-compose**
- **pre-commit hooks** (black, isort, flake8, mypy)

## ⚙️ Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/Zahadum2580/delivery_service.git
cd delivery_service
```

### 2. Создание виртуального окружения
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка окружения
Создайте файл .env на основе .env.example:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=delivery
POSTGRES_HOST=postgres
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=admin
REDIS_HOST=redis
MONGO_URL=mongodb://mongo:27017
TZ=Europe/Moscow
```

### 5. Запуск в Docker
```bash
docker-compose up --build
```

### 🧹 Линтеры и проверки
```bash
pre-commit run --all-files
```

### 📜 Лицензия
MIT License.
