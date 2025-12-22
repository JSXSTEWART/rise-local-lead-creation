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
