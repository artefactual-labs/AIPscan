CREATE DATABASE aipscan CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE celery CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL ON aipscan.* TO 'aipscan'@'%';
GRANT ALL ON celery.* TO 'aipscan'@'%';
