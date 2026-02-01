"""
Bedrock Integration: Agents + Knowledge Bases
Routes customer/ops queries to respective Bedrock Agents with KB access
"""
import os
import logging
import re
import boto3
import uuid
from typing import Optional, Dict, Any, Tuple

from app.ops_realtime import (
    collect_infra_snapshot,
    collect_dynamodb_metrics,
    default_alb_arn,
    default_asg_name,
    default_region,
    default_target_group_arn,
    plan_asg_instance_refresh,
    execute_asg_instance_refresh,
    plan_ddb_capacity_increase,
    execute_ddb_capacity_increase,
    persist_snapshot_to_logs,
    check_api_health,
    check_api_pagination,
)

logger = logging.getLogger(__name__)

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
)

# Agent IDs from environment or defaults
CUSTOMER_AGENT_ID = os.getenv("CUSTOMER_AGENT_ID", "LJCIO6MTHB")
OPS_AGENT_ID = os.getenv("OPS_AGENT_ID", "CGWF5H93V2")

# Customer agent alias (Working-alias-1412)
CUSTOMER_AGENT_ALIAS_ID = os.getenv("CUSTOMER_AGENT_ALIAS_ID", "IQQLSGF6X8")

# Ops agent alias (Working-alias-ops-1412)
OPS_AGENT_ALIAS_ID = os.getenv("OPS_AGENT_ALIAS_ID", "WX8RSD82ZC")

# Knowledge Base IDs from environment or defaults (fallback)
CUSTOMER_KB_ID = os.getenv("CUSTOMER_KB_ID", "SZAIJFW1GL")
OPS_KB_ID = os.getenv("OPS_KB_ID", "DYZ9HTPH0S")

# Model ID for retrieval (not ARN)
MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "deepseek.r1-v1:0",  # DeepSeek R1 - use inference profile
)

# AWS Account ID for inference profile ARN
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "171308902397")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Guardrail ID for PII/sensitive data protection
GUARDRAIL_ID = os.getenv("GUARDRAIL_ID", "5xdt7tfq11gx")  # PII protection guardrail


def query_knowledge_base(
    kb_id: str, query: str, max_results: int = 5
) -> Dict[str, Any]:
    """
    Query a Bedrock Knowledge Base and return RAG response

    Args:
        kb_id: Knowledge Base ID
        query: User's question
        max_results: Number of retrieved documents to return

    Returns:
        dict with 'answer', 'sources', and 'retrieved_docs'
    """
    try:
        # Use inference profile ARN for DeepSeek R1 (not foundation model ARN)
        inference_profile_arn = f"arn:aws:bedrock:{AWS_REGION}:{AWS_ACCOUNT_ID}:inference-profile/us.{MODEL_ID}"
        
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": inference_profile_arn,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {"numberOfResults": max_results}
                    }
                },
            },
        )

        # Extract answer and sources
        answer = response.get("output", {}).get("text", "")
        citations = response.get("citations", [])

        sources = []
        for citation in citations:
            for ref in citation.get("retrievedReferences", []):
                location = ref.get("location", {})
                s3_location = location.get("s3Location", {})
                sources.append(
                    {
                        "uri": s3_location.get("uri", ""),
                        "snippet": ref.get("content", {}).get("text", "")[:200],
                    }
                )

        return {
            "answer": answer,
            "sources": sources,
            "session_id": response.get("sessionId"),
            "kb_id": kb_id,
        }

    except Exception as e:
        logger.error(f"Error querying KB {kb_id}: {str(e)}")
        raise


