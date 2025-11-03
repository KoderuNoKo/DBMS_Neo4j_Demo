# Guide for creating a PostgreSQL database

1. Install pgAdmin 4
2. Create a new local database, name it `mridata` (or anything you like)
3. Open "Query Tool" for the created database, then run `create_db.sql` to create the database schema
4. Open "PSQL Tool" for the created database, run the following command for each table to copy data from csv files to Postgres

```sh
\copy <table> FROM '\path\to\ml-latest\<table>.csv' WITH (FORMAT csv, HEADER true);
```
