/* ******************************************************************************************************************************
 * Scenario 3: Multivalued Relationships. Part 2
 * 
 * Incremental data processing. After the initial data population the new portion of the source data has been arrived.
 * The requirements are to incrementally merge this data into the target tables.
 *     
 ****************************************************************************************************************************** */

/* ******************************************************************************************************************************
-- New portion of the source data
****************************************************************************************************************************** */
insert into stg_inspection values
(21,'uk102'),(21,'uk103'),
(22,'uk107'),(22,'uk106'),(22,'uk105'),
(23,'uk103'),(23,'uk104'),(23,'uk105'),
(24,'uk100'),(24,'uk105'),
(25,'uk100'),(25,'uk103'),(25,'uk111'),
(26,'uk100'),(26,'uk105'),
(27,'uk100'),(27,'uk103'),(27,'uk111');

/* ******************************************************************************************************************************
 * Exersize #3 (incremental processing):
 * Prepare a SQL script (sequence of SQL statements) to merge the new portion of the data into the target table:
 *   1) dim_technician_group;
 *   2) bridge_technician_group;
 *   3) fact_inspection;
 ****************************************************************************************************************************** */

 -- selecting new inspections
with new_inspection_groups as (
    select 
        si.inspection_id,
        string_agg(employee_bk, ',' order by employee_bk) as group_code
    from stg_inspection si
	left join fact_inspection fi
		on si.inspection_id = fi.inspection_id
	where fi.inspection_id is null
    group by si.inspection_id
)
-- inserting new rows (when not matched) to dim_technician_group
merge into dim_technician_group as dg
using (
  select distinct group_code from new_inspection_groups
) as src
on dg.group_code = src.group_code
when not matched then
  insert (group_code) values (src.group_code);


-- inserting new rows (when not matched) to bridge_technician_group
with new_inspection_groups as (
    select 
        si.inspection_id,
        string_agg(employee_bk, ',' order by employee_bk) as group_code
    from stg_inspection si
	left join fact_inspection fi
		on si.inspection_id = fi.inspection_id
	where fi.inspection_id is null
    group by si.inspection_id
)
merge into bridge_technician_group as b
using (
  select distinct
    dg.employee_group_sk,
    dt.employee_sk
  from new_inspection_groups nig
  join dim_technician_group dg
    on dg.group_code = nig.group_code
  join stg_inspection si
    on si.inspection_id = nig.inspection_id
  join dim_technician dt
    on dt.employee_bk = si.employee_bk
) as src
on ( b.employee_group_sk = src.employee_group_sk
     and b.employee_sk = src.employee_sk )
when not matched then
  insert (employee_group_sk, employee_sk)
  values (src.employee_group_sk, src.employee_sk);

-- inserting new rows to fact_inspection
with new_inspection_groups as (
    select 
        si.inspection_id,
        string_agg(employee_bk, ',' order by employee_bk) as group_code
    from stg_inspection si
	left join fact_inspection fi
		on si.inspection_id = fi.inspection_id
	where fi.inspection_id is null
    group by si.inspection_id
)
merge into fact_inspection as f
using (
  select
    nig.inspection_id,
    dg.employee_group_sk
  from new_inspection_groups nig
  join dim_technician_group dg
    on dg.group_code = nig.group_code
) as src
on f.inspection_id = src.inspection_id
when not matched then
  insert (inspection_id, employee_group_sk)
  values (src.inspection_id, src.employee_group_sk);

