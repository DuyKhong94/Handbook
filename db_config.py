from pymongo import MongoClient
import os
USERNAME= "duy1994_user"
PASSWORD = urllib.parse.quote_plus("trungduy94")
MONGO_URL="    f"mongodb+srv://{USERNAME}:{PASSWORD}"
    "@duy1994.hou188l.mongodb.net/handbook"
    "?retryWrites=true&w=majority"
def get_db():
    # đường dẫn MongoDB của bạn
    url = os.getenv("MONGO_URL")
    client = MongoClient(url)
    db = client["handbook"]  # tên database

    return db
