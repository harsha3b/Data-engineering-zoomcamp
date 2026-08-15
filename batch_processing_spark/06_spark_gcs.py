#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pyspark
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from pyspark.context import SparkContext


# In[2]:


credentials_location = '/home/harsh/Data-engineering-zoomcamp/batch_processing_spark/kestra-sandbox-499212-740514085025.json'
conf = SparkConf() \
    .setMaster('local[*]') \
    .setAppName('test') \
    .set("spark.jars", "./lib/gcs-connector-hadoop3-2.2.25-shaded.jar") \
    .set("spark.hadoop.google.cloud.auth.service.account.enable", "true") \
    .set("spark.hadoop.google.cloud.auth.service.account.json.keyfile", credentials_location)


# In[3]:


sc = SparkContext(conf=conf)

hadoop_conf = sc._jsc.hadoopConfiguration()

hadoop_conf.set("fs.AbstractFileSystem.gs.impl",  "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS")
hadoop_conf.set("fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
hadoop_conf.set("fs.gs.auth.service.account.json.keyfile", credentials_location)
hadoop_conf.set("fs.gs.auth.service.account.enable", "true")
hadoop_conf.set("fs.gs.block.size", "67108864")
hadoop_conf.set("fs.gs.rewrite.max.chunk.size", "536870912")
hadoop_conf.set("fs.gs.outputstream.buffer.size", "8388608")
hadoop_conf.set("fs.gs.inputstream.inplace.seek.limit", "8388608")
hadoop_conf.set("fs.gs.inputstream.min.range.request.size", "2097152")


# In[4]:


spark = SparkSession.builder \
    .config(conf=sc.getConf()) \
    .getOrCreate()


# In[5]:


df_green = spark.read.parquet('gs://spark-tutorial-pq/pq/green/*/*')


# In[9]:


df_green.count()


# In[7]:


df_green.show()


# In[10]:


sc._jvm.org.apache.hadoop.util.VersionInfo.getVersion()


# In[6]:


spark.stop()


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




