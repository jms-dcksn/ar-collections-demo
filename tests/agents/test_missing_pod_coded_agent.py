"""Contract tests for the in-solution missing-POD coded agent.

The agent replaced the inline low-code `missingPod` specialist. These tests pin
the pieces the Flow and the demo depend on: the `START -> agent -> END`
topology, the `create_agent()` subgraph, UiPath Trust Layer-only connectivity,
and the unchanged 4-in / 12-out Flow contract.
"""

import ast
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOLUTION = ROOT / "solution/ARCollectionsDemo"
AGENT_DIR = SOLUTION / "MissingPodCodedAgent"
MAIN_PATH = AGENT_DIR / "main.py"
MAPPING_PATH = ROOT / "config/agent-projects.json"

INPUT_FIELDS = {
    "recordCreated__output": "object",
    "triageAgent__output__disputeType": "string",
    "triageAgent__output__rationale": "string",
    "triageAgent__output__confidence": "number",
}
PROPOSAL_FIELDS = [
    "caseId",
    "disputeType",
    "evidenceSummary",
    "rootCause",
    "recommendedAction",
    "actionCode",
    "adjustmentAmount",
    "confidence",
    "approvalSummary",
    "emailSubject",
    "emailBody",
    "resourcesUsed",
]


def load_json(path: Path):
    assert path.is_file(), f"missing required JSON file: {path}"
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def source() -> str:
    assert MAIN_PATH.is_file(), f"missing coded agent entrypoint: {MAIN_PATH}"
    return MAIN_PATH.read_text()


@pytest.fixture(scope="module")
def tree(source: str) -> ast.Module:
    return ast.parse(source)


def test_the_inline_missing_pod_agent_is_gone():
    mapping = load_json(MAPPING_PATH)
    assert "missingPod" not in mapping["agents"]
    legacy = SOLUTION / "ARCollectionsDisputeResolution/81cc5d04-87bf-4a19-9a5f-ba1a2dbf006a"
    assert not legacy.exists(), "the superseded inline missing-POD project must be removed"


def test_project_is_a_langgraph_coded_agent_without_a_build_system():
    langgraph = load_json(AGENT_DIR / "langgraph.json")
    assert langgraph["graphs"] == {"agent": "./main.py:make_graph"}

    pyproject = (AGENT_DIR / "pyproject.toml").read_text()
    assert "uipath-langchain" in pyproject
    assert "[build-system]" not in pyproject


def test_graph_topology_is_exactly_start_agent_end(tree: ast.Module):
    """The wrapper graph must add exactly one node and two edges."""
    added_nodes = []
    added_edges = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "add_node":
            added_nodes.append(ast.unparse(node.args[0]))
        elif node.func.attr == "add_edge":
            added_edges.append(tuple(ast.unparse(arg) for arg in node.args))

    assert added_nodes == ["'agent'"]
    assert added_edges == [("START", "'agent'"), ("'agent'", "END")]


def test_the_only_node_is_the_create_agent_subgraph(tree: ast.Module):
    """`agent` must be the compiled create_agent() subgraph, not a hand-rolled
    LLM loop and not a business-logic node."""
    add_node_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_node"
    ]
    assert len(add_node_calls) == 1
    (call,) = add_node_calls

    # The node argument must resolve to the create_agent(...) result.
    node_arg = ast.unparse(call.args[1])
    create_agent_targets = {
        ast.unparse(target)
        for statement in ast.walk(tree)
        if isinstance(statement, ast.Assign)
        for target in statement.targets
        if isinstance(statement.value, ast.Call)
        and ast.unparse(statement.value.func) == "create_agent"
    }
    assert node_arg in create_agent_targets

    imported = {
        alias.name
        for statement in ast.walk(tree)
        if isinstance(statement, ast.ImportFrom) and statement.module == "langchain.agents"
        for alias in statement.names
    }
    assert "create_agent" in imported


def test_model_is_uipath_azure_chat_openai_on_the_pinned_deterministic_model(
    tree: ast.Module,
):
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "UiPathAzureChatOpenAI"
    ]
    assert len(calls) == 1
    kwargs = {kw.arg: kw.value for kw in calls[0].keywords}
    assert ast.unparse(kwargs["model"]) == "MODEL"
    assert ast.literal_eval(kwargs["temperature"]) == 0

    model = next(
        ast.literal_eval(statement.value)
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "MODEL"
            for target in statement.targets
        )
    )
    assert model == load_json(MAPPING_PATH)["model"] == "gpt-5.6-terra"


def test_the_model_client_is_built_at_runtime_not_at_import(tree: ast.Module):
    """Module-level instantiation needs UiPath auth and breaks `codedagent init`."""
    executed_at_import = [
        statement
        for statement in tree.body
        if not isinstance(
            statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        )
    ]
    for statement in executed_at_import:
        assert "UiPathAzureChatOpenAI(" not in ast.unparse(statement), (
            "the UiPath model client must be constructed inside the graph factory"
        )
    # The compiled graph must also not be built at import time.
    for statement in executed_at_import:
        assert "create_agent(" not in ast.unparse(statement)

    factories = [
        statement.name
        for statement in tree.body
        if isinstance(statement, ast.FunctionDef) and statement.name == "make_graph"
    ]
    assert factories == ["make_graph"]


