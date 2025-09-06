SET NAMES utf8mb4;

-- Переключаемся на нужную базу
CREATE DATABASE IF NOT EXISTS mydb
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE mydb;

-- Пересоздаём пользователя
DROP USER IF EXISTS 'myuser'@'%';
CREATE USER 'myuser'@'%' IDENTIFIED WITH caching_sha2_password BY 'mypassword';

-- Выдаём права
GRANT ALL PRIVILEGES ON mydb.* TO 'myuser'@'%';
FLUSH PRIVILEGES;

-- Создание таблицы типов (если ещё нет)
CREATE TABLE IF NOT EXISTS types (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Вставка стандартных типов посылок
-- Важно: файл SQL сохранён в UTF-8 без BOM!
INSERT INTO types (id, name) VALUES
    (1, 'одежда'),
    (2, 'электроника'),
    (3, 'разное')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Создание таблицы пакетов
CREATE TABLE IF NOT EXISTS packages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id CHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    weight_kg DECIMAL(10,3) NOT NULL,
    content_value_usd DECIMAL(10,3) NOT NULL,
    type_id INT NOT NULL,
    type_name VARCHAR(50) NOT NULL,
    delivery_cost_rub DECIMAL(10,2) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT packages_ibfk_1 FOREIGN KEY (type_id) REFERENCES types(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

