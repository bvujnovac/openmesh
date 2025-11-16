-- OpenMesh Database Initialization Script

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create indexes for better performance
-- (Additional indexes will be created by SQLAlchemy models)

-- Enable pg_trgm for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'OpenMesh database initialized successfully';
END $$;
