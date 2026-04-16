-- =============================================================================
-- NorthStar Bank — Complete Seed Data for Smart Banking Assistant
-- Capstone Project Level 2 (BFSI-ARAG-002)
-- Database: agentic_rag_db (shared with e-commerce schema)
-- PostgreSQL 16+
--
-- Run as a PostgreSQL superuser:
--   psql -U postgres -d agentic_rag_db -f northstar_bank_seed.sql
--
-- NOTE: This script assumes agentic_rag_db already exists (created by seed.sql).
--       Connect to it before running, or use \c agentic_rag_db at the top.
-- =============================================================================

\
-- ─────────────────────────────────────────────────────────────
-- 0. EXTENSIONS
-- ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────
-- 1. SCHEMA
-- ─────────────────────────────────────────────────────────────

-- 1.1 Accounts
CREATE TABLE IF NOT EXISTS accounts (
    account_id      VARCHAR(20)   PRIMARY KEY,
    customer_name   VARCHAR(100)  NOT NULL,
    account_type    VARCHAR(20)   NOT NULL CHECK (account_type IN ('savings','current','salary')),
    branch_code     VARCHAR(10)   NOT NULL,
    ifsc_code       VARCHAR(15),
    mobile          VARCHAR(15),   -- stored masked: e.g. XXXXXXX890
    email           VARCHAR(100),
    kyc_status      VARCHAR(20)   DEFAULT 'verified',
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- 1.2 Transaction History
CREATE TABLE IF NOT EXISTS transactions (
    txn_id          UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id      VARCHAR(20)   REFERENCES accounts(account_id),
    txn_date        DATE          NOT NULL,
    txn_type        VARCHAR(10)   NOT NULL CHECK (txn_type IN ('debit','credit')),
    amount          NUMERIC(15,2) NOT NULL,
    balance_after   NUMERIC(15,2),
    description     VARCHAR(200),
    channel         VARCHAR(20)   CHECK (channel IN ('ATM','UPI','NEFT','RTGS','IMPS','branch','online','POS')),
    merchant_name   VARCHAR(100),
    category        VARCHAR(50),
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- 1.3 Loan Accounts
CREATE TABLE IF NOT EXISTS loan_accounts (
    loan_id         VARCHAR(20)   PRIMARY KEY,
    account_id      VARCHAR(20)   REFERENCES accounts(account_id),
    loan_type       VARCHAR(30)   NOT NULL CHECK (loan_type IN ('home_loan','personal_loan','auto_loan','gold_loan')),
    principal       NUMERIC(15,2) NOT NULL,
    outstanding     NUMERIC(15,2) NOT NULL,
    disbursed_date  DATE,
    emi_amount      NUMERIC(15,2),
    next_emi_date   DATE,
    interest_rate   NUMERIC(5,2),
    tenure_months   INT,
    emi_paid        INT           DEFAULT 0,
    status          VARCHAR(20)   DEFAULT 'active',
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- 1.4 Fixed Deposits
CREATE TABLE IF NOT EXISTS fixed_deposits (
    fd_id           VARCHAR(20)   PRIMARY KEY,
    account_id      VARCHAR(20)   REFERENCES accounts(account_id),
    principal       NUMERIC(15,2) NOT NULL,
    interest_rate   NUMERIC(5,2)  NOT NULL,
    tenure_days     INT           NOT NULL,
    start_date      DATE          NOT NULL,
    maturity_date   DATE          NOT NULL,
    maturity_amount NUMERIC(15,2),
    interest_payout VARCHAR(20)   DEFAULT 'at_maturity',
    status          VARCHAR(20)   DEFAULT 'active',
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- 1.5 Credit Cards
CREATE TABLE IF NOT EXISTS credit_cards (
    card_id         VARCHAR(20)   PRIMARY KEY,
    account_id      VARCHAR(20)   REFERENCES accounts(account_id),
    card_variant    VARCHAR(30),
    credit_limit    NUMERIC(15,2),
    available_limit NUMERIC(15,2),
    outstanding_amt NUMERIC(15,2) DEFAULT 0,
    due_date        DATE,
    min_due         NUMERIC(15,2) DEFAULT 0,
    status          VARCHAR(20)   DEFAULT 'active',
    issued_date     DATE,
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- 1.6 Credit Card Transactions
CREATE TABLE IF NOT EXISTS card_transactions (
    txn_id           UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_id          VARCHAR(20)   REFERENCES credit_cards(card_id),
    txn_date         DATE          NOT NULL,
    txn_type         VARCHAR(20)   CHECK (txn_type IN ('purchase','cashadvance','payment','refund','fee')),
    amount           NUMERIC(15,2) NOT NULL,
    merchant_name    VARCHAR(100),
    category         VARCHAR(50),
    is_international BOOLEAN       DEFAULT FALSE,
    currency         VARCHAR(5)    DEFAULT 'INR',
    created_at       TIMESTAMP     DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 2. SEED DATA — ACCOUNTS (8 rows)
-- ─────────────────────────────────────────────────────────────
INSERT INTO accounts (account_id, customer_name, account_type, branch_code, ifsc_code, mobile, email, kyc_status, created_at) VALUES
('1345367', 'James Mitchell',     'savings', 'CHN001', 'NSBK0CHN001', 'XXXXXXX890', 'james.mitchell@email.com',     'verified', '2019-03-15 10:00:00'),
('2456789', 'Sarah Thompson',     'salary',  'MUM002', 'NSBK0MUM002', 'XXXXXXX123', 'sarah.thompson@email.com',     'verified', '2020-07-22 11:30:00'),
('3567890', 'Robert Clarke',      'current', 'DEL003', 'NSBK0DEL003', 'XXXXXXX456', 'robert.clarke@bizmail.com',    'verified', '2018-11-05 09:15:00'),
('4678901', 'Emily Watson',       'savings', 'HYD004', 'NSBK0HYD004', 'XXXXXXX789', 'emily.watson@email.com',       'verified', '2021-02-18 14:45:00'),
('5789012', 'Daniel Foster',      'salary',  'BLR005', 'NSBK0BLR005', 'XXXXXXX321', 'daniel.foster@email.com',      'verified', '2022-06-01 08:00:00'),
('6890123', 'Laura Bennett',      'savings', 'CHN001', 'NSBK0CHN001', 'XXXXXXX654', 'laura.bennett@email.com',      'verified', '2020-09-30 16:20:00'),
('7901234', 'Michael Harrington', 'current', 'DEL003', 'NSBK0DEL003', 'XXXXXXX987', 'michael.harrington@corp.com',  'verified', '2017-04-10 11:00:00'),
('8012345', 'Catherine Ellis',    'savings', 'BLR005', 'NSBK0BLR005', 'XXXXXXX147', 'catherine.ellis@email.com',    'verified', '2023-01-14 09:30:00');

-- ─────────────────────────────────────────────────────────────
-- 3. SEED DATA — TRANSACTIONS
-- ─────────────────────────────────────────────────────────────

-- ── Account 1345367 — James Mitchell (primary sample account, last ~4 months) ──

INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES

-- ── January 2026 ──
('1345367', '2026-01-03', 'credit', 85000.00, 185000.00, 'Salary Credit - January 2026',        'NEFT',   'Apex Solutions Inc',  'salary'),
('1345367', '2026-01-05', 'debit',  15000.00, 170000.00, 'Home Loan EMI - January',             'NEFT',   'NorthStar Bank',      'loan_emi'),
('1345367', '2026-01-07', 'debit',   4500.00, 165500.00, 'BigBasket Online Grocery',            'UPI',    'BigBasket',           'groceries'),
('1345367', '2026-01-10', 'debit',   2200.00, 163300.00, 'Swiggy Food Order',                   'UPI',    'Swiggy',              'food_dining'),
('1345367', '2026-01-12', 'debit',  12000.00, 151300.00, 'Amazon Shopping',                     'online', 'Amazon India',        'shopping'),
('1345367', '2026-01-15', 'debit',   3500.00, 147800.00, 'BESCOM Electricity Bill',             'online', 'BESCOM',              'utilities'),
('1345367', '2026-01-18', 'debit',   8000.00, 139800.00, 'Tata Motors Service Center',          'POS',    'Tata Service',        'automobile'),
('1345367', '2026-01-20', 'credit',  5000.00, 144800.00, 'UPI Transfer Received - Kevin Walsh', 'UPI',    NULL,                  'transfer'),
('1345367', '2026-01-22', 'debit',   1800.00, 143000.00, 'Netflix Subscription',               'online', 'Netflix',             'entertainment'),
('1345367', '2026-01-25', 'debit',  25000.00, 118000.00, 'HDFC Life Insurance Premium',         'NEFT',   'HDFC Life',           'insurance'),
('1345367', '2026-01-28', 'debit',   6700.00, 111300.00, 'Apollo Pharmacy',                     'UPI',    'Apollo Pharmacy',     'medical'),
('1345367', '2026-01-31', 'debit',   3200.00, 108100.00, 'Airtel Postpaid Bill',                'online', 'Airtel',              'utilities'),

-- ── February 2026 ──
('1345367', '2026-02-03', 'credit', 85000.00, 193100.00, 'Salary Credit - February 2026',       'NEFT',   'Apex Solutions Inc',  'salary'),
('1345367', '2026-02-05', 'debit',  15000.00, 178100.00, 'Home Loan EMI - February',            'NEFT',   'NorthStar Bank',      'loan_emi'),
('1345367', '2026-02-08', 'debit',   5200.00, 172900.00, 'Reliance Smart Grocery',              'POS',    'Reliance Smart',      'groceries'),
('1345367', '2026-02-10', 'debit',  18500.00, 154400.00, 'Croma Electronics - Headphones',      'POS',    'Croma',               'electronics'),
('1345367', '2026-02-14', 'debit',   3800.00, 150600.00, 'Zomato Valentine Dinner',             'UPI',    'Zomato',              'food_dining'),
('1345367', '2026-02-15', 'debit',   2800.00, 147800.00, 'BWSSB Water Bill',                    'online', 'BWSSB',               'utilities'),
('1345367', '2026-02-18', 'debit',  55000.00,  92800.00, 'NEFT to James FD Account',            'NEFT',   NULL,                  'transfer'),
('1345367', '2026-02-20', 'debit',   4100.00,  88700.00, 'Ola Cabs Monthly Pass',               'UPI',    'Ola',                 'transport'),
('1345367', '2026-02-22', 'debit',   9800.00,  78900.00, 'Decathlon Sports Equipment',          'POS',    'Decathlon',           'shopping'),
('1345367', '2026-02-25', 'debit',   1200.00,  77700.00, 'Hotstar Annual Subscription',         'online', 'Disney+ Hotstar',     'entertainment'),
('1345367', '2026-02-28', 'debit',   7500.00,  70200.00, 'Dr. Rajan Clinic Consultation',       'UPI',    'Apollo Clinic',       'medical'),

-- ── March 2026 ──
('1345367', '2026-03-03', 'credit', 85000.00, 155200.00, 'Salary Credit - March 2026',          'NEFT',   'Apex Solutions Inc',  'salary'),
('1345367', '2026-03-05', 'debit',  15000.00, 140200.00, 'Home Loan EMI - March',               'NEFT',   'NorthStar Bank',      'loan_emi'),
('1345367', '2026-03-07', 'debit',   6300.00, 133900.00, 'More Supermarket',                    'POS',    'More Supermarket',    'groceries'),
('1345367', '2026-03-10', 'debit',  32000.00, 101900.00, 'Flight Booking - IndiGo',             'online', 'IndiGo Airlines',     'travel'),
('1345367', '2026-03-12', 'debit',  15000.00,  86900.00, 'MakeMyTrip Hotel Booking',            'online', 'MakeMyTrip',          'travel'),
('1345367', '2026-03-15', 'debit',   3500.00,  83400.00, 'BESCOM Electricity Bill',             'online', 'BESCOM',              'utilities'),
('1345367', '2026-03-17', 'debit',   2500.00,  80900.00, 'Swiggy Food Delivery',                'UPI',    'Swiggy',              'food_dining'),
('1345367', '2026-03-19', 'debit',  75000.00,   5900.00, 'NEFT - Advance Tax Q4',               'NEFT',   'Income Tax Dept',     'tax'),
('1345367', '2026-03-20', 'credit', 75000.00,  80900.00, 'UPI Transfer Received - Bonus',       'UPI',    NULL,                  'transfer'),
('1345367', '2026-03-22', 'debit',   4800.00,  76100.00, 'Nykaa Shopping',                      'online', 'Nykaa',               'shopping'),
('1345367', '2026-03-25', 'debit',  12000.00,  64100.00, 'LIC Premium Payment',                 'online', 'LIC India',           'insurance'),
('1345367', '2026-03-28', 'debit',   3300.00,  60800.00, 'Airtel Postpaid Bill',                'online', 'Airtel',              'utilities'),
('1345367', '2026-03-31', 'debit',   8500.00,  52300.00, 'D-Mart Shopping',                     'POS',    'D-Mart',              'groceries'),

-- ── April 2026 (up to Apr 15) ──
('1345367', '2026-04-01', 'credit', 85000.00, 137300.00, 'Salary Credit - April 2026',          'NEFT',   'Apex Solutions Inc',  'salary'),
('1345367', '2026-04-05', 'debit',  15000.00, 122300.00, 'Home Loan EMI - April',               'NEFT',   'NorthStar Bank',      'loan_emi'),
('1345367', '2026-04-07', 'debit',   5500.00, 116800.00, 'BigBasket Online Grocery',            'UPI',    'BigBasket',           'groceries'),
('1345367', '2026-04-10', 'debit',   3100.00, 113700.00, 'Zomato Order',                        'UPI',    'Zomato',              'food_dining');

-- ── Account 2456789 — Sarah Thompson ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('2456789', '2026-01-01', 'credit', 120000.00, 130000.00, 'Salary Credit January 2026',          'NEFT',   'GlobalTech Corp',     'salary'),
('2456789', '2026-01-05', 'debit',   22000.00, 108000.00, 'Home Loan EMI - January',             'NEFT',   'NorthStar Bank',      'loan_emi'),
('2456789', '2026-01-08', 'debit',    6200.00, 101800.00, 'BigBasket Grocery',                   'UPI',    'BigBasket',           'groceries'),
('2456789', '2026-01-15', 'debit',    9800.00,  92000.00, 'Myntra Fashion',                      'online', 'Myntra',              'shopping'),
('2456789', '2026-01-20', 'debit',    3200.00,  88800.00, 'Swiggy Instamart',                    'UPI',    'Swiggy',              'food_dining'),
('2456789', '2026-02-01', 'credit', 120000.00, 208800.00, 'Salary Credit February 2026',         'NEFT',   'GlobalTech Corp',     'salary'),
('2456789', '2026-02-05', 'debit',   22000.00, 186800.00, 'Home Loan EMI - February',            'NEFT',   'NorthStar Bank',      'loan_emi'),
('2456789', '2026-02-12', 'debit',   15000.00, 171800.00, 'Apple iPhone Accessories',            'online', 'Apple India',         'electronics'),
('2456789', '2026-02-18', 'debit',    5500.00, 166300.00, 'Restaurant Dining',                   'POS',    'The Fatty Bao',       'food_dining'),
('2456789', '2026-03-01', 'credit', 120000.00, 286300.00, 'Salary Credit March 2026',            'NEFT',   'GlobalTech Corp',     'salary'),
('2456789', '2026-03-05', 'debit',   22000.00, 264300.00, 'Home Loan EMI - March',               'NEFT',   'NorthStar Bank',      'loan_emi'),
('2456789', '2026-03-10', 'debit',    8500.00, 255800.00, 'Amazon Shopping',                     'online', 'Amazon India',        'shopping'),
('2456789', '2026-03-15', 'debit',    4200.00, 251600.00, 'Grocery - Spencer''s',                'POS',    'Spencer''s Retail',   'groceries'),
('2456789', '2026-04-01', 'credit', 120000.00, 371600.00, 'Salary Credit April 2026',            'NEFT',   'GlobalTech Corp',     'salary'),
('2456789', '2026-04-05', 'debit',   22000.00, 349600.00, 'Home Loan EMI - April',               'NEFT',   'NorthStar Bank',      'loan_emi'),
('2456789', '2026-04-10', 'debit',   11200.00, 338400.00, 'Nykaa Luxury Skincare',               'online', 'Nykaa',               'shopping');

-- ── Account 3567890 — Robert Clarke (current/business account) ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('3567890', '2026-01-02', 'credit', 500000.00, 1200000.00, 'Business Revenue - January',         'NEFT',   NULL,                  'business_income'),
('3567890', '2026-01-10', 'debit',   80000.00, 1120000.00, 'Vendor Payment - Raw Materials',     'RTGS',   'Bharat Supplies',     'business_expense'),
('3567890', '2026-01-15', 'debit',   45000.00, 1075000.00, 'Office Rent - January',              'NEFT',   'Prestige Properties', 'rent'),
('3567890', '2026-01-20', 'debit',   12000.00, 1063000.00, 'GST Payment',                        'online', 'GST Portal',          'tax'),
('3567890', '2026-02-02', 'credit', 480000.00, 1543000.00, 'Business Revenue - February',        'NEFT',   NULL,                  'business_income'),
('3567890', '2026-02-10', 'debit',   90000.00, 1453000.00, 'Vendor Payment - Logistics',         'RTGS',   'Blue Dart Logistics', 'business_expense'),
('3567890', '2026-02-15', 'debit',   45000.00, 1408000.00, 'Office Rent - February',             'NEFT',   'Prestige Properties', 'rent'),
('3567890', '2026-03-02', 'credit', 620000.00, 2028000.00, 'Business Revenue - March',           'NEFT',   NULL,                  'business_income'),
('3567890', '2026-03-08', 'debit',  150000.00, 1878000.00, 'Equipment Purchase',                 'RTGS',   'HP India',            'business_expense'),
('3567890', '2026-03-15', 'debit',   45000.00, 1833000.00, 'Office Rent - March',                'NEFT',   'Prestige Properties', 'rent'),
('3567890', '2026-04-02', 'credit', 550000.00, 2383000.00, 'Business Revenue - April',           'NEFT',   NULL,                  'business_income'),
('3567890', '2026-04-07', 'debit',   75000.00, 2308000.00, 'Staff Salaries - April',             'NEFT',   NULL,                  'payroll');

-- ── Account 4678901 — Emily Watson (savings) ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('4678901', '2026-01-05', 'credit',  65000.00,  95000.00, 'Salary Credit - January 2026',       'NEFT',   'Wipro Technologies',  'salary'),
('4678901', '2026-01-08', 'debit',    9800.00,  85200.00, 'Personal Loan EMI',                  'NEFT',   'NorthStar Bank',      'loan_emi'),
('4678901', '2026-01-15', 'debit',    5200.00,  80000.00, 'Amazon Prime + Shopping',             'online', 'Amazon India',        'shopping'),
('4678901', '2026-01-22', 'debit',    3800.00,  76200.00, 'Zomato',                              'UPI',    'Zomato',              'food_dining'),
('4678901', '2026-02-05', 'credit',  65000.00, 141200.00, 'Salary Credit - February 2026',      'NEFT',   'Wipro Technologies',  'salary'),
('4678901', '2026-02-08', 'debit',    9800.00, 131400.00, 'Personal Loan EMI',                  'NEFT',   'NorthStar Bank',      'loan_emi'),
('4678901', '2026-02-14', 'debit',    8500.00, 122900.00, 'Lifestyle Store Purchase',            'POS',    'Lifestyle',           'shopping'),
('4678901', '2026-03-05', 'credit',  65000.00, 187900.00, 'Salary Credit - March 2026',         'NEFT',   'Wipro Technologies',  'salary'),
('4678901', '2026-03-08', 'debit',    9800.00, 178100.00, 'Personal Loan EMI',                  'NEFT',   'NorthStar Bank',      'loan_emi'),
('4678901', '2026-03-20', 'debit',   25000.00, 153100.00, 'Fixed Deposit Opening',              'branch', 'NorthStar Bank',      'investment'),
('4678901', '2026-04-05', 'credit',  65000.00, 218100.00, 'Salary Credit - April 2026',         'NEFT',   'Wipro Technologies',  'salary'),
('4678901', '2026-04-08', 'debit',    9800.00, 208300.00, 'Personal Loan EMI',                  'NEFT',   'NorthStar Bank',      'loan_emi');

-- ── Account 5789012 — Daniel Foster (salary) ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('5789012', '2026-01-03', 'credit',  95000.00, 120000.00, 'Salary Credit - January 2026',       'NEFT',   'Infosys Ltd',         'salary'),
('5789012', '2026-01-05', 'debit',   24500.00,  95500.00, 'Auto Loan EMI',                      'NEFT',   'NorthStar Bank',      'loan_emi'),
('5789012', '2026-01-10', 'debit',    6800.00,  88700.00, 'Fuel - HP Petrol Pump',              'POS',    'HP Petroleum',        'automobile'),
('5789012', '2026-01-20', 'debit',   18000.00,  70700.00, 'Croma Electronics',                  'POS',    'Croma',               'electronics'),
('5789012', '2026-02-03', 'credit',  95000.00, 165700.00, 'Salary Credit - February 2026',      'NEFT',   'Infosys Ltd',         'salary'),
('5789012', '2026-02-05', 'debit',   24500.00, 141200.00, 'Auto Loan EMI',                      'NEFT',   'NorthStar Bank',      'loan_emi'),
('5789012', '2026-02-12', 'debit',    7200.00, 134000.00, 'Fuel + Car Service',                 'POS',    'Maruti Service',      'automobile'),
('5789012', '2026-03-03', 'credit',  95000.00, 229000.00, 'Salary Credit - March 2026',         'NEFT',   'Infosys Ltd',         'salary'),
('5789012', '2026-03-05', 'debit',   24500.00, 204500.00, 'Auto Loan EMI',                      'NEFT',   'NorthStar Bank',      'loan_emi'),
('5789012', '2026-03-18', 'debit',   35000.00, 169500.00, 'International Flight - Emirates',    'online', 'Emirates Airlines',   'travel'),
('5789012', '2026-04-03', 'credit',  95000.00, 264500.00, 'Salary Credit - April 2026',         'NEFT',   'Infosys Ltd',         'salary'),
('5789012', '2026-04-05', 'debit',   24500.00, 240000.00, 'Auto Loan EMI',                      'NEFT',   'NorthStar Bank',      'loan_emi');

-- ── Account 6890123 — Laura Bennett (savings) ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('6890123', '2026-01-07', 'credit',  52000.00,  82000.00, 'Salary Credit - January 2026',       'NEFT',   'HCL Technologies',    'salary'),
('6890123', '2026-01-12', 'debit',    4500.00,  77500.00, 'Grocery - Nature''s Basket',          'POS',    'Nature''s Basket',    'groceries'),
('6890123', '2026-01-18', 'debit',    2800.00,  74700.00, 'Airtel Broadband Bill',               'online', 'Airtel',              'utilities'),
('6890123', '2026-02-07', 'credit',  52000.00, 126700.00, 'Salary Credit - February 2026',      'NEFT',   'HCL Technologies',    'salary'),
('6890123', '2026-02-15', 'debit',    9500.00, 117200.00, 'Tanishq Jewellery',                   'POS',    'Tanishq',             'jewellery'),
('6890123', '2026-02-20', 'debit',    6200.00, 111000.00, 'Shoppers Stop',                       'POS',    'Shoppers Stop',       'shopping'),
('6890123', '2026-03-07', 'credit',  52000.00, 163000.00, 'Salary Credit - March 2026',         'NEFT',   'HCL Technologies',    'salary'),
('6890123', '2026-03-01', 'credit',  75000.00, 238000.00, 'FD Interest Payout',                  'NEFT',   'NorthStar Bank',      'interest'),
('6890123', '2026-03-14', 'debit',   22000.00, 216000.00, 'Air Asia Flight Booking',             'online', 'Air Asia',            'travel'),
('6890123', '2026-04-07', 'credit',  52000.00, 268000.00, 'Salary Credit - April 2026',         'NEFT',   'HCL Technologies',    'salary'),
('6890123', '2026-04-12', 'debit',    5100.00, 262900.00, 'Big Bazaar Grocery',                  'POS',    'Big Bazaar',          'groceries');

-- ── Account 7901234 — Michael Harrington (current/business) ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('7901234', '2026-01-03', 'credit', 800000.00, 2500000.00, 'Business Revenue - Q4 Settlement',   'RTGS',   NULL,                  'business_income'),
('7901234', '2026-01-05', 'debit',   35000.00, 2465000.00, 'Home Loan EMI - January',             'NEFT',   'NorthStar Bank',      'loan_emi'),
('7901234', '2026-01-15', 'debit',  120000.00, 2345000.00, 'Staff Payroll - January',             'NEFT',   NULL,                  'payroll'),
('7901234', '2026-02-03', 'credit', 650000.00, 2995000.00, 'Client Payment - Project Alpha',      'RTGS',   'Bharat Corp',         'business_income'),
('7901234', '2026-02-05', 'debit',   35000.00, 2960000.00, 'Home Loan EMI - February',            'NEFT',   'NorthStar Bank',      'loan_emi'),
('7901234', '2026-02-20', 'debit',  200000.00, 2760000.00, 'TDS Payment Q3',                      'online', 'Income Tax Dept',     'tax'),
('7901234', '2026-03-03', 'credit', 900000.00, 3660000.00, 'Client Payment - Project Beta',       'RTGS',   'NextGen Infra',       'business_income'),
('7901234', '2026-03-05', 'debit',   35000.00, 3625000.00, 'Home Loan EMI - March',               'NEFT',   'NorthStar Bank',      'loan_emi'),
('7901234', '2026-03-10', 'debit',  300000.00, 3325000.00, 'Advance Tax - Q4',                    'NEFT',   'Income Tax Dept',     'tax'),
('7901234', '2026-04-03', 'credit', 720000.00, 4045000.00, 'Business Revenue - April',            'RTGS',   NULL,                  'business_income'),
('7901234', '2026-04-05', 'debit',   35000.00, 4010000.00, 'Home Loan EMI - April',               'NEFT',   'NorthStar Bank',      'loan_emi');

-- ── Account 8012345 — Catherine Ellis (savings) ──
INSERT INTO transactions (account_id, txn_date, txn_type, amount, balance_after, description, channel, merchant_name, category) VALUES
('8012345', '2026-01-10', 'credit', 150000.00, 350000.00, 'Salary Credit - January 2026',       'NEFT',   'Tata Consultancy Svc','salary'),
('8012345', '2026-01-15', 'debit',   28000.00, 322000.00, 'International Shopping - Net',       'online', 'ASOS UK',             'shopping'),
('8012345', '2026-01-20', 'debit',    9500.00, 312500.00, 'Restaurant - Taj Hotel',              'POS',    'Taj Hotels',          'food_dining'),
('8012345', '2026-02-10', 'credit', 150000.00, 462500.00, 'Salary Credit - February 2026',      'NEFT',   'Tata Consultancy Svc','salary'),
('8012345', '2026-02-14', 'debit',   45000.00, 417500.00, 'Louis Vuitton Singapore',            'POS',    'Louis Vuitton',       'shopping'),
('8012345', '2026-02-20', 'debit',   12000.00, 405500.00, 'Spa & Wellness - Ananda Resort',     'POS',    'Ananda Spa',          'wellness'),
('8012345', '2026-03-10', 'credit', 150000.00, 555500.00, 'Salary Credit - March 2026',         'NEFT',   'Tata Consultancy Svc','salary'),
('8012345', '2026-03-15', 'debit',   85000.00, 470500.00, 'Qatar Airways Business Class',       'online', 'Qatar Airways',       'travel'),
('8012345', '2026-03-22', 'debit',   18000.00, 452500.00, 'Lenskart Premium Eyewear',           'online', 'Lenskart',            'shopping'),
('8012345', '2026-04-10', 'credit', 150000.00, 602500.00, 'Salary Credit - April 2026',         'NEFT',   'Tata Consultancy Svc','salary'),
('8012345', '2026-04-12', 'debit',   22000.00, 580500.00, 'Etihad Airways Booking',             'online', 'Etihad Airways',      'travel');

-- ─────────────────────────────────────────────────────────────
-- 4. SEED DATA — LOAN ACCOUNTS (6 rows)
-- ─────────────────────────────────────────────────────────────
INSERT INTO loan_accounts (loan_id, account_id, loan_type, principal, outstanding, disbursed_date, emi_amount, next_emi_date, interest_rate, tenure_months, emi_paid, status) VALUES
('L-789012', '1345367', 'home_loan',      4500000.00, 3820000.00, '2021-06-15',  15000.00, '2026-05-05',  8.75, 300, 58, 'active'),
('L-892345', '2456789', 'home_loan',      6000000.00, 5400000.00, '2023-01-20',  22000.00, '2026-05-05',  8.50, 360, 39, 'active'),
('L-345678', '4678901', 'personal_loan',   500000.00,  280000.00, '2024-03-10',   9800.00, '2026-05-10', 13.50,  60, 25, 'active'),
('L-456789', '5789012', 'auto_loan',      1200000.00,  950000.00, '2023-09-01',  24500.00, '2026-05-01',  9.25,  60, 19, 'active'),
('L-567890', '7901234', 'home_loan',      8000000.00, 7200000.00, '2022-11-05',  35000.00, '2026-05-05',  9.00, 360, 41, 'active'),
('L-678901', '1345367', 'personal_loan',   300000.00,      0.00,  '2020-01-15',   6500.00,  NULL,         12.50,  48, 48, 'closed');

-- ─────────────────────────────────────────────────────────────
-- 5. SEED DATA — FIXED DEPOSITS (6 rows)
-- ─────────────────────────────────────────────────────────────
INSERT INTO fixed_deposits (fd_id, account_id, principal, interest_rate, tenure_days, start_date, maturity_date, maturity_amount, interest_payout, status) VALUES
('FD-111001', '1345367', 200000.00, 7.25, 730, '2025-02-18', '2027-02-18', 232900.00, 'at_maturity', 'active'),
('FD-111002', '1345367',  50000.00, 7.10, 365, '2026-01-01', '2027-01-01',  53550.00, 'quarterly',   'active'),
('FD-222001', '2456789', 500000.00, 7.50, 444, '2025-11-01', '2027-01-19', 546250.00, 'at_maturity', 'active'),
('FD-333001', '3567890', 100000.00, 6.75, 548, '2024-06-01', '2025-12-01', 110125.00, 'quarterly',   'matured'),
('FD-444001', '4678901', 150000.00, 7.25, 730, '2025-09-10', '2027-09-10', 172350.00, 'at_maturity', 'active'),
('FD-555001', '6890123',  75000.00, 7.00, 365, '2026-03-01', '2027-03-01',  80250.00, 'at_maturity', 'active');


-- ─────────────────────────────────────────────────────────────
-- 6. SEED DATA — CREDIT CARDS (4 rows)
-- ─────────────────────────────────────────────────────────────
INSERT INTO credit_cards (card_id, account_id, card_variant, credit_limit, available_limit, outstanding_amt, due_date, min_due, status, issued_date) VALUES
('CC-881001', '1345367', 'NorthStar Gold',       200000.00, 145000.00,  55000.00, '2026-04-25', 2750.00, 'active', '2021-07-01'),
('CC-882001', '2456789', 'NorthStar Platinum',   500000.00, 420000.00,  80000.00, '2026-04-28', 4000.00, 'active', '2022-03-15'),
('CC-883001', '5789012', 'NorthStar Classic',     75000.00,  60000.00,  15000.00, '2026-04-20',  750.00, 'active', '2023-01-10'),
('CC-884001', '8012345', 'NorthStar Signature', 1000000.00, 850000.00, 150000.00, '2026-04-30', 7500.00, 'active', '2024-02-01');

-- ─────────────────────────────────────────────────────────────
-- 7. SEED DATA — CREDIT CARD TRANSACTIONS
-- ─────────────────────────────────────────────────────────────

-- ── CC-881001 — James Mitchell (NorthStar Gold) ──
INSERT INTO card_transactions (card_id, txn_date, txn_type, amount, merchant_name, category, is_international, currency) VALUES
('CC-881001', '2026-01-05', 'purchase',  4800.00, 'BookMyShow',            'entertainment',  FALSE, 'INR'),
('CC-881001', '2026-01-10', 'purchase',  9200.00, 'Croma',                 'electronics',    FALSE, 'INR'),
('CC-881001', '2026-01-15', 'purchase',  3600.00, 'Barbeque Nation',       'food_dining',    FALSE, 'INR'),
('CC-881001', '2026-01-22', 'purchase',  6500.00, 'Myntra',                'shopping',       FALSE, 'INR'),
('CC-881001', '2026-01-28', 'payment',  20000.00, 'NorthStar Payment',     'payment',        FALSE, 'INR'),
('CC-881001', '2026-02-03', 'purchase',  5200.00, 'Zara India',            'shopping',       FALSE, 'INR'),
('CC-881001', '2026-02-10', 'purchase',  7800.00, 'Levi''s Store',         'shopping',       FALSE, 'INR'),
('CC-881001', '2026-02-18', 'purchase', 15500.00, 'MakeMyTrip',            'travel',         FALSE, 'INR'),
('CC-881001', '2026-02-25', 'payment',  25000.00, 'NorthStar Payment',     'payment',        FALSE, 'INR'),
('CC-881001', '2026-03-02', 'purchase',  3200.00, 'Barbeque Nation',       'food_dining',    FALSE, 'INR'),
('CC-881001', '2026-03-05', 'purchase', 12000.00, 'Myntra',                'shopping',       FALSE, 'INR'),
('CC-881001', '2026-03-10', 'purchase',  8500.00, 'Marriott Hotels',       'travel',         FALSE, 'INR'),
('CC-881001', '2026-03-14', 'purchase', 28500.00, 'Singapore Airlines',    'travel',         TRUE,  'SGD'),
('CC-881001', '2026-03-15', 'purchase',  4200.00, 'Amazon UK',             'shopping',       TRUE,  'GBP'),
('CC-881001', '2026-03-18', 'purchase',  1500.00, 'Spotify',               'entertainment',  FALSE, 'INR'),
('CC-881001', '2026-03-22', 'purchase',  9800.00, 'Tanishq Jewellery',     'jewellery',      FALSE, 'INR'),
('CC-881001', '2026-03-25', 'fee',         340.00, 'NorthStar Bank',        'bank_fee',       FALSE, 'INR'),
('CC-881001', '2026-04-01', 'payment',  30000.00, 'NorthStar Payment',     'payment',        FALSE, 'INR'),
('CC-881001', '2026-04-03', 'purchase',  6700.00, 'Reliance Digital',      'electronics',    FALSE, 'INR'),
('CC-881001', '2026-04-07', 'purchase',  2100.00, 'Domino''s Pizza',       'food_dining',    FALSE, 'INR'),
('CC-881001', '2026-04-10', 'purchase', 18000.00, 'IRCTC Tatkal Ticket',   'travel',         FALSE, 'INR');

-- ── CC-882001 — Sarah Thompson (NorthStar Platinum) ──
INSERT INTO card_transactions (card_id, txn_date, txn_type, amount, merchant_name, category, is_international, currency) VALUES
('CC-882001', '2026-01-08', 'purchase',  22000.00, 'Apple India',          'electronics',    FALSE, 'INR'),
('CC-882001', '2026-01-12', 'purchase',   8500.00, 'H&M India',            'shopping',       FALSE, 'INR'),
('CC-882001', '2026-01-20', 'purchase',   4200.00, 'Starbucks',            'food_dining',    FALSE, 'INR'),
('CC-882001', '2026-01-25', 'payment',   30000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-882001', '2026-02-05', 'purchase',  35000.00, 'Maldives Resort',      'travel',         TRUE,  'USD'),
('CC-882001', '2026-02-10', 'purchase',  12000.00, 'Zara',                 'shopping',       FALSE, 'INR'),
('CC-882001', '2026-02-20', 'fee',          520.00, 'NorthStar Bank',       'bank_fee',       FALSE, 'INR'),
('CC-882001', '2026-03-01', 'payment',   40000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-882001', '2026-03-08', 'purchase',  18000.00, 'Nykaa Luxe',           'shopping',       FALSE, 'INR'),
('CC-882001', '2026-03-15', 'purchase',  62000.00, 'Business Class Fare',  'travel',         TRUE,  'USD'),
('CC-882001', '2026-03-22', 'refund',    12000.00, 'Zara Refund',          'shopping',       FALSE, 'INR'),
('CC-882001', '2026-04-01', 'payment',   50000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-882001', '2026-04-10', 'purchase',   9500.00, 'Forest Essentials',    'wellness',       FALSE, 'INR');

-- ── CC-883001 — Daniel Foster (NorthStar Classic) ──
INSERT INTO card_transactions (card_id, txn_date, txn_type, amount, merchant_name, category, is_international, currency) VALUES
('CC-883001', '2026-01-07', 'purchase',  3500.00, 'Swiggy',               'food_dining',    FALSE, 'INR'),
('CC-883001', '2026-01-14', 'purchase',  6800.00, 'Flipkart',             'shopping',       FALSE, 'INR'),
('CC-883001', '2026-01-21', 'purchase',  2200.00, 'PVR Cinemas',          'entertainment',  FALSE, 'INR'),
('CC-883001', '2026-01-28', 'payment',  10000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-883001', '2026-02-08', 'purchase',  4100.00, 'Uber',                 'transport',      FALSE, 'INR'),
('CC-883001', '2026-02-15', 'purchase',  8900.00, 'Boat Lifestyle',       'electronics',    FALSE, 'INR'),
('CC-883001', '2026-02-22', 'payment',  12000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-883001', '2026-03-05', 'purchase',  5600.00, 'Zomato Pro',           'food_dining',    FALSE, 'INR'),
('CC-883001', '2026-03-12', 'purchase',  7200.00, 'Puma Store',           'shopping',       FALSE, 'INR'),
('CC-883001', '2026-03-19', 'purchase',  4800.00, 'MakeMyTrip Bus',       'travel',         FALSE, 'INR'),
('CC-883001', '2026-04-02', 'payment',  15000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-883001', '2026-04-08', 'purchase',  3300.00, 'Ola Electric',         'transport',      FALSE, 'INR');

-- ── CC-884001 — Catherine Ellis (NorthStar Signature) ──
INSERT INTO card_transactions (card_id, txn_date, txn_type, amount, merchant_name, category, is_international, currency) VALUES
('CC-884001', '2026-01-10', 'purchase',  45000.00, 'Chanel Boutique',      'shopping',       TRUE,  'EUR'),
('CC-884001', '2026-01-15', 'purchase',  28000.00, 'The Leela Palace',     'travel',         FALSE, 'INR'),
('CC-884001', '2026-01-22', 'purchase',  12000.00, 'Ather Energy',         'automobile',     FALSE, 'INR'),
('CC-884001', '2026-01-28', 'payment',   80000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-884001', '2026-02-05', 'purchase',  95000.00, 'Hermes Paris',         'shopping',       TRUE,  'EUR'),
('CC-884001', '2026-02-12', 'purchase',  35000.00, 'Four Seasons Hotel',   'travel',         TRUE,  'USD'),
('CC-884001', '2026-02-18', 'fee',        1200.00, 'NorthStar Bank',        'bank_fee',       FALSE, 'INR'),
('CC-884001', '2026-02-25', 'payment',  100000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-884001', '2026-03-03', 'purchase',  22000.00, 'Bulgari Jewellery',    'jewellery',      TRUE,  'USD'),
('CC-884001', '2026-03-10', 'purchase',  18500.00, 'Taj Mahal Hotel',      'travel',         FALSE, 'INR'),
('CC-884001', '2026-03-18', 'purchase',   9800.00, 'Kama Ayurveda',        'wellness',       FALSE, 'INR'),
('CC-884001', '2026-04-01', 'payment',  120000.00, 'NorthStar Payment',    'payment',        FALSE, 'INR'),
('CC-884001', '2026-04-08', 'purchase',  42000.00, 'Singapore Airlines',   'travel',         TRUE,  'SGD'),
('CC-884001', '2026-04-12', 'purchase',  15000.00, 'Neiman Marcus Online', 'shopping',       TRUE,  'USD');

-- ─────────────────────────────────────────────────────────────
-- 8. READ-ONLY GRANTS (for rag_readonly role)
-- ─────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rag_readonly') THEN
        GRANT SELECT ON accounts         TO rag_readonly;
        GRANT SELECT ON transactions     TO rag_readonly;
        GRANT SELECT ON loan_accounts    TO rag_readonly;
        GRANT SELECT ON fixed_deposits   TO rag_readonly;
        GRANT SELECT ON credit_cards     TO rag_readonly;
        GRANT SELECT ON card_transactions TO rag_readonly;
    END IF;
END
$$;

-- ─────────────────────────────────────────────────────────────
-- 9. VERIFICATION
-- ─────────────────────────────────────────────────────────────
SELECT 'accounts'         AS table_name, COUNT(*) AS row_count FROM accounts
UNION ALL
SELECT 'transactions',      COUNT(*) FROM transactions
UNION ALL
SELECT 'loan_accounts',     COUNT(*) FROM loan_accounts
UNION ALL
SELECT 'fixed_deposits',    COUNT(*) FROM fixed_deposits
UNION ALL
SELECT 'credit_cards',      COUNT(*) FROM credit_cards
UNION ALL
SELECT 'card_transactions', COUNT(*) FROM card_transactions
ORDER BY table_name;


-- ─────────────────────────────────────────────────────────────
-- 10. USEFUL SAMPLE QUERIES (for reference / trainees)
-- ─────────────────────────────────────────────────────────────

-- Q1: Last 3 months transaction history for James Mitchell (1345367)
-- SELECT txn_date, txn_type, amount, description, merchant_name, category, channel
-- FROM transactions
-- WHERE account_id = '1345367'
--   AND txn_date >= CURRENT_DATE - INTERVAL '3 months'
-- ORDER BY txn_date DESC;

-- Q2: Outstanding balance and next EMI date for loan L-789012
-- SELECT loan_id, loan_type, outstanding, emi_amount, next_emi_date, interest_rate
-- FROM loan_accounts
-- WHERE loan_id = 'L-789012';

-- Q3: All transactions above ₹50,000 for account 1345367
-- SELECT txn_date, txn_type, amount, description, channel
-- FROM transactions
-- WHERE account_id = '1345367' AND amount > 50000
-- ORDER BY txn_date DESC;

-- Q4: Total spend by category for James Mitchell — last full quarter
-- SELECT category, SUM(amount) AS total_spent, COUNT(*) AS txn_count
-- FROM transactions
-- WHERE account_id = '1345367'
--   AND txn_type = 'debit'
--   AND txn_date >= DATE_TRUNC('quarter', CURRENT_DATE) - INTERVAL '3 months'
--   AND txn_date <  DATE_TRUNC('quarter', CURRENT_DATE)
-- GROUP BY category
-- ORDER BY total_spent DESC;

-- Q5: Active FDs for James Mitchell
-- SELECT fd_id, principal, interest_rate, maturity_date, maturity_amount, interest_payout
-- FROM fixed_deposits
-- WHERE account_id = '1345367' AND status = 'active';

-- Q6: International transactions on credit card CC-881001
-- SELECT txn_date, amount, merchant_name, currency, category
-- FROM card_transactions
-- WHERE card_id = 'CC-881001' AND is_international = TRUE
-- ORDER BY txn_date DESC;

-- Q7: All active loans across all customers with EMI due next month
-- SELECT la.loan_id, a.customer_name, la.loan_type, la.emi_amount, la.next_emi_date, la.outstanding
-- FROM loan_accounts la
-- JOIN accounts a ON la.account_id = a.account_id
-- WHERE la.status = 'active'
--   AND la.next_emi_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
-- ORDER BY la.next_emi_date;

-- Q8: Credit card utilisation summary
-- SELECT cc.card_id, a.customer_name, cc.card_variant,
--        cc.credit_limit, cc.available_limit, cc.outstanding_amt,
--        ROUND((cc.outstanding_amt / cc.credit_limit) * 100, 2) AS utilisation_pct
-- FROM credit_cards cc
-- JOIN accounts a ON cc.account_id = a.account_id
-- WHERE cc.status = 'active'
-- ORDER BY utilisation_pct DESC;

-- Q9: Monthly spend trend for James Mitchell (bank transactions)
-- SELECT DATE_TRUNC('month', txn_date) AS month,
--        SUM(CASE WHEN txn_type = 'debit'  THEN amount ELSE 0 END) AS total_debits,
--        SUM(CASE WHEN txn_type = 'credit' THEN amount ELSE 0 END) AS total_credits
-- FROM transactions
-- WHERE account_id = '1345367'
-- GROUP BY 1 ORDER BY 1;

-- Q10: Top 5 merchants by spend on CC-881001 (excluding payments/fees)
-- SELECT merchant_name, SUM(amount) AS total_spend, COUNT(*) AS txn_count
-- FROM card_transactions
-- WHERE card_id = 'CC-881001'
--   AND txn_type = 'purchase'
-- GROUP BY merchant_name
-- ORDER BY total_spend DESC
-- LIMIT 5;