def test_connectivity_is_trust_layer_only(source: str):
    """No direct-provider keys, endpoints, or SDKs may bypass the LLM Gateway."""
    forbidden = (
        "OPENAI_API_KEY",
        "AZURE_OPENAI",
        "api_key",
        "azure_endpoint",
        "openai.azure.com",
        "from openai",
        "import openai",
        "langchain_openai",
    )
    for token in forbidden:
        assert token not in source, f"direct-provider bypass detected: {token}"


def test_agent_declares_no_tools(tree: ast.Module):
    (call,) = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "create_agent"
    ]
    kwargs = {kw.arg: kw.value for kw in call.keywords}
    assert ast.literal_eval(kwargs["tools"]) == []


def test_entry_points_preserve_the_flow_input_and_proposal_contract():
    entry_points = load_json(AGENT_DIR / "entry-points.json")["entryPoints"]
    assert len(entry_points) == 1
    entry = entry_points[0]
    assert entry["filePath"] == "agent"

    assert {
        name: spec["type"] for name, spec in entry["input"]["properties"].items()
    } == INPUT_FIELDS

    output = entry["output"]
    assert list(output["properties"]) == PROPOSAL_FIELDS
    assert sorted(output["required"]) == sorted(PROPOSAL_FIELDS)
    assert output["properties"]["adjustmentAmount"]["type"] == "number"
    assert output["properties"]["confidence"]["type"] == "number"


def test_entry_point_graph_is_start_agent_end_with_an_agent_subgraph():
    entry = load_json(AGENT_DIR / "entry-points.json")["entryPoints"][0]
    graph = entry["graph"]
    assert [node["id"] for node in graph["nodes"]] == ["__start__", "agent", "__end__"]
    assert [(edge["source"], edge["target"]) for edge in graph["edges"]] == [
        ("__start__", "agent"),
        ("agent", "__end__"),
    ]
    agent_node = next(node for node in graph["nodes"] if node["id"] == "agent")
    assert agent_node["subgraph"] is not None
    model_nodes = [
        node for node in agent_node["subgraph"]["nodes"] if node["type"] == "model"
    ]
    assert len(model_nodes) == 1
    assert model_nodes[0]["metadata"]["model_name"] == "gpt-5.6-terra"


def test_system_prompt_carries_over_the_low_code_rules_and_missing_pod_facts(
    source: str,
):
    prompt = re.search(r'SYSTEM_PROMPT = """(.*?)"""', source, re.DOTALL)
    assert prompt, "SYSTEM_PROMPT is missing"
    system_prompt = prompt.group(1)

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

    for fact in ("2026-06-18", "M. Chen", "matching quantities", "PROVIDE_POD"):
        assert fact in system_prompt
    assert "adjustmentAmount=0" in system_prompt

    # Proposal-only: the agent must not send mail or update systems.
    assert "Out of scope: send an email" in system_prompt


def test_bindings_declare_no_resources():
    """The agent makes no UiPath SDK resource calls, so bindings stay empty."""
    bindings = load_json(AGENT_DIR / "bindings.json")
    assert bindings["resources"] == []


def test_pack_options_exclude_python_build_artifacts():
    """`uip solution upload` archives verbatim; .venv would break the upload."""
    uipath = load_json(AGENT_DIR / "uipath.json")
    excluded = set(uipath["packOptions"]["directoriesExcluded"])
    assert {".venv", "__pycache__"} <= excluded


def test_eval_dataset_covers_five_routed_cases_with_declared_evaluators():
    eval_set = load_json(
        AGENT_DIR / "evaluations/eval-sets/missing-pod-dataset.json"
    )
    assert eval_set["version"] == "1.0"
    assert eval_set["id"] == "missing-pod-dataset"

    evaluations = eval_set["evaluations"]
    assert len(evaluations) == 5
    assert len({case["id"] for case in evaluations}) == 5

    declared = set(eval_set["evaluatorRefs"])
    on_disk = {
        load_json(path)["id"]
        for path in (AGENT_DIR / "evaluations/evaluators").glob("*.json")
    }
    assert declared <= on_disk, "every evaluatorRef needs a config file"

    for case in evaluations:
        assert set(case["inputs"]) == set(INPUT_FIELDS)
        criteria = case["evaluationCriterias"]
        assert criteria, f"{case['id']} declares no evaluation criteria"
        assert set(criteria) <= declared

    # Two valid routes must pin the fixed missing-POD action deterministically.
    deterministic = [
        case
        for case in evaluations
        if "JsonSimilarityEvaluator" in case["evaluationCriterias"]
    ]
    assert len(deterministic) >= 2
    for case in deterministic:
        expected = case["evaluationCriterias"]["JsonSimilarityEvaluator"]["expectedOutput"]
        assert expected["actionCode"] == "PROVIDE_POD"
        assert expected["adjustmentAmount"] == 0

    # Degraded inputs must be represented: a misroute and an empty case packet.
    routed_types = {
        case["inputs"]["triageAgent__output__disputeType"] for case in evaluations
    }
    assert "missing_pod" in routed_types
    assert routed_types - {"missing_pod"}, "no conflicting-route case present"
    assert any(not case["inputs"]["recordCreated__output"] for case in evaluations)


def test_llm_judge_evaluator_pins_a_tenant_available_model():
    evaluator = load_json(
        AGENT_DIR / "evaluations/evaluators/llm-judge-output.json"
    )
    assert evaluator["evaluatorTypeId"] == "uipath-llm-judge-output-semantic-similarity"
    assert evaluator["evaluatorConfig"]["model"], "LLM judge needs an explicit model"
