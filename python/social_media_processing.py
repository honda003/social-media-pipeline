#!/usr/bin/env python
# coding: utf-8

# In[1]:

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, coalesce, when, expr
from datetime import datetime
import os

os.environ["PYSPARK_SUBMIT_ARGS"] = (
    "--jars /opt/spark/jars/hadoop-aws-3.3.6.jar,"
    "/opt/spark/jars/aws-java-sdk-bundle-1.12.520.jar,"
    "/opt/spark/jars/postgresql-42.6.0.jar pyspark-shell"
)

today = datetime.now().strftime("%Y-%m-%d")
# In[2]:


spark = SparkSession.builder \
    .appName("SocialMediaAnalytics") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minio") \
    .config("spark.hadoop.fs.s3a.secret.key", "minio123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .getOrCreate()


# In[8]:
# YouTube path for today's folder
youtube_path = f"s3a://socialmedia/youtube/{today}/*.json"

# Load YouTube data
youtube_df = spark.read.option("multiline", "true").json(youtube_path)


# In[9]:


youtube_df.printSchema()


# In[11]:


youtube_df_clean = youtube_df.select(
    col("post_id").alias("id"),
    col("title").alias("title"),
    col("channel_title").alias("author"),
    col("likes").cast("int").alias("likes"),
    col("comments").cast("int").alias("comments"),
    col("published_at").alias("created_at")
).withColumn("platform", lit("youtube"))

# Add score column (likes + comments)
youtube_df_clean = youtube_df_clean.withColumn(
    "score", col("likes") + col("comments")
)


# In[18]:


youtube_df_clean.printSchema()


# In[13]:
# Reddit path for today's folder
reddit_path = f"s3a://socialmedia/reddit/{today}/*.json"

# load reddit data
reddit_df = spark.read.option("multiline", "true").json(reddit_path)


# In[14]:


reddit_df.printSchema()


# In[16]:


reddit_df_clean = reddit_df.select(
    col("post_id").alias("id"),
    col("title").alias("title"),
    lit(None).alias("author"),            
    col("score").cast("int").alias("likes"),
    col("num_comments").cast("int").alias("comments"),
    col("created_utc").alias("created_at")
).withColumn("platform", lit("reddit"))

# Add score = likes + comments
reddit_df_clean = reddit_df_clean.withColumn(
    "score", col("likes") + col("comments")
)


# In[17]:


reddit_df_clean.printSchema()


# In[20]:


# Union both platforms into one DF
social_df = youtube_df_clean.unionByName(reddit_df_clean)


# In[26]:


postgres_url = "jdbc:postgresql://postgres:5432/social_media_analytics"  # use service name "postgres" + DB name
postgres_props = {
    "user": "admin",
    "password": "password",
    "driver": "org.postgresql.Driver"
}


# In[27]:


social_df.write.jdbc(
    url=postgres_url,
    table="social_media_posts",
    mode="append",
    properties=postgres_props
)






