CREATE DATABASE aipscan CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE celery CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'aipscan'@'%' IDENTIFIED WITH caching_sha2_password BY 'demo';
GRANT ALL PRIVILEGES ON aipscan.* TO 'aipscan'@'%';
GRANT ALL PRIVILEGES ON celery.*  TO 'aipscan'@'%';
