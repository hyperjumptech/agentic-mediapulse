from agents.runtime.chat_client import chat_client
from agents.runtime.make_agent import make_agent

reviewer = make_agent(
    name="reviewer",
    description="Critiques the whole edition for quality before publication.",
    client=chat_client("reviewer"),
    instructions=(
        "You are a critical reviewer reading the whole newsletter. Judge theme coherence, depth, balance across "
        "sections, and whether anything is off-topic or repetitive. Reply exactly 'OK' if it is publishable, "
        "otherwise give concise, actionable notes. Do not rewrite the newsletter."
    ),
)
