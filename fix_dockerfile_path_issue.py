import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def get_github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def fetch_file_content(org, repo, branch, file_path, token):
    url = f"https://api.github.com/repos/{org}/{repo}/contents/{file_path}"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers, params={"ref": branch})

    if response.status_code != 200:
        print(f"Error fetching file: {response.json().get('message', 'Unknown error')}")
        return None, None

    file_data = response.json()
    content = base64.b64decode(file_data["content"]).decode("utf-8")
    return content, file_data["sha"]

def update_file_in_github(org, repo, branch, file_path, updated_content, sha, commit_message, token):
    url = f"https://api.github.com/repos/{org}/{repo}/contents/{file_path}"
    headers = get_github_headers(token)

    payload = {
        "message": commit_message,
        "content": base64.b64encode(updated_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": branch
    }

    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"File updated successfully: {response.json().get('commit', {}).get('html_url')}")
    else:
        print(f"Error updating file: {response.json().get('message', 'Unknown error')}")

def find_dockerfile_path(org, repo, branch, token):
    url = f"https://api.github.com/repos/{org}/{repo}/git/trees/{branch}?recursive=1"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching repository tree: {response.json().get('message', 'Unknown error')}")
        return None

    tree = response.json().get("tree", [])
    for item in tree:
        if item["path"].lower().endswith("dockerfile"):
            return item["path"]
    print("Dockerfile not found in the repository.")
    return None

def process_docker_build_commands(content, dockerfile_path):
    updated_content = ""
    dockerfile_dir = "/".join(dockerfile_path.split("/")[:-1])

    for line in content.splitlines():
        if "docker build" in line and "-t" in line:
            parts = line.split(" ")
            try:
                t_index = parts.index("-t")
                updated_line = " ".join(parts[:t_index + 2]) + f" {dockerfile_dir}"
                updated_content += updated_line + "\n"
                updated_content += f"# Dockerfile path: {dockerfile_path}\n"
            except ValueError:
                updated_content += line + "\n"
        else:
            updated_content += line + "\n"
    return updated_content

def fix_dockerfile_path(org, repo, branch, file_path, token):
    """Fix docker build paths in a GitHub repo workflow file and update it."""
    dockerfile_path = find_dockerfile_path(org, repo, branch, token)
    if not dockerfile_path:
        return None, None, None

    file_content, sha = fetch_file_content(org, repo, branch, file_path, token)
    if not file_content:
        return None, None, None

    updated_content = process_docker_build_commands(file_content, dockerfile_path)
    return updated_content, sha, dockerfile_path
