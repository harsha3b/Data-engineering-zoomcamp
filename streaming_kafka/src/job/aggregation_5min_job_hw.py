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


def create_trip_counts_sink(t_env):
    table_name = 'gt_trip_counts_5min'
    ensure_postgres_table(
        table_name,
        """
        window_start TIMESTAMP,
        pulocationid INTEGER,
        num_trips BIGINT,
        PRIMARY KEY (window_start, pulocationid)
        """,
    )
    sink_ddl = f"""
        CREATE TABLE {table_name} (
            window_start TIMESTAMP(3),
            PULocationID INT,
            num_trips BIGINT,
            PRIMARY KEY (window_start, PULocationID) NOT ENFORCED
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
            passenger_count INTEGER,
            trip_distance DOUBLE,
            tip_amount DOUBLE,
            total_amount DOUBLE,
            lpep_pickup_datetime BIGINT,
            lpep_dropoff_datetime BIGINT,
            event_timestamp AS TO_TIMESTAMP_LTZ(lpep_pickup_datetime, 3),
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'properties.bootstrap.servers' = 'redpanda:29092',
            'topic' = 'green-trips',
            'scan.startup.mode' = 'earliest-offset',
            'properties.auto.offset.reset' = 'earliest',
            'format' = 'json'
        );
        """
    t_env.execute_sql(source_ddl)
    return table_name


def log_aggregation():
    # Set up the execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(1)

    # Set up the table environment
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    try:
        # Create Kafka table
        source_table = create_events_source_kafka(t_env)
        trip_counts_table = create_trip_counts_sink(t_env)

        t_env.execute_sql(f"""
        INSERT INTO {trip_counts_table}
        SELECT
            window_start,
            PULocationID,
            COUNT(*) AS num_trips
        FROM TABLE(
            TUMBLE(TABLE {source_table}, DESCRIPTOR(event_timestamp), INTERVAL '5' MINUTES)
        )
        GROUP BY window_start, PULocationID;

        """).wait()

    except Exception as e:
        print("Writing records from Kafka to JDBC failed:", str(e))


if __name__ == '__main__':
    log_aggregation()