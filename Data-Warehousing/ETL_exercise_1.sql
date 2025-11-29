/* ******************************************************************************************************************************
 * 
 * Scenario 1: SCD1 and SCD2 incremental data processing
 *     
 ****************************************************************************************************************************** */

------------------------------------------------------------------------------------------------------------------
-- Initialization
------------------------------------------------------------------------------------------------------------------
drop table if exists dim_customer;
create table dim_customer(
    customer_sk serial primary key,
    customer_bk varchar(255),
    full_name  varchar(255),   -- SCD1 attribure
    country varchar(255),      -- SCD2 attribure
    state_region varchar(255), -- SCD2 attribure
    valid_from timestamp,
    valid_to timestamp
);
truncate table dim_customer;
insert into dim_customer(customer_bk, full_name, country, state_region, valid_from, valid_to) 
values 
('us101', 'Lori Smith', 'US', 'Texas', '1900-01-01','9999-12-31 23:59:59'),
('uk101', 'Ivan Kohut', 'Ukraine', 'Lviv', '1900-01-01','2020-10-31 23:59:59'),
('uk101', 'Ivan Kohut', 'Ukraine', 'Kyiv', '2020-11-01','9999-12-31 23:59:59'),
('uk102', 'Oksana Lysytsia', 'Ukraine', 'Ternopil', '1900-01-01','9999-12-31 23:59:59'),
('uk103', 'Iryna Vovk', 'Ukraine', 'Ivano-Frankivsk', '1900-01-01','9999-12-31 23:59:59');


drop table if exists stg_customer;
create table stg_customer(
    customer_bk varchar(255) primary key,
    full_name  varchar(255),
    country varchar(255),
    state_region varchar(255)
);
truncate table stg_customer;
insert into stg_customer(customer_bk, full_name, country, state_region) 
values 
('us101', 'Lorelei Smith', 'US', 'Texas'), 
('us102', 'Chris Black', 'US', 'California'),
('uk101', 'Ivan Kohut-Baran', 'Ukraine', 'Irpin'),
('uk102', 'Oksana Lysytsia-Vovk', 'Ukraine', 'Ternopil'),
('uk103', 'Iryna Vovk', 'Ukraine', 'Ivano-Frankivsk');



/* ******************************************************************************************************************************
 * Exersize #1:
 * Prepare a SQL script (sequence of SQL statements) to implement the merging of the stg_customer (increment of the customer data) 
 * into the target dim_customer dimension table  
 ****************************************************************************************************************************** */


 /* -------------------------
   Since we have duplicate bk for different customers (for instance, us101), there could be a situation when 
   the same customer will have both SCD 1 and SCD 2
   So we need to clearly seperate SCD 1 and SCD 2 logic 
---------------------------- */

-- for customers with SCD 1 and SCD 1 + SCD 2 

MERGE INTO dim_customer AS d
USING stg_customer AS s
ON (
    d.customer_bk = s.customer_bk
)

WHEN MATCHED AND
     d.full_name <> s.full_name
 AND (d.country = s.country
 OR d.state_region = s.state_region)
THEN UPDATE SET
    full_name = s.full_name;

-- for new rows

MERGE INTO dim_customer AS d
USING stg_customer AS s
ON (
    d.customer_bk = s.customer_bk
    AND d.valid_to = '9999-12-31 23:59:59'
)

WHEN NOT MATCHED THEN
INSERT (
    customer_bk, full_name, country, state_region,
    valid_from, valid_to
)
VALUES (
    s.customer_bk,
    s.full_name,
    s.country,
    s.state_region,
    CURRENT_TIMESTAMP,
    '9999-12-31 23:59:59'
);

-- updating existing rows' valid_to for SCD 2

MERGE INTO dim_customer AS d
USING stg_customer AS s
ON (
    d.customer_bk = s.customer_bk
    AND d.valid_to = '9999-12-31 23:59:59'
)
WHEN MATCHED AND
     (d.country <> s.country OR d.state_region <> s.state_region)
THEN UPDATE SET
    valid_to = CURRENT_TIMESTAMP;

-- inserting new rows for SCD 2

INSERT INTO dim_customer (
    customer_bk, full_name, country, state_region,
    valid_from, valid_to
)
SELECT
    s.customer_bk,
    s.full_name,
    s.country,
    s.state_region,
    CURRENT_TIMESTAMP,
    '9999-12-31 23:59:59'
FROM stg_customer s
JOIN dim_customer d
  ON s.customer_bk = d.customer_bk
 AND d.valid_to = CURRENT_TIMESTAMP;

