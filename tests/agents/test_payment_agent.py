import json
from pathlib import Path
from uuid import UUID

import pytest


ROOT = Path(__file__).resolve().parents[2]
FLOW_DIR = ROOT / "solution" / "ARCollectionsDemo" / "ARCollectionsDisputeResolution"
MAPPING_PATH = ROOT / "config" / "agent-projects.json"

PAYMENT_AGENT_ID = "1c6b5289-1ff4-45f1-b48c-e613f8fd917f"
INPUT_FIELDS = {
    "recordCreated__output": "object",
    "triageAgent__output__disputeType": "string",
    "triageAgent__output__rationale": "string",
    "triageAgent__output__confidence": "number",
}
OUTPUT_FIELDS = {
    "caseId": "string",
    "disputeType": "string",
    "evidenceSummary": "string",
    "rootCause": "string",
    "recommendedAction": "string",
    "actionCode": "string",
    "adjustmentAmount": "number",
    "confidence": "number",
    "approvalSummary": "string",
    "emailSubject": "string",
    "emailBody": "string",
    "resourcesUsed": "string",
}
ACTION_CODES = ["ISSUE_CREDIT", "PROVIDE_POD", "REALLOCATE_PAYMENT"]
TOOL_INPUT_FIELDS = {
    "caseId": "string",
    "customerAccountId": "string",
    "invoiceNumber": "string",
    "paymentReference": "string",
}
TOOL_OUTPUT_FIELDS = {
    "paymentReference": "string",
    "paymentAmount": "number",
    "paymentDate": "string",
    "appliedInvoiceNumber": "string",
    "targetInvoiceNumber": "string",
    "applicationStatus": "string",
    "matchedRemittance": "boolean",
    "recommendedAction": "string",
    "sourceSystem": "string",
}


def load_payment_agent():
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    agent_id = mapping["agents"]["paymentMisapplication"]
    assert str(UUID(agent_id)) == agent_id
    assert agent_id == PAYMENT_AGENT_ID

    agent_dir = FLOW_DIR / agent_id
    assert agent_dir.is_dir()
    agent_path = agent_dir / "agent.json"
    assert agent_path.is_file()
    agent = json.loads(agent_path.read_text(encoding="utf-8"))
    assert agent["projectId"] == agent_id == agent_dir.name
    return agent_dir, agent


def schema_types(schema):
    return {
        name: definition.get("type")
        for name, definition in schema.get("properties", {}).items()
    }


def load_resources(agent_dir):
    resources_dir = agent_dir / "resources"
    assert resources_dir.is_dir()
    resource_files = sorted(resources_dir.glob("*/resource.json"))
    assert len(resource_files) == 2

    resources = []
    ids = set()
    for resource_file in resource_files:
        resource = json.loads(resource_file.read_text(encoding="utf-8"))
        resource_id = resource["id"]
        assert str(UUID(resource_id)) == resource_id
        assert resource_file.parent.name == resource_id
        assert resource_id not in ids
        ids.add(resource_id)
        resources.append(resource)
    return resources


def test_payment_agent_has_exact_flattened_input_and_specialist_output_contracts():
    _, agent = load_payment_agent()

    input_schema = agent["inputSchema"]
    assert input_schema["type"] == "object"
    assert schema_types(input_schema) == INPUT_FIELDS
    assert "casePacket" not in input_schema["properties"]

    output_schema = agent["outputSchema"]
    assert output_schema["type"] == "object"
    assert schema_types(output_schema) == OUTPUT_FIELDS


