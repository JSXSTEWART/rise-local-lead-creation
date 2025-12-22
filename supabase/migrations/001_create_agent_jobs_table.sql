-- Migration: Create agent_jobs table
-- Purpose: Track all agent-initiated jobs (discovery, enrichment, qualification, delivery)
-- Created: 2025-12-22

CREATE TABLE IF NOT EXISTS agent_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('discovery', 'enrichment', 'qualification', 'delivery', 'manual')),
    status VARCHAR(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    initiated_by VARCHAR(100), -- user_id, agent_name (e.g., 'zapier_discovery_coordinator', 'user@example.com')
    initiated_by_type VARCHAR(20) CHECK (initiated_by_type IN ('human', 'zapier_agent', 'claude_agent')),
    parameters JSONB, -- Job-specific parameters (e.g., {"metro_id": "austin", "radius": 15})
    results JSONB, -- Job outputs (e.g., {"leads_created": 47, "cost_cents": 235})
    error_message TEXT, -- Error details if status='failed'
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_agent_jobs_status_type ON agent_jobs(status, job_type);
CREATE INDEX idx_agent_jobs_created ON agent_jobs(created_at DESC);
CREATE INDEX idx_agent_jobs_initiated_by ON agent_jobs(initiated_by);
CREATE INDEX idx_agent_jobs_status ON agent_jobs(status) WHERE status IN ('queued', 'running');

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agent_jobs_updated_at BEFORE UPDATE ON agent_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE agent_jobs IS 'Tracks all agent-initiated jobs across the pipeline';
COMMENT ON COLUMN agent_jobs.job_type IS 'Type of job: discovery, enrichment, qualification, delivery, manual';
COMMENT ON COLUMN agent_jobs.status IS 'Current job status: queued, running, completed, failed, cancelled';
COMMENT ON COLUMN agent_jobs.initiated_by IS 'User ID or agent name that initiated the job';
COMMENT ON COLUMN agent_jobs.parameters IS 'JSON object with job-specific input parameters';
COMMENT ON COLUMN agent_jobs.results IS 'JSON object with job output data and metrics';
COMMENT ON COLUMN agent_jobs.retry_count IS 'Number of retry attempts (for failed jobs)';
