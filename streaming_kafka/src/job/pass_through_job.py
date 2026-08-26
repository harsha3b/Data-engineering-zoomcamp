from pyflink.datastream import StreamExecutionEnvironment
from pyflink.java_gateway import get_gateway
from pyflink.table import EnvironmentSettings, StreamTableEnvironment

POSTGRES_URL = 'jdbc:postgresql://postgres:5432/postgres'
POSTGRES_USER = 'postgres'
POSTGRES_PASSWORD = 'postgres'


def ensure_postgres_table(table_name, columns_ddl):
    """Flink's JDBC sink DDL only registers a table in Flink's catalog, it
    never creates the table in Postgres itself, so the physical table has
    to be created here first or every insert fails with
    'relation "..." does not exist'."""
    jvm = get_gateway().jvm
    conn = jvm.java.sql.DriverManager.getConnection(
        POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD
    )
    try:
        stmt = conn.createStatement()
        try:
            stmt.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns_ddl})')
        finally:
            stmt.close()
    finally:
        conn.close()


def create_processed_events_sink_postgres(t_env):
    table_name = 'processed_events'
    ensure_postgres_table(
        table_name,
        """
        pulocationid INTEGER,
        dolocationid INTEGER,
        trip_distance DOUBLE PRECISION,
        total_amount DOUBLE PRECISION,
        pickup_datetime TIMESTAMP
        """,
    )
    sink_ddl = f"""
        CREATE TABLE {table_name} (
            PULocationID INTEGER,
            DOLocationID INTEGER,
            trip_distance DOUBLE,
            total_amount DOUBLE,
            pickup_datetime TIMESTAMP
        ) WITH (
            'connector' = 'jdbc',
            'url' = '{POSTGRES_URL}',
            'table-name' = '{table_name}',
            'username' = '{POSTGRES_USER}',
            'password' = '{POSTGRES_PASSWORD}',
            'driver' = 'org.postgresql.Driver'
        );
        """
    t_env.execute_sql(sink_ddl)
    return table_name


def create_events_source_kafka(t_env):
    table_name = "events"
    source_ddl = f"""
        CREATE TABLE {table_name} (
            PULocationID INTEGER,
            DOLocationID INTEGER,
            trip_distance DOUBLE,
            total_amount DOUBLE,
            tpep_pickup_datetime BIGINT
        ) WITH (
            'connector' = 'kafka',
            'properties.bootstrap.servers' = 'redpanda:29092',
            'topic' = 'rides',
            'scan.startup.mode' = 'earliest-offset',
            'properties.auto.offset.reset' = 'earliest',
            'format' = 'json'
        );
        """
    t_env.execute_sql(source_ddl)
    return table_name

def log_processing():
    # Set up the execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)

    # Set up the table environment
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)
    try:
        # Create Kafka table
        source_table = create_events_source_kafka(t_env)
        postgres_sink = create_processed_events_sink_postgres(t_env)
        # write records to postgres
        t_env.execute_sql(
            f"""
                    INSERT INTO {postgres_sink}
                    SELECT
                        PULocationID,
                        DOLocationID,
                        trip_distance,
                        total_amount,
                        TO_TIMESTAMP_LTZ(tpep_pickup_datetime, 3) as pickup_datetime
                    FROM {source_table}
                    """
        ).wait()

    except Exception as e:
        print("Writing records from Kafka to JDBC failed:", str(e))


if __name__ == '__main__':
    log_processing()