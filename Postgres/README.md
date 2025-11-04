# Guide for creating a PostgreSQL database

1. Install pgAdmin 4
2. Create a new local database, name it `mridata` (or anything you like)
3. Open "Query Tool" for the created database, then run `create_db.sql` to create the database schema (the documentation for the schema can be found in `./docs/postgres_schema.md`)
4. Open "PSQL Tool" for the created database, run the following command for each table to copy data from csv files to Postgres

```sh
\copy <table> FROM '\path\to\ml-latest\<table>.csv' WITH (FORMAT csv, HEADER true);
```

## Chuẩn bị data để import (new)

- Ở thư mục ngoài cùng, chạy lệnh sau (cần có python virtual environment, xem README ở ngoài) 

```bash
python ./MriExporter/main.py
```

- Sau khi chạy xong, trong thư mục `mri_export` sẽ có cái file csv, dùng các file csv này để import vào PostgreSQL