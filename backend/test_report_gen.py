"""
Quick diagnostic: run this directly to see what the LLM returns for report generation.
Usage: python test_report_gen.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

from services.pipeline import VoicePipeline
from prompts.system_prompts import REPORT_GENERATION_PROMPT
from prompts.template_engine import render
from config import COMPANY_NAME, LLM_TEMPERATURE, REPORT_MAX_TOKENS, get_model


async def main():
    topic = "machine learning"
    page_count = 3
    output_format = "PDF"

    gen_prompt = render(
        REPORT_GENERATION_PROMPT,
        {
            "company": COMPANY_NAME,
            "topic": topic,
            "page_count": str(page_count),
            "output_format": output_format,
            "report_title": "Machine Learning Overview",
            "memory_context": f"[CONFIRMED REPORT SLOTS]\n  topic: {topic}\n  page_count: {page_count}\n  output_format: {output_format}",
        },
    )

    print(f"[TEST] model={get_model()} max_tokens={REPORT_MAX_TOKENS}")
    print(f"[TEST] prompt_length={len(gen_prompt)} chars")
    print("-" * 60)

    pipeline = VoicePipeline()

    # Patch to inspect the raw response before parsing
    original_execute = pipeline.execute
    async def traced_execute(**kwargs):
        from openai import AsyncOpenAI
        from config import get_groq_api_key, GROQ_BASE_URL
        client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
        msgs = VoicePipeline._build_messages(kwargs['system_prompt'], kwargs['history'], kwargs['user_input'])
        resp = await client.chat.completions.create(
            model=kwargs['model'], messages=msgs,
            temperature=kwargs['temperature'], max_tokens=kwargs['max_tokens']
        )
        choice = resp.choices[0]
        raw = choice.message.content.strip()
        print(f"[TRACE] finish_reason={choice.finish_reason}")
        print(f"[TRACE] raw_length={len(raw)}")
        print(f"[TRACE] raw_tail={raw[-200:]}")
        return VoicePipeline._parse_llm_output(raw)

    result = await traced_execute(
        system_prompt=gen_prompt,
        model=get_model(),
        temperature=LLM_TEMPERATURE,
        max_tokens=REPORT_MAX_TOKENS,
        history=[],
        user_input=f"Generate a {page_count}-page {output_format} report on: {topic}",
    )

    print("[TEST] keys returned:", list(result.keys()))
    sections = result.get("sections") or []
    print(f"[TEST] sections count: {len(sections)}")
    if sections:
        print("[TEST] first section heading:", sections[0].get("heading"))
        print("[TEST] SUCCESS - report generation works")
    else:
        print("[TEST] FAILED - no sections in output")
        print("[TEST] full result:")
        print(json.dumps(result, indent=2)[:2000])


asyncio.run(main())
