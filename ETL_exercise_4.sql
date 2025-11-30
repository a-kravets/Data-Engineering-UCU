/* ******************************************************************************************************************************
 * Scenario 4: Build a special bridge table for the organization structure (using Closure table approach)
 * 
 * Inputs:
 *   2 target tables: 
 *     1) dim_employee (already prepolulated)
 *     2) bridge_employee_hierachy table where hierarchical data should be populate according to Closure table approach  
 * 
 *   1 input table:
 *     1) stg_employee table where each record contains parent_id
 *     
 ****************************************************************************************************************************** */

------------------------------------------------------------------------------------------------------------------
-- Initialization (target tables)
------------------------------------------------------------------------------------------------------------------
drop table if exists dim_employee;
create table dim_employee(
    employee_sk serial primary key,
    employee_bk varchar(255),
    full_name  varchar(255)
);
truncate table dim_employee;
insert into dim_employee(employee_bk, full_name) 
values 
('uk100', 'Lori Smith'),
('uk101', 'Ivan Kohut'),
('uk102', 'Oksana Lysytsia'),
('uk103', 'Iryna Vovk'),
('uk104', 'Mag Smith'),
('uk105', 'Ivanka Kohut'),
('uk106', 'Leyla Lysytsia'),
('uk107', 'Olesia Vovk'),
('uk108', 'John Smith'),
('uk109', 'Ivan Piven'),
('uk110', 'Oksana Baran'),
('uk111', 'Iryna Zayets');

drop table if exists bridge_employee_hierachy;
create table bridge_employee_hierachy(
    ancestor_employee_sk int not null,
    descendant_employee_sk int not null,
    depth_from_parent int,
    is_leave boolean,
    primary key (ancestor_employee_sk,descendant_employee_sk)
);


------------------------------------------------------------------------------------------------------------------
-- Initialization (target tables)
------------------------------------------------------------------------------------------------------------------
drop table if exists stg_employee;
create table stg_employee(
    employee_bk varchar(255) not null primary key,
    full_name  varchar(255),
    parent_bk varchar(255)
);

truncate table stg_employee;
insert into stg_employee(employee_bk, full_name, parent_bk) 
values 
('uk100', 'Lori Smith',null),
('uk101', 'Ivan Kohut','uk100'),
('uk102', 'Oksana Lysytsia','uk100'),
('uk103', 'Iryna Vovk','uk101'),
('uk104', 'Mag Smith','uk101'),
('uk105', 'Ivanka Kohut','uk102'),
('uk106', 'Leyla Lysytsia','uk102'),
('uk107', 'Olesia Vovk','uk104'),
('uk108', 'John Smith','uk104'),
('uk109', 'Ivan Piven','uk107'),
('uk110', 'Oksana Baran','uk108'),
('uk111', 'Iryna Zayets','uk109');


/* ******************************************************************************************************************************
 * Exersize #4 (build hierarchy bridge table):
 * Prepare a SQL script (sequence of SQL statements) to build the bridge_employee_hierachy table according to closure table algorithm
 ****************************************************************************************************************************** */

 --SELECT * FROM stg_employee;
 --SELECT * FROM dim_employee;

-- https://stackoverflow.com/questions/12621873/how-can-i-create-a-closure-table-using-data-from-an-adjacency-list

WITH RECURSIVE org AS (

    -- base level: each employee is ancestor of itself
    SELECT
        de.employee_sk AS ancestor_employee_sk,
        de.employee_sk AS descendant_employee_sk,
        0              AS depth,
        se.parent_bk   AS parent_bk,
        de.employee_bk AS employee_bk
    FROM dim_employee de
    LEFT JOIN stg_employee se
        ON de.employee_bk = se.employee_bk

    UNION ALL

    -- moving down
    SELECT
        org.ancestor_employee_sk,
        child.employee_sk AS descendant_employee_sk,
        org.depth + 1      AS depth,
        se2.parent_bk      AS parent_bk,
        child.employee_bk  AS employee_bk
    FROM org
    JOIN stg_employee se2
        ON se2.parent_bk = org.employee_bk
    JOIN dim_employee child
        ON child.employee_bk = se2.employee_bk
),

-- finding out how many children each employee has
children AS (
    SELECT
        parent_bk AS employee_bk,
        COUNT(*)  AS children_count
    FROM stg_employee
    WHERE parent_bk IS NOT NULL
    GROUP BY parent_bk
)

INSERT INTO bridge_employee_hierachy
    (ancestor_employee_sk, descendant_employee_sk, depth_from_parent, is_leave)
SELECT
    org.ancestor_employee_sk,
    org.descendant_employee_sk,
    org.depth,
    (c.children_count IS NULL) AS is_leave
FROM org
LEFT JOIN children c ON org.employee_bk = c.employee_bk;


--SELECT * FROM bridge_employee_hierachy