"""Phase-1 verification agent. Calls the LLM and bumps a counter."""

from datetime import datetime, timezone

from auto_project import llm, state

NAME = "hello"


def run() -> None:
    count = state.get(NAME, "count", 0) + 1
    response = llm.call(
        f"Greeting #{count}. Reply with one short, original sentence — no preamble.",
        system="You are a concise greeter. Never repeat the same line twice.",
    )
    state.set(NAME, "count", count)
    state.set(
        NAME,
        "last",
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "count": count,
            "response": response.strip(),
        },
    )
    print(f"[{NAME}] #{count}: {response.strip()}")


if __name__ == "__main__":
    run()
