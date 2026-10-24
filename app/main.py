import asyncio
import os
import logging

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are TrekBuddy, an expert Indian Trek Guide chatbot.

Your role is to assist users with questions about Indian treks, including:
- Trek difficulty levels, elevation profile, and physical fitness preparation
- Estimated budgets and cost breakdown (permits, guides, equipment, stay, food, transport)
- Ideal trek duration and day-by-day itineraries
- Best season, ideal months, and weather windows to visit
- Comprehensive packing lists and essential gear (layers, footwear, first aid, mountain safety gear)
- Trek safety protocols, AMS (Acute Mountain Sickness) prevention, acclimatization, and emergency precautions

Important instructions:
- Provide warm, well-structured, helpful, and beginner-friendly advice.
- Do not invent live weather, current trail conditions, or real-time availability. Explicitly remind trekkers to check with local forest checkpoints, district authorities, or certified trek organizers before starting.
- Focus on treks across the Indian Himalayas, Western Ghats, Sahyadris, and other Indian ranges.
"""

app = FastAPI(title="TrekBuddy - Your Indian Trek Guide API")

origins = [
    "https://trekbuddy-26.netlify.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI()
model = os.getenv("OPENAI_MODEL", "gpt-6-luna")

history: list[dict[str, str]] = []
history_lock = asyncio.Lock()


class GenerateRequest(BaseModel):
    model: str
    input: str


@app.post("/api/chat", response_class=PlainTextResponse)
async def chat(
    message: str = Body(..., media_type="text/plain")
) -> str:
    async with history_lock:
        history.append({"role": "user", "content": message})

        try:
            response = await client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=history,
                store=False,
            )

            answer = response.output_text

            if not answer:
                raise RuntimeError("Empty response from model")

            history.append(
                {"role": "assistant", "content": answer}
            )
            return answer

        except Exception:
            # Remove the unanswered user message if the request fails.
            history.pop()
            logger.exception("Chat request failed")
            raise HTTPException(
                status_code=502,
                detail="Unable to process your message.",
            )


@app.post("/api/generate")
async def generate(payload: GenerateRequest):
    try:
        response = await client.responses.create(
            model=payload.model,
            input=payload.input,
            store=False,
        )

        usage = response.usage

        return {
            "model": response.model,
            "output": response.output_text,
            "usage": {
                "input_tokens": (
                    usage.input_tokens if usage else None
                ),
                "output_tokens": (
                    usage.output_tokens if usage else None
                ),
                "total_tokens": (
                    usage.total_tokens if usage else None
                ),
            },
        }

    except Exception:
        logger.exception("LLM generation failed")
        raise HTTPException(
            status_code=502,
            detail="LLM generation failed. Check server logs.",
        )


@app.delete("/api")
async def clear_chat() -> Response:
    async with history_lock:
        history.clear()

    return Response(status_code=200)
