CREATE DATABASE adb;
USE adb;

GRANT ALL PRIVILEGES ON adb.* TO 'root'@'localhost';
FLUSH PRIVILEGES;

select * from participants;
select * from projects;
select * from sessions;
select * from session_lineage;

-- drop table session_lineage;
-- drop table sessions;
-- drop table projects;
-- drop table participants;