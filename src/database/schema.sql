-- Schema for Sales Transactions
CREATE TABLE IF NOT EXISTS sales (
    transaction_id VARCHAR(20) PRIMARY KEY,
    order_date DATE NOT NULL,
    year_month VARCHAR(7) NOT NULL,
    product VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    sales_channel VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    discount_amount REAL NOT NULL DEFAULT 0.0 CHECK (discount_amount >= 0),
    gross_revenue REAL NOT NULL,
    net_revenue REAL NOT NULL,
    status VARCHAR(20) NOT NULL,
    is_imputed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sales_order_date ON sales(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_year_month ON sales(year_month);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product);
CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region);
CREATE INDEX IF NOT EXISTS idx_sales_category ON sales(category);
CREATE INDEX IF NOT EXISTS idx_sales_status ON sales(status);
