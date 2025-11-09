import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import praw
from minio import Minio

# Load env
load_dotenv()
client_id = os.getenv("REDDIT_CLIENT_ID")
secret = os.getenv("REDDIT_SECRET")
user_agent = os.getenv("REDDIT_USER_AGENT")

# Reddit API
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=secret,
    user_agent=user_agent
)

# MinIO client
minio_client = Minio(
    "minio:9000", #container's internal port and name
    access_key="minio",
    secret_key="minio123",
    secure=False
)

bucket_name = "socialmedia"
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)

# Load state
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # directory of reddit.py
state_file = os.path.join(BASE_DIR, "states/reddit_state.json")

if os.path.exists(state_file):
    with open(state_file, "r") as f:
        state = json.load(f)
else:
    state = {"seen_ids": []}

seen_ids = set(state["seen_ids"])

# Folder path in MinIO
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
time_now = datetime.now(timezone.utc).strftime("%H-%M-%S")
object_prefix = f"reddit/{today}/{time_now}.json"

# Fetch posts
subreddit = reddit.subreddit("python")
posts = []
for post in subreddit.new(limit=20):
    if post.id not in seen_ids:
        posts.append({
            "post_id": post.id,
            "title": post.title,
            "score": post.score,             # popularity (upvotes - downvotes)
            "num_comments": post.num_comments,  # engagement
            "created_utc": datetime.utcfromtimestamp(post.created_utc).isoformat() + "Z",
            "platform": "reddit",
            "url": post.url,
        })
        seen_ids.add(post.id)

# Save to MinIO
if posts:
    tmp_file = f"/tmp/{time_now}.json"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)

    minio_client.fput_object(bucket_name, object_prefix, tmp_file)
    print(f"✅ Uploaded {object_prefix} to MinIO")

    # Update state
    state["seen_ids"] = list(seen_ids)
    with open(state_file, "w") as f:
        json.dump(state, f)
else:
    print("No new Reddit posts found.")
