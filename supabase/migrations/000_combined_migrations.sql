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
-- Migration: Create agent_decisions table
-- Purpose: Track all agent decisions (qualification, scoring, routing, email variants)
-- Created: 2025-12-22

CREATE TABLE IF NOT EXISTS agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL, -- Foreign key to leads table
    decision_type VARCHAR(50) NOT NULL CHECK (decision_type IN ('qualification', 'scoring', 'routing', 'email_variant', 'category_assignment')),
    agent_name VARCHAR(100) NOT NULL, -- e.g., 'claude_qualifier', 'zapier_router', 'llm_council'
    agent_type VARCHAR(20) NOT NULL CHECK (agent_type IN ('zapier_agent', 'claude_agent', 'council')),
    decision VARCHAR(50) NOT NULL, -- e.g., 'qualified', 'rejected', 'marginal', 'route_instantly'
    confidence DECIMAL(3,2) CHECK (confidence >= 0.00 AND confidence <= 1.00), -- 0.00 to 1.00
    reasoning TEXT, -- Human-readable explanation of decision
    metadata JSONB, -- Additional context (e.g., council votes, pain signals, A/B test variant)
    overridden_by VARCHAR(100), -- User ID who overrode this decision (null if not overridden)
    override_reason TEXT, -- Reason for override
    overridden_at TIMESTAMP WITH TIME ZONE, -- When override occurred
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_agent_decisions_lead_type ON agent_decisions(lead_id, decision_type);
CREATE INDEX idx_agent_decisions_agent ON agent_decisions(agent_name);
CREATE INDEX idx_agent_decisions_overridden ON agent_decisions(overridden_by) WHERE overridden_by IS NOT NULL;
CREATE INDEX idx_agent_decisions_created ON agent_decisions(created_at DESC);
CREATE INDEX idx_agent_decisions_lead_id ON agent_decisions(lead_id);

-- Foreign key constraint (assuming leads table exists)
-- ALTER TABLE agent_decisions ADD CONSTRAINT fk_agent_decisions_lead
--     FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE;

-- Comments
COMMENT ON TABLE agent_decisions IS 'Tracks all agent decisions with reasoning and override capability';
COMMENT ON COLUMN agent_decisions.decision_type IS 'Type of decision: qualification, scoring, routing, email_variant, category_assignment';
COMMENT ON COLUMN agent_decisions.agent_name IS 'Name of the agent that made the decision';
COMMENT ON COLUMN agent_decisions.decision IS 'The actual decision made (qualified, rejected, etc.)';
COMMENT ON COLUMN agent_decisions.confidence IS 'Confidence score from 0.00 to 1.00';
COMMENT ON COLUMN agent_decisions.reasoning IS 'Human-readable explanation for transparency';
COMMENT ON COLUMN agent_decisions.metadata IS 'JSON with additional context (council votes, pain signals, etc.)';
COMMENT ON COLUMN agent_decisions.overridden_by IS 'User who overrode the agent decision';
COMMENT ON COLUMN agent_decisions.override_reason IS 'Explanation for why decision was overridden';
-- Migration: Create audit_log table
-- Purpose: Comprehensive audit trail for compliance and debugging
-- Created: 2025-12-22

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    actor VARCHAR(100) NOT NULL, -- user_id, agent_name, 'system', 'anonymous'
    actor_type VARCHAR(20) NOT NULL CHECK (actor_type IN ('human', 'zapier_agent', 'claude_agent', 'system')),
    action VARCHAR(100) NOT NULL, -- e.g., 'discovery_started', 'lead_qualified', 'email_sent', 'user_login'
    resource_type VARCHAR(50), -- e.g., 'lead', 'job', 'config', 'user'
    resource_id VARCHAR(100), -- UUID or identifier of the resource
    metadata JSONB, -- Full context of the action (parameters, results, changes)
    ip_address INET, -- IP address of the actor (for humans)
    user_agent TEXT, -- User agent string (for humans)
    session_id VARCHAR(100), -- Session identifier for grouping related actions
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    -- Compliance fields
    data_classification VARCHAR(20) CHECK (data_classification IN ('public', 'internal', 'confidential', 'restricted')),
    compliance_tags TEXT[], -- e.g., ['gdpr', 'soc2', 'pii']
    retention_days INT DEFAULT 2555 -- 7 years for compliance (2555 days)
);

