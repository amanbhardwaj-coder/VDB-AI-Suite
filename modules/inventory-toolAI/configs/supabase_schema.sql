create table if not exists public.inventory_ai_runs (
  run_id text primary key,
  saved_at timestamptz,
  file_name text,
  file_meta jsonb,
  inventory_type text,
  source_rows integer,
  source_columns integer,
  export_profile text,
  warnings jsonb,
  remote_paths jsonb,
  sync_status text,
  sync_errors jsonb
);

create table if not exists public.inventory_ai_learned_headers (
  accepted_header text primary key,
  setter text,
  variations jsonb,
  source_file text,
  updated_at timestamptz
);

alter table public.inventory_ai_runs enable row level security;
alter table public.inventory_ai_learned_headers enable row level security;

drop policy if exists "service role full access on inventory_ai_runs" on public.inventory_ai_runs;
create policy "service role full access on inventory_ai_runs"
on public.inventory_ai_runs
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "service role full access on inventory_ai_learned_headers" on public.inventory_ai_learned_headers;
create policy "service role full access on inventory_ai_learned_headers"
on public.inventory_ai_learned_headers
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
