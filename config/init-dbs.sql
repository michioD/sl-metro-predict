-- Initialization script for PostgreSQL databases

-- Airflow is the default database from POSTGRES_DB in docker-compose
-- We need to create additional databases for MLflow and the Data Warehouse (dbt)

CREATE DATABASE mlflow;
GRANT ALL PRIVILEGES ON DATABASE mlflow TO airflow;

CREATE DATABASE data_warehouse;
GRANT ALL PRIVILEGES ON DATABASE data_warehouse TO airflow;

\c data_warehouse
CREATE SCHEMA bronze;
CREATE SCHEMA silver;
CREATE SCHEMA gold;
GRANT ALL PRIVILEGES ON SCHEMA bronze TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA silver TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA gold TO airflow;
