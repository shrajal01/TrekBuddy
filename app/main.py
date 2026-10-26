import asyncio
import os
import logging

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
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
    "https://trekbuddy-26.netlify.app/",
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


@app.post("/api/chat")
async def chat(
    message: str = Body("", media_type="text/plain")
):
    cleaned_message = message.strip()
    if not cleaned_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    await history_lock.acquire()
    try:
        history.append({"role": "user", "content": cleaned_message})

        stream = await client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=list(history),
            store=False,
            stream=True,
        )
    except Exception:
        # If initialization fails, remove the unanswered user message and release lock
        if history and history[-1]["role"] == "user" and history[-1]["content"] == cleaned_message:
            history.pop()
        history_lock.release()
        logger.exception("Failed to initialize chat stream")
        raise HTTPException(
            status_code=502,
            detail="Unable to process your message.",
        )

    async def stream_generator():
        accumulated_chunks: list[str] = []
        completed_successfully = False
        try:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if delta:
                        accumulated_chunks.append(delta)
                        yield delta
                elif event.type == "error":
                    logger.error("OpenAI error event during streaming: %s", event)
                    raise RuntimeError("Error event from OpenAI streaming")

            full_response = "".join(accumulated_chunks).strip()
            if not full_response:
                raise RuntimeError("Empty response received from model")

            history.append({"role": "assistant", "content": full_response})
            completed_successfully = True

        except BaseException as exc:
            logger.exception("Chat streaming interrupted: %s", exc)
            if not completed_successfully and history and history[-1]["role"] == "user" and history[-1]["content"] == cleaned_message:
                history.pop()
            raise
        finally:
            try:
                await stream.close()
            except Exception:
                pass
            history_lock.release()

    return StreamingResponse(
        stream_generator(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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
