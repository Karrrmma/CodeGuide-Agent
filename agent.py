import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from tools import list_files, read_file, search_code

from collections import Counter

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def pick_relevant_files(search_results: list[dict], limit: int = 5) -> list[str]:
    file_counts = Counter(result["file"] for result in search_results)

    return [
        file
        for file, count in file_counts.most_common(limit)
    ]
def read_relevant_files(project_path: str, files: list[str]) -> str:
    context = ""

    for file in files:
        try:
            content = read_file(project_path, file)
        except Exception as error:
            context += f"\n\n## {file}\nCould not read file: {error}\n"
            continue

        context += f"\n\n## {file}\n"
        context += "```text\n"
        context += content[:8000]
        context += "\n```"

    return context


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


def ask_model(messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
    )

    return response.choices[0].message.content

def search_multiple_terms(project_path: str, terms: list[str]) -> list[dict]:
    all_results = []
    seen = set()

    for term in terms:
        results = search_code(project_path, term)

        for result in results:
            key = (result["file"], result["line"], result["text"])

            if key in seen:
                continue

            seen.add(key)

            all_results.append({
                "term": term,
                "file": result["file"],
                "line": result["line"],
                "text": result["text"],
            })

    return all_results


def plan_search_terms(question: str) -> list[str]:
    messages = [
        {
            "role": "system",
            "content": """
You turn codebase questions into useful code search keywords.

Return only a JSON array of short search terms.

Good examples:
Question: Where is login handled?
Answer: ["login", "auth", "signin", "session", "token", "password"]

Question: How does the app connect to the database?
Answer: ["database", "db", "connection", "connect", "DATABASE_URL", "prisma", "sql"]

Question: Where are API routes defined?
Answer: ["route", "router", "api", "endpoint", "controller"]

Rules:
- Return only JSON.
- Use 3 to 8 search terms.
- Prefer words likely to appear in code.
- Include common synonyms.
""",
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
    )

    text = response.choices[0].message.content

    try:
        terms = json.loads(text)
    except json.JSONDecodeError:
        terms = [question]

    return terms


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
        search_terms = plan_search_terms(question)
        search_results = search_multiple_terms(project_path, search_terms)
        relevant_files = pick_relevant_files(search_results)
        file_context = read_relevant_files(project_path, relevant_files)

        context = f"Search terms used: {search_terms}\n\n"

        if search_results:
            context += "Search results:\n"
            for result in search_results[:30]:
                context += (
                    f"- Search term: {result['term']} | "
                    f"{result['file']}:{result['line']} "
                    f"{result['text']}\n"
                )

            context += "\n\nInspected files:\n"
            for file in relevant_files:
                context += f"- {file}\n"

            context += "\n\nFile contents inspected:\n"
            context += file_context
        else:
            context += "No search results found. Answer honestly and suggest better search terms.\n"

        messages.append({
            "role": "user",
            "content": f"""
User question:
{question}

Relevant code search results:
{context}

Answer the user using the RepoLens workflow.
""",
        })

        answer = ask_model(messages)

        messages.append({
    "role": "user",
    "content": f"""
User question:
{question}

RepoLens inspected the following context:
{context}

Answer the user using only the inspected context. Cite file paths. If the context is not enough, say what should be inspected next.
""",
})


        print(f"\nRepoLens: {answer}\n")


if __name__ == "__main__":
    main()
