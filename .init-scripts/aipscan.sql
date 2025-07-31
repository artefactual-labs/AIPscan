CREATE DATABASE aipscan CHARACTER SET utf8 COLLATE utf8_unicode_ci;
CREATE DATABASE celery CHARACTER SET utf8 COLLATE utf8_unicode_ci;
GRANT ALL ON aipscan.* TO 'aipscan'@'%';
GRANT ALL ON celery.* TO 'aipscan'@'%';
