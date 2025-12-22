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
