-- MySQL initialization script
-- Creates the database and grants permissions.
-- Tables are created by SQLAlchemy (db.create_all()), not here.

CREATE DATABASE IF NOT EXISTS cloud_scheduler
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'cloudscheduler'@'%'
    IDENTIFIED BY 'changeme_db_password';

GRANT ALL PRIVILEGES ON cloud_scheduler.* TO 'cloudscheduler'@'%';
FLUSH PRIVILEGES;
