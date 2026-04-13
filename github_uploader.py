import requests
import base64
def upload_file_to_github(
    token,
    owner,
    repo,
    file_path_repo,
    file_path_local,
    branch="main",
    commit_message="update file"
):
    # đọc file
    with open(file_path_local, "rb") as f:
        content = f.read()

    encoded_content = base64.b64encode(content).decode("utf-8")

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path_repo}"

    headers = {
        "Authorization": f"token {token}"
    }

    # lấy SHA nếu file tồn tại
    response = requests.get(url, headers=headers)
    sha = None

    if response.status_code == 200:
        sha = response.json()["sha"]

    # data gửi lên
    data = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch
    }

    if sha:
        data["sha"] = sha  # overwrite

    res = requests.put(url, json=data, headers=headers)

    return res.json()