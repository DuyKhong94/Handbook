from pymongo import MongoClient
import os

def get_db():
    # đường dẫn MongoDB của bạn
    url = os.getenv("MONGO_URL")
    client = MongoClient(url)
    db = client["handbook"]  # tên database
    return db