import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FLOW_DIR = ROOT / "solution/ARCollectionsDemo/ARCollectionsDisputeResolution"
MAPPING_PATH = ROOT / "config/agent-projects.json"

INPUT_FIELDS = {
    "loadSampleCase__output__output": {
        "type": "object",
        "description": "Case packet loaded by the Flow sample-case step.",
    },
    "triageAgent__output__disputeType": {
        "type": "string",
        "description": "Dispute type selected by the triage agent.",
    },
    "triageAgent__output__rationale": {
        "type": "string",
        "description": "Evidence-grounded rationale returned by the triage agent.",
    },
    "triageAgent__output__confidence": {
        "type": "number",
        "description": "Confidence returned by the triage agent.",
    },
}
INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(INPUT_FIELDS),
    "properties": INPUT_FIELDS,
}

OUTPUT_PROPERTIES = {
    "caseId": {"type": "string", "description": "Original case identifier."},
    "disputeType": {"type": "string", "description": "Routed dispute type."},
    "evidenceSummary": {
        "type": "string",
        "description": "Concise summary of evidence supporting the recommendation.",
    },
    "rootCause": {"type": "string", "description": "Concise cause of the payment blocker."},
    "recommendedAction": {"type": "string", "description": "Proposed resolution."},
    "actionCode": {
        "type": "string",
        "description": "Approved downstream action code.",
        "enum": ["ISSUE_CREDIT", "PROVIDE_POD", "REALLOCATE_PAYMENT"],
    },
    "adjustmentAmount": {
        "type": "number",
        "description": "Financial adjustment amount, or zero when none is needed.",
    },
    "confidence": {
        "type": "number",
        "description": "Specialist confidence from 0 to 1.",
        "minimum": 0,
        "maximum": 1,
    },
    "approvalSummary": {
        "type": "string",
        "description": "Concise collector-facing approval summary.",
    },
    "emailSubject": {"type": "string", "description": "Proposed customer email subject."},
    "emailBody": {
        "type": "string",
        "description": "Proposed plain-text customer email body.",
    },
    "resourcesUsed": {
        "type": "string",
        "description": "Business-readable sources actually used, without invented resource calls.",
    },
}
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(OUTPUT_PROPERTIES),
    "properties": OUTPUT_PROPERTIES,
}

EXPECTED_INPUT_TOKENS = {
    "input.loadSampleCase__output__output",
    "input.triageAgent__output__disputeType",
    "input.triageAgent__output__rationale",
    "input.triageAgent__output__confidence",
}

SPECIALISTS = {
    "poMismatch": {
        "project_id": "30427850-3685-4d58-9c41-8dfb95163182",
        "prompt_terms": (
            "48,750",
            "47,250",
            "1,500",
            "ISSUE_CREDIT",
            "adjustmentAmount=1500",
        ),
    },
    "missingPod": {
        "project_id": "81cc5d04-87bf-4a19-9a5f-ba1a2dbf006a",
        "prompt_terms": (
            "2026-06-18",
            "M. Chen",
            "matching quantities",
            "PROVIDE_POD",
            "adjustmentAmount=0",
        ),
    },
}


def load_agent(agent_key: str) -> tuple[Path, dict]:
    mapping = json.loads(MAPPING_PATH.read_text())
    project_id = mapping["agents"][agent_key]
    assert re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", project_id)
    assert project_id == SPECIALISTS[agent_key]["project_id"]

    agent_dir = FLOW_DIR / project_id
    agent_path = agent_dir / "agent.json"
    assert agent_dir.is_dir()
    assert agent_path.is_file()
    return agent_dir, json.loads(agent_path.read_text())


@pytest.mark.parametrize("agent_key", SPECIALISTS)
def test_basic_specialist_contract(agent_key: str) -> None:
    agent_dir, agent = load_agent(agent_key)

    assert agent["projectId"] == SPECIALISTS[agent_key]["project_id"]
    assert agent["type"] == "lowCode"
    assert agent["metadata"]["isConversational"] is False
    assert agent["settings"] == {
        "model": "gpt-5.6-terra",
        "maxTokens": 4096,
        "temperature": 0,
        "engine": "basic-v2",
        "maxIterations": 5,
        "mode": "standard",
    }
    assert agent["inputSchema"] == INPUT_SCHEMA
    assert agent["outputSchema"] == OUTPUT_SCHEMA

    assert [message["role"] for message in agent["messages"]] == ["system", "user"]
    assert all(message["content"].strip() for message in agent["messages"])

    system_prompt = agent["messages"][0]["content"]
    user_prompt = agent["messages"][1]["content"]
    combined_prompt = f"{system_prompt}\n{user_prompt}"

    for field_name in INPUT_FIELDS:
        assert f"{{{{input.{field_name}}}}}" in user_prompt
    assert "{{input.casePacket}}" not in combined_prompt
    assert "$vars" not in combined_prompt

    variable_tokens = {
        token["rawString"]
        for token in agent["messages"][1]["contentTokens"]
        if token["type"] == "variable"
    }
    assert variable_tokens == EXPECTED_INPUT_TOKENS
    assert agent["messages"][0]["contentTokens"] == [
        {"type": "simpleText", "rawString": system_prompt}
    ]

    for required_rule in (
        "preserve caseId",
        "preserve the routed disputeType",
        "concise collector-facing approval summary",
        "plain-text customer email",
        "fictional company name",
        "never select or infer a recipient",
        "use only the supplied case packet and triage routing evidence",
        "no tools or Context Grounding resources",
        "never invent tool calls or context searches",
        "return only the structured output contract",
    ):
        assert required_rule.lower() in system_prompt.lower()

    for term in SPECIALISTS[agent_key]["prompt_terms"]:
        assert term in system_prompt

    resources_dir = agent_dir / "resources"
    assert resources_dir.is_dir()
    assert list(resources_dir.iterdir()) == []
    assert "resources" not in agent