-- Indexes for performance (audit logs can get very large)
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_actor_type ON audit_log(actor_type);
CREATE INDEX idx_audit_log_severity ON audit_log(severity) WHERE severity IN ('error', 'critical');

-- Partitioning by month for large-scale deployments (optional, uncomment if needed)
-- CREATE TABLE audit_log_2025_12 PARTITION OF audit_log
--     FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Function to automatically delete old audit logs (compliance retention)
CREATE OR REPLACE FUNCTION delete_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_log
    WHERE timestamp < NOW() - INTERVAL '1 day' * retention_days;
END;
$$ LANGUAGE plpgsql;

-- Scheduled job to clean up old audit logs (run daily)
-- SELECT cron.schedule('delete-old-audit-logs', '0 2 * * *', 'SELECT delete_old_audit_logs();');

-- Comments
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all system actions (compliance, debugging, security)';
COMMENT ON COLUMN audit_log.actor IS 'User ID, agent name, or system identifier that performed the action';
COMMENT ON COLUMN audit_log.action IS 'Action performed (e.g., discovery_started, lead_qualified, email_sent)';
COMMENT ON COLUMN audit_log.resource_type IS 'Type of resource affected (lead, job, config, user)';
COMMENT ON COLUMN audit_log.resource_id IS 'UUID or identifier of the affected resource';
COMMENT ON COLUMN audit_log.metadata IS 'Full context JSON (parameters, results, before/after values)';
COMMENT ON COLUMN audit_log.severity IS 'Log severity: debug, info, warning, error, critical';
COMMENT ON COLUMN audit_log.compliance_tags IS 'Array of compliance tags (gdpr, soc2, pii, etc.)';
COMMENT ON COLUMN audit_log.retention_days IS 'Number of days to retain this log entry (default 7 years)';

-- Row-Level Security (RLS) - append-only for non-admins
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can insert audit logs
CREATE POLICY "Anyone can insert audit logs" ON audit_log
    FOR INSERT
    WITH CHECK (true);

-- Policy: Only admins can read audit logs
CREATE POLICY "Only admins can read audit logs" ON audit_log
    FOR SELECT
    USING (
        auth.jwt() ->> 'role' = 'admin' OR
        auth.jwt() ->> 'role' = 'service_role'
    );

-- Policy: No one can update or delete audit logs (immutable)
CREATE POLICY "Audit logs are immutable" ON audit_log
    FOR UPDATE
    USING (false);

CREATE POLICY "Audit logs cannot be deleted" ON audit_log
    FOR DELETE
    USING (false);
-- Migration: Create rate_limits table
-- Purpose: Track API rate limits for external services and agent quotas
-- Created: 2025-12-22

CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(50) NOT NULL, -- e.g., 'clay', 'apollo', 'instantly', 'agent:zapier_orchestrator'
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INT DEFAULT 0 NOT NULL,
    quota_limit INT NOT NULL, -- Maximum requests allowed in this window
    reset_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB, -- Additional info (e.g., cost per request, endpoint-specific limits)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(service_name, window_start)
);

-- Indexes for performance
CREATE INDEX idx_rate_limits_service_window ON rate_limits(service_name, window_start DESC);
CREATE INDEX idx_rate_limits_reset ON rate_limits(reset_at);
CREATE INDEX idx_rate_limits_service ON rate_limits(service_name);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_rate_limits_updated_at BEFORE UPDATE ON rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to check if rate limit is exceeded
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_service_name VARCHAR(50),
    p_quota_limit INT,
    p_window_minutes INT DEFAULT 60
)
RETURNS TABLE(allowed BOOLEAN, remaining INT, reset_at TIMESTAMP WITH TIME ZONE) AS $$
DECLARE
    v_window_start TIMESTAMP WITH TIME ZONE;
    v_reset_at TIMESTAMP WITH TIME ZONE;
    v_current_count INT;
