import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tools import list_files, read_file, search_code


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the project, ignoring unsafe/generated folders.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search the codebase for a keyword or phrase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Short code search term, such as login, auth, route, task, database, or component.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a specific file from the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative file path inside the project.",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
]


def load_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_system_prompt() -> str:
    system_prompt = load_prompt("prompts/system.md")
    workflow_prompt = load_prompt("prompts/workflow.md")
    return system_prompt + "\n\n" + workflow_prompt


def create_project_summary(project_path: str) -> str:
    files = list_files(project_path)
    file_list = "\n".join(f"- {file}" for file in files[:200])

    return f"""
Project path: {project_path}

Files:
{file_list}
"""


def run_tool(tool_name: str, arguments: dict, project_path: str):
    if tool_name == "list_files":
        return list_files(project_path)[:300]

    if tool_name == "search_code":
        query = arguments["query"]
        return search_code(project_path, query)[:50]

    if tool_name == "read_file":
        file_path = arguments["file_path"]
        content = read_file(project_path, file_path)
        return content[:8000]

    raise ValueError(f"Unknown tool: {tool_name}")


def ask_agent(messages: list[dict], project_path: str) -> str:
    for _ in range(6):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content or ""

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            result = run_tool(tool_name, arguments, project_path)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "I used the maximum number of tool steps and could not finish confidently."

def main():
    project_path = input("Enter project path: ").strip()

    system_prompt = build_system_prompt()
    project_summary = create_project_summary(project_path)

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": f"Here is the initial project map:\n\n{project_summary}",
        },
    ]

    print("\nRepoLens is ready. Ask about this codebase.")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        messages.append({
            "role": "user",
            "content": question,
        })

        answer = ask_agent(messages, project_path)

        print(f"\nRepoLens: {answer}\n")


if __name__ == "__main__":
    main()
