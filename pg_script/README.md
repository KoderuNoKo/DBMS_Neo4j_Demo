# Guide for creating a PostgreSQL database

1. Install pgAdmin 4
2. Create a new local database, name it `movielens` 
3. Open "Query Tool" for the created database, then run `create_db.sql` to create the database schema
4. Open "PSQL Tool" for the created database, run the following command for each table to copy data from csv files to Postgres

```sh
\copy <table> FROM '\path\to\ml-latest\<table>.csv' WITH (FORMAT csv, HEADER true);
```

- For the table `Tag`, it require an additional column `tagId` as `PRIMARY KEY`, so its copy command is a bit different.

```sh
\copy Tag(userId, movieId, tag, timestamp) FROM '\path\to\ml-latest\tags.csv' WITH (FORMAT csv, HEADER true)
```

5. In case of failure due to encoding errors, returning something like

```sh
ERROR:  character with byte sequence 0x81 in encoding "WIN1252" has no equivalent in encoding "UTF8"
CONTEXT:  COPY movie, line 640
```

- Update the `DIR` constants in `clean_encoding.py` and run it
- The cleaned files should appear in `./ml-latest/cleaned/` update the path for the above copy commands and try again