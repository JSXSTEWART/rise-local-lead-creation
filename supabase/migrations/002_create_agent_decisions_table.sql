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
