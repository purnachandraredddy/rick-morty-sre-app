-- Initialize database for Rick and Morty application
-- This script is run when the PostgreSQL container starts

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE rickmorty'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rickmorty')\gexec

-- Connect to the database
\c rickmorty;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance (will be created by SQLAlchemy, but good to have as backup)
-- These will be created after the tables are created by the application

-- Grant permissions (if using different user)
-- GRANT ALL PRIVILEGES ON DATABASE rickmorty TO your_app_user;