BEGIN
    -- Calculate window start (rounded to window_minutes)
    v_window_start := date_trunc('hour', NOW()) +
                      (FLOOR(EXTRACT(MINUTE FROM NOW()) / p_window_minutes) * p_window_minutes || ' minutes')::INTERVAL;
    v_reset_at := v_window_start + (p_window_minutes || ' minutes')::INTERVAL;

    -- Get or create rate limit record
    INSERT INTO rate_limits (service_name, window_start, request_count, quota_limit, reset_at)
    VALUES (p_service_name, v_window_start, 0, p_quota_limit, v_reset_at)
    ON CONFLICT (service_name, window_start)
    DO NOTHING;

    -- Get current count
    SELECT rl.request_count INTO v_current_count
    FROM rate_limits rl
    WHERE rl.service_name = p_service_name
      AND rl.window_start = v_window_start;

    -- Check if limit exceeded
    IF v_current_count < p_quota_limit THEN
        -- Increment counter
        UPDATE rate_limits
        SET request_count = request_count + 1
        WHERE service_name = p_service_name
          AND window_start = v_window_start;

        RETURN QUERY SELECT TRUE, (p_quota_limit - v_current_count - 1)::INT, v_reset_at;
    ELSE
        RETURN QUERY SELECT FALSE, 0::INT, v_reset_at;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to increment rate limit counter (for manual tracking)
CREATE OR REPLACE FUNCTION increment_rate_limit(
    p_service_name VARCHAR(50),
    p_quota_limit INT,
    p_window_minutes INT DEFAULT 60,
    p_increment INT DEFAULT 1
)
RETURNS BOOLEAN AS $$
DECLARE
    v_window_start TIMESTAMP WITH TIME ZONE;
    v_reset_at TIMESTAMP WITH TIME ZONE;
    v_current_count INT;
BEGIN
    v_window_start := date_trunc('hour', NOW()) +
                      (FLOOR(EXTRACT(MINUTE FROM NOW()) / p_window_minutes) * p_window_minutes || ' minutes')::INTERVAL;
    v_reset_at := v_window_start + (p_window_minutes || ' minutes')::INTERVAL;

    -- Upsert rate limit record
    INSERT INTO rate_limits (service_name, window_start, request_count, quota_limit, reset_at)
    VALUES (p_service_name, v_window_start, p_increment, p_quota_limit, v_reset_at)
    ON CONFLICT (service_name, window_start)
    DO UPDATE SET
        request_count = rate_limits.request_count + p_increment,
        updated_at = NOW();

    -- Check if limit exceeded
    SELECT request_count INTO v_current_count
    FROM rate_limits
    WHERE service_name = p_service_name
      AND window_start = v_window_start;

    RETURN v_current_count <= p_quota_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to reset rate limit (for testing or manual intervention)
CREATE OR REPLACE FUNCTION reset_rate_limit(p_service_name VARCHAR(50))
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limits WHERE service_name = p_service_name;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old rate limit records
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limits WHERE reset_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE rate_limits IS 'Tracks API rate limits for external services and agent quotas';
COMMENT ON COLUMN rate_limits.service_name IS 'Service or agent identifier (e.g., clay, apollo, agent:zapier_orchestrator)';
COMMENT ON COLUMN rate_limits.window_start IS 'Start of the rate limit window (aligned to window_minutes)';
COMMENT ON COLUMN rate_limits.request_count IS 'Number of requests made in this window';
COMMENT ON COLUMN rate_limits.quota_limit IS 'Maximum requests allowed in this window';
COMMENT ON COLUMN rate_limits.reset_at IS 'When the rate limit window resets';
COMMENT ON COLUMN rate_limits.metadata IS 'Additional metadata (cost per request, endpoint-specific limits)';

-- Example rate limit configurations (insert after table creation)
INSERT INTO rate_limits (service_name, window_start, request_count, quota_limit, reset_at, metadata) VALUES
    ('clay', date_trunc('hour', NOW()), 0, 1000, date_trunc('hour', NOW()) + INTERVAL '1 hour', '{"cost_per_request": 0.01, "plan": "professional"}'),
    ('apollo', date_trunc('hour', NOW()), 0, 100, date_trunc('hour', NOW()) + INTERVAL '1 hour', '{"cost_per_request": 0.05}'),
    ('instantly', date_trunc('hour', NOW()), 0, 500, date_trunc('hour', NOW()) + INTERVAL '1 hour', '{"cost_per_request": 0.001}'),
    ('agent:zapier_orchestrator', date_trunc('hour', NOW()), 0, 100, date_trunc('hour', NOW()) + INTERVAL '1 hour', '{"max_per_minute": 100}'),
    ('agent:claude_qualifier', date_trunc('hour', NOW()), 0, 50, date_trunc('hour', NOW()) + INTERVAL '1 hour', '{"max_per_minute": 50}')
ON CONFLICT (service_name, window_start) DO NOTHING;
