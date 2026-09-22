-- Source database schema (workorders_source)
-- Normalized 3NF model for the cleaned Excel data

DROP TABLE IF EXISTS open_work_order CASCADE;
DROP TABLE IF EXISTS region CASCADE;
DROP TABLE IF EXISTS work_category CASCADE;
DROP TABLE IF EXISTS order_status CASCADE;

-- one row per city, region_code is the natural key from the Excel file
CREATE TABLE region (
    region_id    SERIAL       PRIMARY KEY,
    region_code  INTEGER      NOT NULL UNIQUE,
    region_name  VARCHAR(100) NOT NULL
);

-- work order categories (operation, repairs, cabling, ...)
CREATE TABLE work_category (
    category_id    SERIAL       PRIMARY KEY,
    category_name  VARCHAR(150) NOT NULL UNIQUE,
    category_order SMALLINT     NOT NULL
);

-- progress statuses of a work order
CREATE TABLE order_status (
    status_id    SERIAL       PRIMARY KEY,
    status_name  VARCHAR(100) NOT NULL UNIQUE,
    status_order SMALLINT     NOT NULL
);

-- main fact table in long format:
-- one row per city x month x category x status
CREATE TABLE open_work_order (
    id           BIGSERIAL   PRIMARY KEY,
    region_id    INTEGER     NOT NULL REFERENCES region(region_id),
    jalali_year  SMALLINT    NOT NULL CHECK (jalali_year BETWEEN 1300 AND 1500),
    jalali_month SMALLINT    NOT NULL CHECK (jalali_month BETWEEN 1 AND 12),
    category_id  INTEGER     NOT NULL REFERENCES work_category(category_id),
    status_id    INTEGER     NOT NULL REFERENCES order_status(status_id),
    order_count  INTEGER     NOT NULL CHECK (order_count >= 0),
    source_row   INTEGER,
    loaded_at    TIMESTAMP   NOT NULL DEFAULT now(),
    CONSTRAINT uq_owo UNIQUE (region_id, jalali_year, jalali_month, category_id, status_id)
);

CREATE INDEX idx_owo_period ON open_work_order (jalali_year, jalali_month);
CREATE INDEX idx_owo_region ON open_work_order (region_id);