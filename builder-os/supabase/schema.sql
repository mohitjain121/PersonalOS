-- builder-os schema (table-prefixed per docs/adr/0001-personal-ai-os-philosophy.md)

create table builder_discoveries (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('hn', 'github', 'arxiv', 'blog', 'reddit', 'twitter', 'web', 'hermes', 'agent-reach')),
  title text not null,
  url text,
  summary text,
  relevance_note text not null,
  status text not null default 'new' check (status in ('new', 'reviewed', 'actioned', 'dismissed')),
  discovered_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create index builder_discoveries_status_idx on builder_discoveries (status);
create index builder_discoveries_discovered_at_idx on builder_discoveries (discovered_at desc);

-- Work Orders: the contract between Builder OS and implementation workers
-- (Claude Code today; `worker` stays a plain string, not a polymorphic type,
-- until a second real worker exists — see docs/adr/).
create table builder_work_orders (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  objective text not null,
  application text,
  work_type text not null check (work_type in ('feature', 'bug', 'research', 'refactor', 'architecture', 'documentation')),
  priority text not null default 'normal' check (priority in ('low', 'normal', 'high')),
  status text not null default 'draft' check (status in ('draft', 'queued', 'in_progress', 'needs_input', 'review', 'done', 'failed', 'rejected')),
  context text,
  architectural_constraints text,
  acceptance_criteria text not null,
  dependencies text,
  worker text not null default 'claude-code',
  worker_session_id text,
  result_summary text,
  commit_sha text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index builder_work_orders_status_idx on builder_work_orders (status);
create index builder_work_orders_created_at_idx on builder_work_orders (created_at desc);
