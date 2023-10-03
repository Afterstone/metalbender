-- NB
--  Meant to be run manually.
--  Remember to change your working database to the 
--      one you want the user to have access to.
--      Schema public is the default schema in the CURRENT database.
-- Remember to change the following variables:
--      ${USERNAME}
--      ${PASSWORD}
--      ${DATABASE}


CREATE USER ${USERNAME} WITH PASSWORD '${PASSWORD}' LOGIN;
GRANT CONNECT ON DATABASE ${DATABASE} TO ${USERNAME};
GRANT USAGE ON SCHEMA public TO ${USERNAME};

-- Change as needed
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${USERNAME};

-- Change as needed.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${USERNAME};

-- Change as needed.
GRANT CREATE ON SCHEMA public TO ${USERNAME};