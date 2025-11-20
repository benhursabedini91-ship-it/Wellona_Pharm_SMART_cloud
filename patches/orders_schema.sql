CREATE SCHEMA IF NOT EXISTS app;

-- Header i porosisë
CREATE TABLE IF NOT EXISTS app.orders (
  id            bigserial PRIMARY KEY,
  supplier      text        NOT NULL,        -- p.sh. 'phoenix', 'sopharma', ...
  status        text        NOT NULL,        -- 'draft' | 'approved' | 'sent'
  target_days   int         NOT NULL,
  sales_window  int         NOT NULL,        -- 7 | 30 | 180
  approved_by   text,
  approved_at   timestamptz,
  created_by    text        NOT NULL DEFAULT 'system',
  created_at    timestamptz NOT NULL DEFAULT now(),
  note          text
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON app.orders(status);

-- Rreshtat e porosisë
CREATE TABLE IF NOT EXISTS app.order_items (
  id          bigserial PRIMARY KEY,
  order_id    bigint      NOT NULL REFERENCES app.orders(id) ON DELETE CASCADE,
  sifra       text        NOT NULL,
  barkod      text,
  naziv       text,
  avg_daily   numeric,
  current_stock numeric,
  minzaliha   numeric,
  pakovanje   numeric,
  qty         numeric     NOT NULL,
  unit_cost   numeric,
  line_total  numeric
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON app.order_items(order_id);

-- Constraint-e të thjeshta
ALTER TABLE app.orders
  ADD CONSTRAINT chk_orders_sales_window CHECK (sales_window IN (7,30,180))
  , ADD CONSTRAINT chk_orders_status      CHECK (status IN ('draft','approved','sent'));
