import os
import requests
import zipfile
from dotenv import load_dotenv

load_dotenv()

def get_latest_logs():
    # Read environment variables
    owner = os.getenv("OWNER")
    repo = os.getenv("REPO")
    token = os.getenv("TOKEN")

    if not owner or not repo or not token:
        print("Error: OWNER, REPO, and TOKEN environment variables must be set.")
        return

    # GitHub API base URL
    BASE_URL = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"

    # Headers for authentication
    HEADERS = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get the latest workflow runs
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status()
    runs = response.json()

    if "workflow_runs" not in runs or len(runs["workflow_runs"]) == 0:
        print("No workflow runs found.")
        return

    # Find the latest workflow run
    latest_run = runs["workflow_runs"][0]
    log_url = latest_run["logs_url"]

    # Get the logs URL
    log_response = requests.get(log_url, headers=HEADERS)
    log_response.raise_for_status()

    # Write the logs to a ZIP file
    log_file = "latest_workflow_logs.zip"
    with open(log_file, "wb") as file:
        file.write(log_response.content)

    print(f"Logs downloaded successfully and saved to {log_file}")

    # Extract and combine logs into a single .txt file
    extract_and_combine_logs(log_file)

def extract_and_combine_logs(zip_file):
    combined_log_file = "combined_logs.txt"
    logs_dir = "logs"

    # Extract the ZIP file
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(logs_dir)

    # Combine all log files into one
    with open(combined_log_file, "w", encoding="utf-8") as outfile:
        for root, _, files in os.walk(logs_dir):
            for file in files:
                log_path = os.path.join(root, file)
                with open(log_path, "r", encoding="utf-8") as infile:
                    outfile.write(f"--- Logs from {file} ---\n")
                    outfile.write(infile.read())
                    outfile.write("\n\n")

    print(f"All logs combined into {combined_log_file}")

    # Clean up: Delete the extracted logs directory and the ZIP file
    for root, dirs, files in os.walk(logs_dir, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    os.rmdir(logs_dir)  # Remove the logs directory itself
    os.remove(zip_file)  # Remove the ZIP file

    print(f"Cleaned up intermediate files. Only {combined_log_file} remains.")

    # Display the content of the combined log file
    print("\n--- Combined Logs Content ---\n")
    with open(combined_log_file, "r", encoding="utf-8") as file:
        print(file.read())

if __name__ == "__main__":
    get_latest_logs()