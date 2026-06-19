from agents.runtime.chat_client import SKILLS, chat_client
from agents.runtime.make_agent import make_agent

translator = make_agent(
    name="translator",
    description="Translates the finished newsletter into a target language for storage.",
    client=chat_client("translator"),
    instructions=(
        "You are a translator. You receive a TARGET LANGUAGE and a numbered list of newsletter snippets. "
        "Consult the **translation** skill for tone and fidelity rules. Translate each numbered snippet into the "
        "target language and return exactly one translated line per input number, in the same order, each prefixed "
        "with the same number and a period. Do not add, drop, merge, reorder, or renumber lines. Write nothing else."
    ),
    context_providers=[SKILLS],
)
