-- ============================================================
-- Migration: Add embedding column to fact_job_offer
-- Run this ONCE after the initial schema is created
-- ============================================================

-- Store embeddings as JSONB (384-element float array)
ALTER TABLE fact_job_offer
ADD COLUMN IF NOT EXISTS embedding JSONB;

-- Partial index: quickly find offers that still need embeddings
CREATE INDEX IF NOT EXISTS idx_fact_embedding_null
ON fact_job_offer (offer_id)
WHERE embedding IS NULL;

-- Verify the column was added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'fact_job_offer' AND column_name = 'embedding';