def test_payment_agent_uses_selected_model_and_grounded_specialist_prompts():
    _, agent = load_payment_agent()

    assert agent["settings"] == {
        "model": "gpt-5.6-terra",
        "maxTokens": 4096,
        "temperature": 0,
        "engine": "basic-v2",
        "maxIterations": 8,
        "mode": "standard",
    }
    messages = {message["role"]: message["content"] for message in agent["messages"]}
    assert messages["system"].strip()
    assert messages["user"].strip()

    user_prompt = messages["user"]
    for field in INPUT_FIELDS:
        assert f"{{{{input.{field}}}}}" in user_prompt
    assert "{{input.casePacket}}" not in user_prompt

    prompt = f"{messages['system']}\n{user_prompt}".casefold()
    for requirement in (
        "lookuppaymentapplication",
        "ar-payment-resolution-index",
        "before reasoning",
        "both resources",
        "consistent",
        "reallocate_payment",
        "adjustmentamount: 0",
        "inv-30915",
        "will clear",
        "fictional company name",
        "never select the recipient",
        "resourcesused",
        "do not invent resource calls",
        "fail the agent run",
        "return only",
    ):
        assert requirement in prompt


def test_payment_agent_has_exact_context_and_api_resources():
    agent_dir, _ = load_payment_agent()
    resources = load_resources(agent_dir)

    contexts = [r for r in resources if r.get("$resourceType") == "context"]
    tools = [r for r in resources if r.get("$resourceType") == "tool"]
    assert len(contexts) == 1
    assert len(tools) == 1

    context = contexts[0]
    assert context.get("isEnabled", True) is True
    assert context["referenceKey"] in {None, ""}
    assert context["contextType"] == "index"
    assert context["folderPath"] == "JD/demos"
    assert context["indexName"] == "ar-payment-resolution-index"
    settings = context["settings"]
    assert settings["retrievalMode"] == "semantic"
    assert settings["query"]["variant"] == "dynamic"
    assert settings["folderPathPrefix"] == {"variant": "static", "value": ""}
    assert settings["fileExtension"] == {"value": "All"}
    assert settings["threshold"] == 0

    tool = tools[0]
    required_tool_keys = {
        "$resourceType",
        "name",
        "description",
        "location",
        "type",
        "inputSchema",
        "outputSchema",
        "settings",
        "guardrail",
        "properties",
        "id",
        "referenceKey",
        "argumentProperties",
    }
    assert required_tool_keys <= set(tool) <= required_tool_keys | {
        "canvasNodeId",
        "isEnabled",
    }
    assert tool["name"] == "LookupPaymentApplication"
    assert "read-only lookup for cash-application evidence" in tool["description"]
    assert tool["location"] == "solution"
    assert tool["type"] == "api"
    assert tool["referenceKey"] == "e2a2f52e-30ba-4ce0-a1b0-0a45a7b04898"
    assert tool.get("isEnabled", True) is True
    assert tool["settings"] == {}
    assert tool["guardrail"] == {"policies": []}
    assert tool["properties"] == {
        "processName": "LookupPaymentApplication",
        "folderPath": "JD/demos",
    }
    assert tool["argumentProperties"] == {}


def test_payment_lookup_tool_has_exact_runtime_schemas():
    agent_dir, _ = load_payment_agent()
    tool = next(
        resource
        for resource in load_resources(agent_dir)
        if resource.get("$resourceType") == "tool"
    )

    input_schema = tool["inputSchema"]
    assert input_schema["type"] == "object"
    assert schema_types(input_schema) == TOOL_INPUT_FIELDS

    output_schema = tool["outputSchema"]
    assert output_schema["type"] == "object"
    assert schema_types(output_schema) == TOOL_OUTPUT_FIELDS


@pytest.mark.xfail(
    reason="UV-15990: the VS Code flow editor discards authored resource metadata on save",
    strict=False,
)
def test_payment_resources_keep_authored_metadata():
    agent_dir, _ = load_payment_agent()
    resources = load_resources(agent_dir)
    context = next(r for r in resources if r.get("$resourceType") == "context")
    tool = next(r for r in resources if r.get("$resourceType") == "tool")

    assert context["name"] == "Payment Resolution Knowledge"
    assert "payment-misapplication" in context["description"].lower()
    assert context["settings"]["resultCount"] == 5
    assert context["settings"]["query"]["description"] == (
        "Retrieve payment-misapplication controls and resolution evidence."
    )
    assert schema_types(tool["inputSchema"])["guardrails"] == "array"
    assert tool["inputSchema"]["required"]
    assert tool["outputSchema"]["required"]
