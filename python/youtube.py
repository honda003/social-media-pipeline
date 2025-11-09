import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from googleapiclient.discovery import build
from minio import Minio

# Load API key
load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")

# YouTube API setup
youtube = build("youtube", "v3", developerKey=api_key)
CHANNEL_ID = "UC8butISFwT-Wl7EV0hUK0BQ"  # FreeCodeCamp channel

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

# Load state (seen video IDs)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # directory of youtube.py
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
object_prefix = f"youtube/{today}/{time_now}.json"

# Fetch latest videos metadata
search_request = youtube.search().list(
    part="snippet",
    channelId=CHANNEL_ID,
    maxResults=10,
    order="date"
)
search_response = search_request.execute()

videos = []
for item in search_response.get("items", []):
    video_id = item["id"].get("videoId")
    if video_id and video_id not in seen_ids:
        # Fetch statistics
        stats_request = youtube.videos().list(
            part="statistics",
            id=video_id
        )
        stats_response = stats_request.execute()
        stats = stats_response["items"][0]["statistics"]

        videos.append({
            "post_id": video_id,
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"],
            "channel_title": item["snippet"]["channelTitle"],
            "description": item["snippet"]["description"],
            "views": stats.get("viewCount", 0),
            "likes": stats.get("likeCount", 0),
            "comments": stats.get("commentCount", 0),
            "platform": "youtube"
        })
        seen_ids.add(video_id)

# Save to MinIO
if videos:
    tmp_file = f"/tmp/{time_now}.json"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2)

    minio_client.fput_object(bucket_name, object_prefix, tmp_file)
    print(f"✅ Uploaded {object_prefix} to MinIO")

    # Update state
    state["seen_ids"] = list(seen_ids)
    with open(state_file, "w") as f:
        json.dump(state, f)
else:
    print("No new YouTube videos found.")