def query_customer_kb(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Query customer-facing knowledge base"""
    return query_knowledge_base(CUSTOMER_KB_ID, query, max_results)


def query_ops_kb(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Query ops/admin knowledge base"""
    return query_knowledge_base(OPS_KB_ID, query, max_results)


def invoke_agent(
    agent_id: str, query: str, session_id: Optional[str] = None, alias_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invoke a Bedrock Agent with a user query

    Args:
        agent_id: Agent ID (e.g., LJCIO6MTHB for customer agent)
        query: User's question
        session_id: Optional session ID for multi-turn conversation (generated if None)
        alias_id: Optional agent alias ID (defaults per agent)

    Returns:
        dict with 'answer', 'session_id', and 'agent_id'
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Use agent-specific alias if not provided
    if not alias_id:
        alias_id = CUSTOMER_AGENT_ALIAS_ID if agent_id == CUSTOMER_AGENT_ID else OPS_AGENT_ALIAS_ID

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=query,
        )

        # Parse streaming response - agents return an EventStream object
        answer = ""
        event_stream = response.get("completion")
        
        if event_stream:
            for event in event_stream:
                # Event structure: {'chunk': {'bytes': b'...'}} or {'trace': {...}}
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        # Decode bytes to text
                        chunk_text = chunk["bytes"].decode("utf-8")
                        answer += chunk_text
                        logger.debug(f"Chunk: {chunk_text[:100]}")
                        
                elif "trace" in event:
                    # Trace events contain agent reasoning/actions
                    trace = event.get("trace", {})
                    logger.debug(f"Trace event: {trace.get('type', 'unknown')}")

        logger.info(f"Agent {agent_id} returned {len(answer)} characters")

        return {
            "answer": answer if answer.strip() else f"[Agent {agent_id} processed your query but returned no text. The agent may need clarification or attached Knowledge Bases.]",
            "session_id": session_id,
            "agent_id": agent_id,
        }

    except Exception as e:
        logger.error(f"Error invoking agent {agent_id} (alias {alias_id}): {str(e)}", exc_info=True)
        raise


def invoke_customer_agent(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Invoke customer support agent (handles courses, enrollment, billing)"""
    return invoke_agent(CUSTOMER_AGENT_ID, query, session_id)


def invoke_ops_agent(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Invoke ops agent (handles ALB, ASG, deployments, incident response)
    
    Enhanced with local function calling for:
    - DynamoDB metrics
    - ASG instance refresh planning/execution
    - DynamoDB capacity planning/execution
    - Infrastructure snapshots
    """
    
    region = default_region()
    asg_name = default_asg_name()
    tg_arn = default_target_group_arn()
    alb_arn = default_alb_arn()
    
    # Try to detect intent and call local functions first
    intent, intent_data = _detect_ops_intent(query)
    local_result: Optional[Dict[str, Any]] = None
    
    if intent == "ddb_metrics":
        # Extract table names from query
        table_names = intent_data.get("table_names", [])
        minutes = intent_data.get("minutes", 10)
        if table_names:
            try:
                local_result = collect_dynamodb_metrics(
                    region=region,
                    table_names=table_names,
                    minutes=minutes,
                )
                local_result["_intent"] = "ddb_metrics"
            except Exception as e:
                logger.warning(f"DynamoDB metrics collection failed: {e}")
    
    elif intent == "ddb_capacity":
        table_name = intent_data.get("table_name")
        execute = intent_data.get("execute", False)
        if table_name:
            try:
                if execute:
                    local_result = execute_ddb_capacity_increase(
                        region=region,
                        table_name=table_name,
                        factor=intent_data.get("factor", 1.5),
                        max_increment=intent_data.get("max_increment", 100),
                    )
                else:
                    local_result = plan_ddb_capacity_increase(
                        region=region,
                        table_name=table_name,
                        factor=intent_data.get("factor", 1.5),
                        max_increment=intent_data.get("max_increment", 100),
                    )
                local_result["_intent"] = "ddb_capacity"
            except Exception as e:
                logger.warning(f"DynamoDB capacity operation failed: {e}")
    
    elif intent == "asg_refresh":
        target_asg = intent_data.get("asg_name") or asg_name
        execute = intent_data.get("execute", False)
        if target_asg:
            try:
                if execute:
                    local_result = execute_asg_instance_refresh(
                        region=region,
                        asg_name=target_asg,
                    )
                else:
                    local_result = plan_asg_instance_refresh(
                        region=region,
                        asg_name=target_asg,
                    )
                local_result["_intent"] = "asg_refresh"
            except Exception as e:
                logger.warning(f"ASG instance refresh operation failed: {e}")
    
    elif intent == "infra_snapshot":
        try:
            local_result = collect_infra_snapshot(
                region=region,
                asg_name=asg_name,
                target_group_arn=tg_arn,
                alb_arn=alb_arn,
                include_activity_limit=10,
            )
            local_result["_intent"] = "infra_snapshot"
            
            # Persist if requested
            if intent_data.get("persist"):
                persist_result = persist_snapshot_to_logs(
                    region=region,
                    snapshot=local_result,
                )
                local_result["_persist_result"] = persist_result
        except Exception as e:
            logger.warning(f"Infra snapshot collection failed: {e}")
    
    elif intent == "api_health":
        try:
            base_url = intent_data.get("base_url") or os.getenv("API_BASE_URL", "http://localhost:8000")
            endpoints = intent_data.get("endpoints")
            local_result = check_api_health(base_url=base_url, endpoints=endpoints)
            local_result["_intent"] = "api_health"
        except Exception as e:
            logger.warning(f"API health check failed: {e}")
    
    elif intent == "api_pagination":
        try:
            base_url = intent_data.get("base_url") or os.getenv("API_BASE_URL", "http://localhost:8000")
            endpoint = intent_data.get("endpoint", "/api/courses")
            local_result = check_api_pagination(base_url=base_url, endpoint=endpoint)
            local_result["_intent"] = "api_pagination"
        except Exception as e:
            logger.warning(f"API pagination check failed: {e}")
    
    # Check if user wants AI analysis/recommendations (not just raw data)
    needs_ai_analysis = _needs_agent_analysis(query)
    
    # If we got a local result and user wants AI analysis, call agent with data as context
    if local_result and needs_ai_analysis:
        return _invoke_agent_with_local_data(query, local_result, session_id)
    
    # If we got a local result but no AI analysis needed, format it nicely
    if local_result:
        return _format_ops_local_result(query, local_result, session_id)
    
    # Fallback to Bedrock Agent with enriched context
    enable_realtime = os.getenv("OPS_REALTIME_CONTEXT", "true").strip().lower() in {"1", "true", "yes"}
    if not enable_realtime:
        return invoke_agent(OPS_AGENT_ID, query, session_id)

    context: Optional[str] = None
    try:
        snapshot = collect_infra_snapshot(
            region=region,
            asg_name=asg_name,
            target_group_arn=tg_arn,
            alb_arn=alb_arn,
            include_activity_limit=10,
        )
        max_bytes = int(os.getenv("OPS_REALTIME_MAX_BYTES", "6000"))
        raw = (
            "Realtime AWS infra snapshot (best-effort; may contain errors in 'errors' field).\n"
            "Use this as ground truth for current ASG/ALB/TG state; if missing/errored, say so.\n"
            + "SNAPSHOT_JSON="
            + __import__("json").dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
        )
        context = raw[:max_bytes]
    except Exception as e:
        logger.warning("Failed to collect ops realtime snapshot: %s", str(e))

    if context:
        enriched_query = f"{context}\n\nUSER_QUESTION: {query}"
        return invoke_agent(OPS_AGENT_ID, enriched_query, session_id)

    return invoke_agent(OPS_AGENT_ID, query, session_id)


def _needs_agent_analysis(query: str) -> bool:
    """Check if user wants AI analysis/recommendations, not just raw data.
    
    Returns True if query contains analysis-related keywords.
    """
    q = query.lower()
    
    analysis_patterns = [
        # Vietnamese
        r"(cải thiện|đề xuất|recommend|khuyến nghị|tư vấn|gợi ý)",
        r"(đánh giá|phân tích|analyze|analysis|review)",
        r"(tối ưu|optimize|optimization|nên làm gì)",
        r"(vấn đề|problem|issue|lỗi gì|có gì sai)",
        r"(cho.*biết.*gì|what.*should|có nên|should i)",
        r"(giải thích|explain|tại sao|why|như thế nào|how)",
        r"(ý kiến|opinion|nhận xét|comment|feedback)",
        r"(best practice|practice|chuẩn|standard)",
        r"(cảnh báo|warning|alert|risk|rủi ro)",
        r"(hướng dẫn|guide|help|giúp)",
    ]
    
    for pattern in analysis_patterns:
        if re.search(pattern, q):
            return True
    
    return False


def _invoke_agent_with_local_data(
    query: str, 
    local_result: Dict[str, Any], 
    session_id: Optional[str]
) -> Dict[str, Any]:
    """Invoke Bedrock Agent with local data as context for AI analysis."""
    import json
    
    intent = local_result.get("_intent", "unknown")
    
    # Build context from local result
    context_parts = [
        "Dữ liệu real-time đã thu thập từ AWS (dùng làm ground truth):",
        f"DATA_TYPE: {intent}",
        f"DATA_JSON={json.dumps(local_result, ensure_ascii=False, default=str)}"
    ]
    
    # Add specific prompts based on intent
    if intent == "infra_snapshot":
        context_parts.append(
            "\nHãy phân tích infrastructure snapshot này và đưa ra:"
            "\n- Đánh giá tình trạng hiện tại (healthy/unhealthy)"
            "\n- Các vấn đề tiềm ẩn (nếu có)"
            "\n- Đề xuất cải thiện cụ thể"
            "\n- Best practices nên áp dụng"
        )
    elif intent == "ddb_metrics":
        context_parts.append(
            "\nHãy phân tích DynamoDB metrics này và đưa ra:"
            "\n- Đánh giá performance hiện tại"
            "\n- Có throttling hay không"
            "\n- Đề xuất về capacity/pricing model"
            "\n- Cảnh báo nếu có vấn đề"
        )
    elif intent == "asg_refresh":
        context_parts.append(
            "\nHãy đánh giá kế hoạch instance refresh này:"
            "\n- Rủi ro tiềm ẩn"
            "\n- Thời điểm tốt để thực hiện"
            "\n- Các bước chuẩn bị cần thiết"
        )
    elif intent == "ddb_capacity":
        context_parts.append(
            "\nHãy đánh giá kế hoạch tăng capacity này:"
            "\n- Chi phí ước tính"
            "\n- Có hợp lý không"
            "\n- Các phương án thay thế"
        )
    elif intent == "api_health":
        context_parts.append(
            "\nHãy phân tích API health check này và đưa ra:"
            "\n- Đánh giá tình trạng các endpoints"
            "\n- Response time có chấp nhận được không"
            "\n- Các vấn đề cần chú ý"
            "\n- Đề xuất cải thiện"
        )
    elif intent == "api_pagination":
        context_parts.append(
            "\nHãy phân tích kết quả kiểm tra pagination này:"
            "\n- API có hỗ trợ pagination không"
            "\n- Nếu không, tại sao nên implement"
            "\n- Cách implement pagination hiệu quả"
            "\n- Best practices cho API pagination"
        )
    
    context = "\n".join(context_parts)
    
    # Limit context size
    max_bytes = int(os.getenv("OPS_REALTIME_MAX_BYTES", "8000"))
    context = context[:max_bytes]
    
    enriched_query = f"{context}\n\nUSER_QUESTION: {query}"
    
    return invoke_agent(OPS_AGENT_ID, enriched_query, session_id)


def _detect_ops_intent(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Detect user intent from query for local function dispatch.
    
    ⚠️ ARCHITECTURE NOTE:
    This uses regex-based intent detection which has limitations:
    - Must define patterns for every way users might ask
    - Pattern order matters (first match wins)
    - Doesn't scale well
    
    Better approaches for production:
    1. Bedrock Agent Action Groups - define Lambda functions, agent decides which to call
    2. Function Calling (Claude/GPT-4) - LLM chooses tools based on schemas
    3. LLM-based intent classification - use small model to classify intent
    
    Current approach is a quick workaround because Bedrock Agent 
    doesn't have Action Groups configured for these local functions.
    
    Returns:
        (intent_name, intent_data) or (None, {}) if no local intent detected
    """
    q = query.lower()
    data: Dict[str, Any] = {}
    
    # Get DynamoDB tables from environment
    default_ddb_tables = os.getenv("OPS_DDB_TABLES", "").split(",")
    default_ddb_tables = [t.strip() for t in default_ddb_tables if t.strip()]
    
    # Helper to find matching table from partial name
    def find_matching_tables(partial_name: str) -> list:
        """Find tables that match partial name (e.g., 'courses' -> 'course-management-courses-dev')"""
        matches = []
        partial_lower = partial_name.lower()
        for table in default_ddb_tables:
            # Exact match or partial match (table name contains the partial)
            if partial_lower == table.lower() or partial_lower in table.lower():
                matches.append(table)
        return matches
    
    # DynamoDB metrics intent - expanded patterns
    ddb_metrics_patterns = [
        r"(dynamodb|ddb).*(metric|metrics|số liệu|kiểm tra|check|throttl)",
        r"(metric|metrics).*(dynamodb|ddb|bảng|table)",
        r"kiểm tra.*(dynamodb|ddb|bảng)",
        r"(throttle|throttling|check).*(dynamodb|ddb|table|bảng)",
        r"(check|kiểm tra).*(throttl|metric|ddb|dynamodb)",
    ]
    for pattern in ddb_metrics_patterns:
        if re.search(pattern, q):
            # Extract table names - try quoted first, then unquoted
            tables = []
            # Match quoted table names
            quoted_matches = re.findall(r"['\"]([^'\"]+)['\"]", q)
            for m in quoted_matches:
                # Try to find matching table from partial name
                found = find_matching_tables(m)
                if found:
                    tables.extend(found)
                elif "course-management" in m.lower() or "-dev" in m.lower():
                    tables.append(m)
            
            # Match explicit table names (with hyphens like AWS naming)
            if not tables:
                explicit_match = re.findall(r"(?:table|bảng)\s+([a-zA-Z][a-zA-Z0-9-]+)", q, re.IGNORECASE)
                for t in explicit_match:
                    if "-" in t:
                        tables.append(t)
                    else:
                        # Try partial match
                        found = find_matching_tables(t)
                        tables.extend(found)
            
            # Extract minutes
            minutes_match = re.search(r"(\d+)\s*(phút|minute|min)", q)
            minutes = int(minutes_match.group(1)) if minutes_match else 10
            
            # Use default tables from .env if none specified
            data["table_names"] = tables if tables else default_ddb_tables
            data["minutes"] = minutes
            return ("ddb_metrics", data)
    
    # DynamoDB capacity intent
    ddb_capacity_patterns = [
        r"(tăng|increase|scale).*(capacity|dung lượng|rcu|wcu).*(dynamodb|ddb|table|bảng)",
        r"(dynamodb|ddb|table|bảng).*(capacity|dung lượng|rcu|wcu)",
        r"capacity.*(dynamodb|ddb|bảng|table)",
    ]
    for pattern in ddb_capacity_patterns:
        if re.search(pattern, q):
            # Match quoted table names first
            table_match = re.search(r"['\"]([^'\"]+)['\"]", q)
            if table_match:
                data["table_name"] = table_match.group(1)
            else:
                # Match explicit table names with hyphens
                explicit_match = re.search(r"(?:table|bảng)\s+([a-zA-Z][a-zA-Z0-9-]+)", q, re.IGNORECASE)
                if explicit_match and "-" in explicit_match.group(1):
                    data["table_name"] = explicit_match.group(1)
                elif default_ddb_tables:
                    # Default to first table if not specified
                    data["table_name"] = default_ddb_tables[0]
            
            # Check if execution is requested
            data["execute"] = bool(re.search(r"(thực thi|execute|apply|run|chạy)", q))
            
            # Extract factor
            factor_match = re.search(r"(\d+\.?\d*)\s*(lần|times|x)", q)
            if factor_match:
                data["factor"] = float(factor_match.group(1))
            
            return ("ddb_capacity", data)
    
    # ASG instance refresh intent
    asg_refresh_patterns = [
        r"instance\s*refresh",
        r"refresh.*instance",
        r"(rolling|update|cập nhật).*(asg|auto\s*scaling)",
        r"(kế hoạch|plan|lên kế hoạch).*(refresh|rolling)",
    ]
    for pattern in asg_refresh_patterns:
        if re.search(pattern, q):
            # Extract ASG name - only match explicit ASG name patterns
            # Pattern: asg 'name' or asg "name" or "asg name-with-dashes" (must have hyphen or be quoted)
            # First try quoted names
            asg_match = re.search(r"asg\s+['\"]([^'\"]+)['\"]", q, re.IGNORECASE)
            if not asg_match:
                # Then try unquoted names that look like AWS resource names (must contain hyphen)
                asg_match = re.search(r"asg\s+([a-zA-Z][a-zA-Z0-9]*(?:-[a-zA-Z0-9]+)+)", q, re.IGNORECASE)
            
            if asg_match:
                matched_name = asg_match.group(1)
                # Filter out Vietnamese words that might be captured
                vn_stopwords = {"nhưng", "chưa", "thực", "thi", "cho", "và", "của", "trong", "này", "nh", "chu", "th"}
                if matched_name and matched_name.lower() not in vn_stopwords:
                    data["asg_name"] = matched_name
            
            # Check if execution is requested
            data["execute"] = bool(re.search(r"(thực thi|execute|apply|run|chạy|start)", q))
            
            # If "chưa thực thi" or "không thực thi" - don't execute
            if re.search(r"(chưa|không|don'?t|no).*(thực thi|execute)", q):
                data["execute"] = False
            
            return ("asg_refresh", data)
    
    # Infra snapshot intent
    snapshot_patterns = [
        r"(snapshot|tình trạng|status|state).*(infra|infrastructure|cơ sở hạ tầng)",
        r"(infra|infrastructure|cơ sở hạ tầng).*(snapshot|tình trạng|status|state)",
        r"(lấy|get|collect|thu thập).*(snapshot|trạng thái)",
        r"(kiểm tra|check).*(infra|infrastructure|tình trạng|hiện tại)",
        r"(real-?time|theo dõi|monitor).*(asg|alb|target)",
    ]
    for pattern in snapshot_patterns:
        if re.search(pattern, q):
            data["persist"] = bool(re.search(r"(persist|lưu|save|ghi log)", q))
            return ("infra_snapshot", data)
    
    # ⚠️ API pagination MUST be checked BEFORE api_health (more specific pattern first)
    # API pagination check intent
    api_pagination_patterns = [
        r"(phân trang|pagination|paging)",  # Any mention of pagination
        r"(api|endpoint|backend).*(phân trang|pagination|paging)",
        r"(kiểm tra|check).*(phân trang|pagination)",
        r"backend.*(đã|có|chưa).*(phân trang|pagination)",
    ]
    for pattern in api_pagination_patterns:
        if re.search(pattern, q):
            # Extract endpoint if specified
            endpoint_match = re.search(r"(/api/\w+|/\w+)", q)
            if endpoint_match:
                data["endpoint"] = endpoint_match.group(1)
            # Extract base URL if specified
            url_match = re.search(r"(https?://[^\s]+)", q)
            if url_match:
                data["base_url"] = url_match.group(1)
            return ("api_pagination", data)
    
    # API health check intent (more general - check AFTER pagination)
    api_health_patterns = [
        r"(kiểm tra|check|test).*(api|endpoint).*(health|hoạt động)",
        r"(api|endpoint).*(hoạt động|working|healthy|status)",
        r"health.*(check|api|endpoint)",
        r"(check|test).*(api|endpoint)$",  # Generic "check api" without pagination
    ]
    for pattern in api_health_patterns:
        if re.search(pattern, q):
            # Skip if pagination-related words are present (handled above)
            if re.search(r"(phân trang|pagination|paging)", q):
                continue
            # Extract base URL if specified
            url_match = re.search(r"(https?://[^\s]+)", q)
            if url_match:
                data["base_url"] = url_match.group(1)
            return ("api_health", data)
    
    return (None, {})


def _format_ops_local_result(query: str, result: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
    """Format local function result into a nice response."""
    
    import json
    
    intent = result.pop("_intent", "unknown")
    persist_result = result.pop("_persist_result", None)
    
    if intent == "ddb_metrics":
        tables = result.get("tables", {})
        answer_parts = [f"📊 **DynamoDB Metrics** (last {result.get('window_minutes', 5)} minutes)\n"]
        
        for table_name, table_data in tables.items():
            answer_parts.append(f"\n**Table: {table_name}**")
            metrics = table_data.get("metrics", {})
            
            # Key metrics summary
            consumed_read = metrics.get("ConsumedReadCapacityUnits", {})
            consumed_write = metrics.get("ConsumedWriteCapacityUnits", {})
            read_throttle = metrics.get("ReadThrottleEvents", {})
            write_throttle = metrics.get("WriteThrottleEvents", {})
            
            if consumed_read and consumed_read.get("sum") is not None:
                answer_parts.append(f"- Read Consumed: {consumed_read.get('sum', 0):.1f} RCU (avg: {consumed_read.get('average', 0):.1f})")
            if consumed_write and consumed_write.get("sum") is not None:
                answer_parts.append(f"- Write Consumed: {consumed_write.get('sum', 0):.1f} WCU (avg: {consumed_write.get('average', 0):.1f})")
            if read_throttle and read_throttle.get("sum"):
                answer_parts.append(f"- ⚠️ Read Throttles: {read_throttle.get('sum', 0):.0f}")
            if write_throttle and write_throttle.get("sum"):
                answer_parts.append(f"- ⚠️ Write Throttles: {write_throttle.get('sum', 0):.0f}")
            
            billing = table_data.get("billing_mode", "UNKNOWN")
            answer_parts.append(f"- Billing Mode: {billing}")
            
            if table_data.get("provisioned_throughput"):
                pt = table_data["provisioned_throughput"]
                answer_parts.append(f"- Provisioned: {pt.get('read', 'N/A')} RCU / {pt.get('write', 'N/A')} WCU")
        
        answer = "\n".join(answer_parts)
    
    elif intent == "ddb_capacity":
        if result.get("allowed") is False:
            answer = f"❌ **Cannot increase capacity for table `{result.get('table_name')}`**\n"
            answer += f"Reason: {result.get('reason', result.get('error', 'Unknown'))}"
        elif result.get("executed"):
            answer = f"✅ **DynamoDB Capacity Updated for `{result.get('table_name')}`**\n"
            answer += f"- Previous: {result.get('current', {}).get('read', 'N/A')} RCU / {result.get('current', {}).get('write', 'N/A')} WCU\n"
            answer += f"- New: {result.get('proposed', {}).get('read', 'N/A')} RCU / {result.get('proposed', {}).get('write', 'N/A')} WCU"
        else:
            answer = f"📋 **Capacity Increase Plan for `{result.get('table_name')}`**\n"
            answer += f"- Current: {result.get('current', {}).get('read', 'N/A')} RCU / {result.get('current', {}).get('write', 'N/A')} WCU\n"
            answer += f"- Proposed: {result.get('proposed', {}).get('read', 'N/A')} RCU / {result.get('proposed', {}).get('write', 'N/A')} WCU\n"
            answer += f"- Factor: {result.get('factor', 1.5)}x (max increment: {result.get('max_increment', 100)})\n"
            answer += "\n💡 Add 'thực thi' or 'execute' to apply this change."
    
    elif intent == "asg_refresh":
        asg_display = result.get("asg_name") or "(default from env)"
        if result.get("started"):
            answer = f"✅ **Instance Refresh Started for ASG `{result.get('asg_name')}`**\n"
            answer += f"- Refresh ID: {result.get('instance_refresh_id', 'N/A')}\n"
            answer += f"- Strategy: Rolling\n"
            answer += f"- Min Healthy: 90%"
        elif result.get("error"):
            answer = f"❌ **Instance Refresh Failed for ASG `{asg_display}`**\n"
            error_info = result.get("error", {})
            if isinstance(error_info, dict):
                answer += f"Error: {error_info.get('message', 'Unknown error')}"
            else:
                answer += f"Error: {error_info}"
        else:
            plan = result.get("plan", {})
            asg_name = result.get("asg_name")
            if asg_name:
                answer = f"📋 **Instance Refresh Plan for ASG `{asg_name}`**\n"
            else:
                answer = f"📋 **Instance Refresh Plan**\n"
                answer += f"⚠️ No ASG name specified. Set OPS_ASG_NAME env var or specify in query.\n\n"
            answer += f"- Strategy: {plan.get('strategy', 'Rolling')}\n"
            answer += f"- Min Healthy Percentage: {plan.get('preferences', {}).get('MinHealthyPercentage', 90)}%\n"
            answer += f"- Instance Warmup: {plan.get('preferences', {}).get('InstanceWarmup', 60)}s\n"
            answer += "\n💡 Add 'thực thi' or 'execute' to start this refresh."
            answer += "\n💡 Specify ASG: 'instance refresh cho asg my-asg-name'"
    
    elif intent == "infra_snapshot":
        answer_parts = [f"📸 **Infrastructure Snapshot** ({result.get('timestamp', 'N/A')})\n"]
        answer_parts.append(f"Region: `{result.get('region', 'N/A')}`")
        
        inputs = result.get("inputs", {})
        
        # ASG info
        asg = result.get("asg")
        if asg:
            answer_parts.append(f"\n**🖥️ ASG: {asg.get('auto_scaling_group_name', 'N/A')}**")
            answer_parts.append(f"- Desired/Min/Max: {asg.get('desired_capacity', 'N/A')}/{asg.get('min_size', 'N/A')}/{asg.get('max_size', 'N/A')}")
            answer_parts.append(f"- Instance Count: {asg.get('instance_count', 0)}")
            health = asg.get("health_counts", {})
            if health:
                answer_parts.append(f"- Health: {health}")
            lifecycle = asg.get("lifecycle_counts", {})
            if lifecycle:
                answer_parts.append(f"- Lifecycle: {lifecycle}")
        elif not inputs.get("asg_name"):
            answer_parts.append(f"\n⚠️ **ASG:** Not configured (set OPS_ASG_NAME or ASG_NAME env var)")
        
        # Target Group info
        tg = result.get("target_group")
        if tg:
            tg_name = tg.get('target_group_arn', 'N/A').split('/')[-1] if tg.get('target_group_arn') else 'N/A'
            answer_parts.append(f"\n**🎯 Target Group:** {tg_name}")
            counts = tg.get("counts", {})
            answer_parts.append(f"- Target Health: {counts}")
        elif not inputs.get("target_group_arn"):
            answer_parts.append(f"\n⚠️ **Target Group:** Not configured (set OPS_TARGET_GROUP_ARN env var)")
        
        # ALB info
        alb = result.get("alb")
        if alb:
            answer_parts.append(f"\n**⚖️ ALB:** {alb.get('dns_name', 'N/A')}")
            answer_parts.append(f"- State: {alb.get('state', 'N/A')}")
            answer_parts.append(f"- Type: {alb.get('type', 'N/A')} | Scheme: {alb.get('scheme', 'N/A')}")
        elif not inputs.get("alb_arn"):
            answer_parts.append(f"\n⚠️ **ALB:** Not configured (set OPS_ALB_ARN env var)")
        
        # Instance Refresh info
        ir = result.get("instance_refresh")
        if ir:
            answer_parts.append(f"\n**Latest Instance Refresh:**")
            answer_parts.append(f"- Status: {ir.get('status', 'N/A')}")
            answer_parts.append(f"- Progress: {ir.get('percentage_complete', 'N/A')}%")
        
        # Recent scaling activities
        activities = result.get("scaling_activities", [])
        if activities:
            answer_parts.append(f"\n**Recent Scaling Activities:** ({len(activities)} events)")
            for act in activities[:3]:
                answer_parts.append(f"- {act.get('status_code', 'N/A')}: {act.get('description', 'N/A')[:60]}...")
        
        # Errors
        errors = result.get("errors", {})
        if errors:
            answer_parts.append(f"\n⚠️ **Errors:** {errors}")
        
        if persist_result:
            if persist_result.get("ok"):
                answer_parts.append("\n✅ Snapshot saved to CloudWatch Logs")
            else:
                answer_parts.append(f"\n⚠️ Failed to save snapshot: {persist_result.get('error', {}).get('message', 'Unknown')}")
        
        answer = "\n".join(answer_parts)
    
    elif intent == "api_health":
        answer_parts = [f"🔍 **API Health Check** ({result.get('timestamp', 'N/A')})\n"]
        answer_parts.append(f"Base URL: `{result.get('base_url', 'N/A')}`")
        
        summary = result.get("summary", {})
        total = summary.get("total", 0)
        healthy = summary.get("healthy", 0)
        unhealthy = summary.get("unhealthy", 0)
        
        status_emoji = "✅" if unhealthy == 0 else "⚠️"
        answer_parts.append(f"\n{status_emoji} **Summary:** {healthy}/{total} endpoints healthy\n")
        
        endpoints = result.get("endpoints", {})
        for ep_name, ep_data in endpoints.items():
            status = "✅" if ep_data.get("healthy") else "❌"
            answer_parts.append(f"\n**{status} {ep_name}**")
            if ep_data.get("status_code"):
                answer_parts.append(f"- Status: {ep_data['status_code']}")
            if ep_data.get("response_time_ms"):
                answer_parts.append(f"- Response Time: {ep_data['response_time_ms']}ms")
            if ep_data.get("has_pagination") is not None:
                pag_status = "Yes" if ep_data["has_pagination"] else "No"
                answer_parts.append(f"- Pagination: {pag_status}")
                if ep_data.get("pagination_keys"):
                    answer_parts.append(f"  Keys: {ep_data['pagination_keys']}")
            if ep_data.get("error"):
                answer_parts.append(f"- ⚠️ Error: {ep_data['error']}")
        
        answer = "\n".join(answer_parts)
    
    elif intent == "api_pagination":
        answer_parts = [f"📄 **API Pagination Check** ({result.get('timestamp', 'N/A')})\n"]
        answer_parts.append(f"Endpoint: `{result.get('base_url', '')}{result.get('endpoint', '')}`\n")
        
        supports = result.get("supports_pagination", False)
        style = result.get("pagination_style")
        
        if supports:
            answer_parts.append(f"✅ **Pagination Supported!**")
            answer_parts.append(f"- Style: `{style}`")
        else:
            answer_parts.append(f"❌ **Pagination NOT Detected**")
            answer_parts.append("- The API might return all results at once")
            answer_parts.append("- Consider implementing pagination for large datasets")
        
        answer_parts.append("\n**Test Results:**")
        for test in result.get("tests", []):
            if test.get("success"):
                answer_parts.append(f"- {test['style']}: ✅ OK")
            elif test.get("error"):
                answer_parts.append(f"- {test['style']}: ❌ {test['error'][:50]}")
        
        answer = "\n".join(answer_parts)
    
    else:
        answer = f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
    
    return {
        "answer": answer,
        "session_id": session_id or str(uuid.uuid4()),
        "agent_id": OPS_AGENT_ID,
        "_local_function": intent,
        "_raw_result": result,
    }
