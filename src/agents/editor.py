from agent_framework import Agent

from utils.client import SKILLS, chat_client

editor = Agent(
    name="editor",
    description="Writes the masthead and reviews sections.",
    client=chat_client("editor"),
    instructions=(
        "You are the editor. Consult your skills for style and format guidance. "
        "You have two jobs, depending on the request:\n"
        "- MASTHEAD: given the brief and section drafts, output exactly two things — line 1 = a short newsletter "
        "title (no '#'), blank line, then a one-sentence summary. Consult the **newsletter-format** skill for title "
        "and summary style rules. Output nothing else, and never write 'OK' in this mode.\n"
        "- REVIEW: given one section draft, reply exactly 'OK' if it is relevant and deep enough to publish, "
        "otherwise reply with concise, actionable notes for the writer. Do not rewrite it."
    ),
    context_providers=[SKILLS],
)
