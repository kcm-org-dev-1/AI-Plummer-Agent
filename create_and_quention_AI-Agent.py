import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, FilePurpose
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fix_dockerfile_path_issue import fix_dockerfile_path, update_file_in_github

load_dotenv()

# Environment variables
org = os.getenv("OWNER")
repo = os.getenv("REPO")
token = os.getenv("TOKEN")
branch = os.getenv("BRANCH") #"task/main/Add_post_run"
workflow_file_path = ".github/workflows/actions-pipeline.yml"
project_conn_str = os.getenv("PROJECT_CONNECTION_STRING")

# Initialize Azure AI Project Client
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(), conn_str=project_conn_str
)

def upload_file(file_path):
    file = project_client.agents.upload_file_and_poll(file_path=file_path, purpose=FilePurpose.AGENTS)
    print(f"Uploaded file, file ID: {file.id}")
    return file

def create_vector_store(file_id):
    vector_store = project_client.agents.create_vector_store_and_poll(file_ids=[file_id], name="my_vectorstore")
    print(f"Created vector store, vector store ID: {vector_store.id}")
    return vector_store

def create_agent(vector_store):
    file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="my-agent",
        instructions=(
            "You are an expert agent that analyzes pipeline logs and repository files to identify the root cause of errors. "
            "Your task is to provide the exact issue causing the error and suggest actionable steps to resolve it. "
            "Only use information from the provided files to answer."
        ),
        tools=file_search_tool.definitions,
        tool_resources=file_search_tool.resources,
    )
    print(f"Created agent, agent ID: {agent.id}")
    return agent

def create_thread():
    thread = project_client.agents.create_thread()
    print(f"Created thread, thread ID: {thread.id}")
    return thread

def create_message(thread_id):
    message = project_client.agents.create_message(
        thread_id=thread_id,
        role="user",
        content="What is the ERROR about? and How can we fix it?",
        attachments=[]
    )
    print(f"Created message, message ID: {message.id}")
    return message

def process_run(thread_id, agent_id):
    run = project_client.agents.create_and_process_run(thread_id=thread_id, agent_id=agent_id)
    print(f"Created run, run ID: {run.id}")
    return run

def retrieve_and_fix_if_needed(thread_id):
    messages = project_client.agents.list_messages(thread_id=thread_id)
    sorted_messages = sorted(messages["data"], key=lambda x: x["created_at"])

    print("\n--- Thread Messages (sorted) ---")
    for msg in sorted_messages:
        role = msg["role"].upper()
        content = msg.get("content", [])
        text_value = content[0]["text"]["value"] if content and content[0]["type"] == "text" else ""

        print(f"{role}: {text_value}")

        # Check for Dockerfile path issue
        if role == "ASSISTANT" and "dockerfile" in text_value.lower() and "path" in text_value.lower():
            print("\n⚠️ Detected Dockerfile path issue. Attempting to fix...")

            updated_content, sha, dockerfile_path = fix_dockerfile_path(org, repo, branch, workflow_file_path, token)
            if updated_content and sha:
                commit_message = (
                    f"Fix: Updated Docker build paths using AI detection. Dockerfile: {dockerfile_path}"
                )
                update_file_in_github(org, repo, branch, workflow_file_path, updated_content, sha, commit_message, token)
            else:
                print("❌ Could not generate updated content.")

def clean_up(vector_store, agent):
    project_client.agents.delete_vector_store(vector_store.id)
    print("Deleted vector store")
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")

if __name__ == "__main__":
    with project_client:
        # Step 1: Upload logs
        file = upload_file(file_path="combined_logs.txt")

        # Step 2: Create vector store
        vector_store = create_vector_store(file_id=file.id)

        # Step 3: Create agent
        agent = create_agent(vector_store=vector_store)

        # Step 4: Create thread
        thread = create_thread()

        # Step 5: Create user message
        create_message(thread_id=thread.id)

        # Step 6: Process run
        process_run(thread_id=thread.id, agent_id=agent.id)

        # Step 7: Check messages and possibly fix Dockerfile path issue
        retrieve_and_fix_if_needed(thread_id=thread.id)

        # Step 8: Clean up
        clean_up(vector_store=vector_store, agent=agent)
