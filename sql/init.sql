create table if not exists news_raw (
  id bigserial primary key,
  source text not null,
  ticker text,
  published_at timestamptz,
  title text,
  url text unique,
  content text,
  ingested_at timestamptz default now()
);

create table if not exists news_features (
  id bigserial primary key,
  url text unique,
  ticker text,
  event_type text,
  sentiment double precision,
  urgency double precision,
  relevance double precision,
  risk_flag boolean,
  trade_bias text,
  confidence double precision,
  rationale text,
  extracted_at timestamptz default now()
);

create table if not exists trade_intents (
  id bigserial primary key,
  ts timestamptz default now(),
  ticker text not null,
  side text not null,
  tv_price double precision,
  tv_score double precision,
  tv_atr double precision,
  tv_stop double precision,
  tv_takeprofit double precision,
  decision text not null,
  decision_reason text
);

create table if not exists executions (
  id bigserial primary key,
  ts timestamptz default now(),
  ticker text not null,
  alpaca_order_id text,
  status text,
  qty double precision,
  notional double precision,
  submitted_price double precision,
  raw_response jsonb
);
