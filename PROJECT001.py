from kafka import KafkaConsumer
import happybase
from pyspark.sql import SparkSession
from elasticsearch import Elasticsearch
import json

# Kafka consumer configuration
KAFKA_TOPIC = 'clickstream'
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'

# HBase configuration
HBASE_HOST = 'localhost'
HBASE_TABLE_NAME = 'clickstream_data'

# Elasticsearch configuration
ES_HOST = 'localhost'
ES_PORT = 9200
ES_INDEX_NAME = 'processed_clickstream_data'

# Initialize Kafka consumer
consumer = KafkaConsumer(KAFKA_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

# Initialize HBase connection
hbase_connection = happybase.Connection(HBASE_HOST)
hbase_table = hbase_connection.table(HBASE_TABLE_NAME)

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Clickstream Data Processing") \
    .getOrCreate()

# Initialize Elasticsearch connection
es = Elasticsearch([{'host': ES_HOST, 'port': ES_PORT}])

def process_clickstream_data():
    # Read data from HBase
    hbase_rdd = spark.sparkContext.parallelize(hbase_table.scan())
    hbase_df = spark.createDataFrame(hbase_rdd)

    # Process data using Spark
    processed_data = hbase_df.groupBy("url", "country") \
        .agg({"clicks": "count", "unique_users": "countDistinct", "time_spent": "avg"})

    # Write processed data to Elasticsearch
    for row in processed_data.collect():
        es.index(index=ES_INDEX_NAME, body=row.asDict())

# Main loop
for message in consumer:
    # Deserialize message and store in HBase
    clickstream_data = json.loads(message.value)
    hbase_table.put(clickstream_data['event_id'], {
        b'click_data:user_id': clickstream_data['user_id'],
        b'click_data:timestamp': clickstream_data['timestamp'],
        b'click_data:url': clickstream_data['url'],
        b'geo_data:country': clickstream_data['country'],
        b'geo_data:city': clickstream_data['city'],
        b'user_agent_data:browser': clickstream_data['browser'],
        b'user_agent_data:os': clickstream_data['os'],
        b'user_agent_data:device': clickstream_data['device']
    })

    # Periodically process clickstream data
    process_clickstream_data()

#%%
