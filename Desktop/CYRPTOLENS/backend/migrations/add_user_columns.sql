-- Migration: Add missing columns to users table
-- Date: 2025-11-29

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS country VARCHAR(100),
ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);

