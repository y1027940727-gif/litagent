import json
import sys
from .agent import Agent
from .llm import Gemini


def main():
    q = " ".join(sys.argv[1:]) or input("Question: ")
    r = Agent(Gemini()).run(q)
    print(r.answer, "\n")
    print(json.dumps(r.check, indent=2, ensure_ascii=False))
    print("Retrieved:", ", ".join(r.retrieved_ids))


if __name__ == "__main__":
    main()
