import os
from collections.abc import Coroutine
from typing import Any, Protocol

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-6-luna"


class Summarizer(Protocol):
    def __call__(self, ticket: str) -> Coroutine[Any, Any, str]: ...


async def summarize_ticket(
    ticket: str,
    *,
    client: AsyncOpenAI | None = None,
    model: str | None = None,
) -> str:
    openai_client = client or AsyncOpenAI()
    response = await openai_client.responses.create(
        model=model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        input=f"Summarize this support ticket in 2 lines : \n\n{ticket}",
        store=False,
    )

    if not response.output_text:
        raise RuntimeError("OpenAI returned an empty summary")

    return response.output_text