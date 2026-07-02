-- =============================================================
-- venture-studio: Supabase Schema
-- Designed for Sprint 1 usage, Sprint 2–4 structure built-in
-- =============================================================

-- ─────────────────────────────────────────
-- SPRINT 1: Core capture + research
-- ─────────────────────────────────────────

CREATE TABLE ideas (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_text     TEXT NOT NULL,                          -- verbatim from Telegram
  title        TEXT,                                   -- extracted by Hermes
  domain       TEXT,                                   -- 'fintech', 'saas', 'marketplace', etc.
  source       TEXT DEFAULT 'telegram',
  status       TEXT DEFAULT 'raw' CHECK (status IN (
                 'raw',           -- just captured
                 'researching',   -- Hermes is running research
                 'validated',     -- report generated
                 'experimenting', -- Sprint 2+: you're actively testing
                 'paused',        -- shelved, not killed
                 'killed'         -- consciously abandoned
               )),
  verdict      TEXT CHECK (verdict IN ('strong', 'promising', 'weak', 'dead', NULL)),
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE research_runs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  status       TEXT DEFAULT 'running' CHECK (status IN ('running', 'complete', 'failed')),
  web_results  JSONB,       -- raw search output per subagent
  synthesis    TEXT,        -- full markdown report
  pdf_path     TEXT,        -- local path to generated PDF (null until created)
  sprint_level INTEGER DEFAULT 1,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- SPRINT 2: Rich structured evidence
-- ─────────────────────────────────────────

CREATE TABLE evidence (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  type         TEXT CHECK (type IN (
                 'market', 'competitor', 'forum',
                 'news', 'regulatory', 'technical', 'user_pain'
               )),
  content      TEXT,
  source_url   TEXT,
  sentiment    TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral')),
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE competitors (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  url          TEXT,
  description  TEXT,
  funding      TEXT,         -- 'bootstrapped', '$2M seed', 'Series B', etc.
  stage        TEXT CHECK (stage IN ('idea', 'early', 'growth', 'mature', 'dead')),
  geo_focus    TEXT,         -- 'India', 'Global', 'US', etc.
  threat_level TEXT CHECK (threat_level IN ('low', 'medium', 'high', 'direct')),
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE experiments (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  hypothesis   TEXT,
  method       TEXT,         -- 'landing page', 'cold outreach', 'prototype', etc.
  status       TEXT CHECK (status IN ('proposed', 'active', 'complete', 'abandoned')),
  outcome      TEXT,
  learnings    TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- SPRINT 3: Cross-idea reasoning + monitoring
-- ─────────────────────────────────────────

CREATE TABLE idea_relations (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_a_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  idea_b_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  relation_type  TEXT CHECK (relation_type IN ('similar', 'complement', 'conflict', 'pivot')),
  similarity_score FLOAT CHECK (similarity_score BETWEEN 0 AND 1),
  notes          TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(idea_a_id, idea_b_id),
  CHECK (idea_a_id <> idea_b_id)
);

CREATE TABLE market_signals (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id       UUID REFERENCES ideas(id) ON DELETE CASCADE,
  signal_text   TEXT NOT NULL,
  source        TEXT,
  significance  TEXT CHECK (significance IN ('low', 'medium', 'high')),
  alerted       BOOLEAN DEFAULT FALSE,   -- whether digest has surfaced this
  detected_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Your ratings per idea — this is the feedback signal for Sprint 3 personalization
CREATE TABLE idea_ratings (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id    UUID REFERENCES ideas(id) ON DELETE CASCADE,
  dimension  TEXT CHECK (dimension IN (
               'market_size',      -- how big is the opportunity
               'problem_severity', -- how painful is this for users
               'founder_fit',      -- your personal edge here
               'timing',           -- right moment in the market
               'competition'       -- how crowded (inverted: 5 = clear space)
             )),
  score      INTEGER CHECK (score BETWEEN 1 AND 5),
  notes      TEXT,
  rated_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(idea_id, dimension)    -- one score per dimension per idea
);

-- ─────────────────────────────────────────
-- SPRINT 4: Multi-agent contributions
-- ─────────────────────────────────────────

CREATE TABLE agent_contributions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id      UUID REFERENCES ideas(id) ON DELETE CASCADE,
  run_id       UUID REFERENCES research_runs(id) ON DELETE CASCADE,
  agent_type   TEXT CHECK (agent_type IN (
                 'researcher',
                 'devil_advocate',
                 'business_model',
                 'tech_feasibility',
                 'gtm',
                 'experiment_designer'
               )),
  output       TEXT,
  confidence   FLOAT CHECK (confidence BETWEEN 0 AND 1),
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE synthesis_reports (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id       UUID REFERENCES ideas(id) ON DELETE CASCADE,
  run_id        UUID REFERENCES research_runs(id) ON DELETE CASCADE,
  final_verdict TEXT CHECK (final_verdict IN ('strong', 'promising', 'weak', 'dead')),
  summary       TEXT,           -- 3-sentence TL;DR for Telegram
  report_md     TEXT,           -- full markdown report
  report_json   JSONB,          -- structured data for Sprint 4 reasoning
  sprint_level  INTEGER DEFAULT 1,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────

CREATE INDEX idx_ideas_status         ON ideas(status);
CREATE INDEX idx_ideas_domain         ON ideas(domain);
CREATE INDEX idx_ideas_verdict        ON ideas(verdict);
CREATE INDEX idx_research_idea        ON research_runs(idea_id);
CREATE INDEX idx_evidence_idea        ON evidence(idea_id);
CREATE INDEX idx_competitors_idea     ON competitors(idea_id);
CREATE INDEX idx_market_signals_idea  ON market_signals(idea_id);
CREATE INDEX idx_market_signals_alert ON market_signals(alerted) WHERE alerted = FALSE;
CREATE INDEX idx_ratings_idea         ON idea_ratings(idea_id);
CREATE INDEX idx_agent_contrib_idea   ON agent_contributions(idea_id);
CREATE INDEX idx_agent_contrib_type   ON agent_contributions(agent_type);

-- Full-text search across idea corpus (Sprint 2 search)
CREATE INDEX idx_ideas_fts ON ideas
  USING gin(to_tsvector('english', coalesce(title, '') || ' ' || raw_text));

-- ─────────────────────────────────────────
-- TRIGGERS
-- ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ideas_updated_at
  BEFORE UPDATE ON ideas
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────
-- VIEWS (useful from Sprint 2 onwards)
-- ─────────────────────────────────────────

-- Active ideas with their latest research run
CREATE VIEW active_ideas AS
SELECT
  i.id,
  i.title,
  i.domain,
  i.status,
  i.verdict,
  i.created_at,
  r.pdf_path,
  r.created_at AS last_researched_at,
  (SELECT COUNT(*) FROM competitors c WHERE c.idea_id = i.id) AS competitor_count,
  (SELECT AVG(score) FROM idea_ratings ir WHERE ir.idea_id = i.id) AS avg_rating
FROM ideas i
LEFT JOIN LATERAL (
  SELECT * FROM research_runs WHERE idea_id = i.id ORDER BY created_at DESC LIMIT 1
) r ON TRUE
WHERE i.status NOT IN ('killed')
ORDER BY i.created_at DESC;

-- Weekly digest source: unacted validated ideas ranked by avg rating
CREATE VIEW digest_candidates AS
SELECT
  i.id,
  i.title,
  i.domain,
  i.status,
  i.verdict,
  i.created_at,
  r.pdf_path,
  COALESCE(AVG(ir.score), 0) AS avg_rating,
  COUNT(DISTINCT c.id) AS competitor_count,
  COUNT(DISTINCT ms.id) AS new_signals
FROM ideas i
LEFT JOIN research_runs r ON r.idea_id = i.id
LEFT JOIN idea_ratings ir ON ir.idea_id = i.id
LEFT JOIN competitors c ON c.idea_id = i.id
LEFT JOIN market_signals ms ON ms.idea_id = i.id AND ms.alerted = FALSE
WHERE i.status IN ('validated', 'paused')
  AND i.verdict IN ('strong', 'promising')
GROUP BY i.id, i.title, i.domain, i.status, i.verdict, i.created_at, r.pdf_path
ORDER BY avg_rating DESC, new_signals DESC;
