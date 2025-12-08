"""
Operations chatbot endpoint using Amazon Bedrock Knowledge Bases (RAG).

This router provides a single `/ops/ask` endpoint that accepts an ops query
and attempts to use Bedrock's retrieve-and-generate capability if enabled.
If Bedrock is not configured or not available, the endpoint can fallback to
OpenAI if `OPENAI_API_KEY` is provided.

Note: To use Bedrock Knowledge Bases you must provision a KB and upload
documents to an S3 bucket, then configure the KB to index that S3 location.
This file expects appropriate IAM permissions on the instance or role.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import boto3
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


class OpsQuery(BaseModel):
    query: str
    knowledge_base_id: Optional[str] = None
    max_tokens: int = 512


def call_bedrock_retrieve_and_generate(kb_id: str, query: str, max_tokens: int = 512) -> Dict[str, Any]:
    """Call Bedrock retrieve-and-generate style API for a Knowledge Base.

    This uses boto3 and expects Bedrock agent APIs to be available in the
    environment. The exact method names and parameters may vary by AWS SDK
    version; adjust as needed for your environment.
    """
    # Try bedrock-agent-runtime client (some SDKs expose the agent runtime)
    try:
        client = boto3.client("bedrock-agent-runtime")
    except Exception:
        # Fallback to bedrock-runtime (depending on boto3 version/environment)
        client = boto3.client("bedrock-runtime")

    payload = {
        "input": {"text": query},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {"knowledgeBaseId": kb_id},
        },
        "outputConfig": {"maxTokens": max_tokens},
    }

    # Use a best-effort call; SDKs may require different param names.
    try:
        resp = client.retrieve_and_generate(**payload)
        return resp
    except Exception as e:
        logger.exception("Bedrock retrieve_and_generate failed")
        raise


def call_openai_chat(query: str, max_tokens: int = 512) -> Dict[str, Any]:
    import openai

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set for fallback generation")
    openai.api_key = key
    resp = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": query}],
        max_tokens=max_tokens,
    )
    return resp


@router.post("/ops/ask")
async def ops_ask(req: OpsQuery):
    """Answer an operations question using Bedrock KB or fallback to OpenAI.

    Request body:
    {
      "query": "Why did ASG scale out at 3PM?",
      "knowledge_base_id": "kb-xxxxx"  # optional if configured as default
    }
    """
    kb_id = req.knowledge_base_id or os.getenv("BEDROCK_KB_ID")
    # Prefer Bedrock if configured
    if kb_id and os.getenv("USE_BEDROCK", "true").lower() in ("1", "true", "yes"):
        try:
            result = call_bedrock_retrieve_and_generate(kb_id, req.query, req.max_tokens)
            return {"provider": "bedrock", "result": result}
        except Exception as e:
            logger.warning("Bedrock call failed, falling back if available: %s", str(e))

    # Fallback to OpenAI if available
    if os.getenv("OPENAI_API_KEY"):
        try:
            resp = call_openai_chat(req.query, req.max_tokens)
            return {"provider": "openai", "result": resp}
        except Exception:
            logger.exception("OpenAI fallback failed")

    raise HTTPException(status_code=503, detail="No generation backend available (Bedrock or OpenAI)")
