import json
from pathlib import Path
from uuid import UUID

import pytest


ROOT = Path(__file__).resolve().parents[2]
FLOW_DIR = ROOT / "solution/ARCollectionsDemo/ARCollectionsDisputeResolution"
MAPPING_PATH = ROOT / "config/agent-projects.json"
FLATTENED_INPUT = "recordCreated__output"


def _load_json(path: Path):
    assert path.is_file(), f"missing required JSON file: {path}"
    return json.loads(path.read_text())


def _triage_project():
    mapping = _load_json(MAPPING_PATH)
    assert set(mapping["agents"]) == {
        "triage",
        "poMismatch",
        "missingPod",
        "paymentMisapplication",
    }
    project_id = mapping["agents"]["triage"]
    assert str(UUID(project_id)) == project_id
    project_dir = FLOW_DIR / project_id
    assert project_dir.is_dir(), f"missing triage project: {project_dir}"
    return project_id, project_dir, _load_json(project_dir / "agent.json")


def test_triage_agent_has_deterministic_model_and_exact_schemas():
    project_id, _, agent = _triage_project()

    assert agent["projectId"] == project_id
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
    assert agent["inputSchema"]["type"] == "object"
    assert set(agent["inputSchema"]["properties"]) == {FLATTENED_INPUT}
    assert agent["inputSchema"]["properties"][FLATTENED_INPUT]["type"] == "object"
    assert agent["outputSchema"]["type"] == "object"
    assert {
        name: definition.get("type")
        for name, definition in agent["outputSchema"]["properties"].items()
    } == {"disputeType": "string", "rationale": "string", "confidence": "number"}


def test_triage_prompts_enforce_grounded_classification_and_flattened_input():
    _, _, agent = _triage_project()
    messages = agent["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    normalized_system = " ".join(system_prompt.lower().split())
    normalized_user = " ".join(user_prompt.lower().split())

    for required_text in (
        "search the attached ar-dispute-triage-index taxonomy on every run",
        "classify only from the case packet and the retrieved taxonomy",
        "cite the taxonomy category and example in rationale",
        "ambiguous",
        "unsupported",
        "below 0.75",
        "never call tools",
        "never propose a resolution",
        "do not invent facts",
    ):
        assert required_text in normalized_system
    for dispute_type in (
        "po_mismatch",
        "missing_pod",
        "payment_misapplication",
        "unsupported",
    ):
        assert dispute_type in normalized_system

    variable = f"{{{{input.{FLATTENED_INPUT}}}}}"
    assert user_prompt.count(variable) == 1
    assert "$vars" not in user_prompt
    assert "return only json with exactly these fields: disputeType, rationale, confidence".lower() in normalized_user
    assert messages[0]["contentTokens"] == [
        {"type": "simpleText", "rawString": system_prompt}
    ]
    assert messages[1]["contentTokens"] == [
        {
            "type": "simpleText",
            "rawString": "Classify this AR dispute case packet.\n\nCase packet:\n",
        },
        {"type": "variable", "rawString": f"input.{FLATTENED_INPUT}"},
        {
            "type": "simpleText",
            "rawString": (
                "\n\nReturn only JSON with exactly these fields: "
                "disputeType, rationale, confidence."
            ),
        },
    ]


def test_triage_has_exactly_one_enabled_index_context_and_no_tools():
    _, project_dir, _ = _triage_project()
    resource_paths = sorted(project_dir.glob("resources/*/resource.json"))
    assert len(resource_paths) == 1

    resource_path = resource_paths[0]
    resource = _load_json(resource_path)
    resource_id = resource_path.parent.name
    assert str(UUID(resource_id)) == resource_id
    required_resource_keys = {
        "$resourceType",
        "id",
        "referenceKey",
        "name",
        "description",
        "contextType",
        "folderPath",
        "indexName",
        "settings",
    }
    assert required_resource_keys <= set(resource) <= required_resource_keys | {"isEnabled"}
    assert resource["id"] == resource_id
    assert resource["$resourceType"] == "context"
    assert resource.get("isEnabled", True) is True
    assert resource["referenceKey"] in {None, ""}
    assert resource["contextType"] == "index"
    assert resource["folderPath"] == "JD/demos"
    assert resource["indexName"] == "ar-dispute-triage-index"
    settings = resource["settings"]
    assert settings["retrievalMode"] == "semantic"
    assert settings["query"]["variant"] == "dynamic"
    assert settings["folderPathPrefix"] == {"variant": "static", "value": ""}
    assert settings["fileExtension"] == {"value": "All"}
    assert settings["threshold"] == 0
    assert all(
        _load_json(path).get("$resourceType") != "tool" for path in resource_paths
    )


@pytest.mark.xfail(
    reason="UV-15990: the VS Code flow editor discards authored context metadata on save",
    strict=False,
)
def test_triage_context_keeps_authored_metadata():
    _, project_dir, _ = _triage_project()
    resource = _load_json(sorted(project_dir.glob("resources/*/resource.json"))[0])
    assert resource["name"] == "AR Dispute Triage Taxonomy"
    assert "classif" in resource["description"].lower()
    assert resource["settings"]["resultCount"] == 5
    assert resource["settings"]["query"]["description"] == (
        "Retrieve taxonomy categories and examples for dispute classification."
    )
