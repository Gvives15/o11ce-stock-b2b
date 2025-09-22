-- PostgreSQL initialization script
-- This script runs when the database is first created

-- Create additional databases if needed
-- CREATE DATABASE bff_test;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance (will be created by Django migrations)
-- These are just examples, actual indexes should be created via Django migrations