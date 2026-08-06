import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOLUTION = ROOT / "solution" / "ARCollectionsDemo"


def test_solution_contains_one_flow_and_two_api_workflows():
    expected = {
        "ARCollectionsDisputeResolution": ".flow",
        "LookupPaymentApplication": "Workflow.json",
        "MockUpdateDispute": "Workflow.json",
    }
    for project, marker in expected.items():
        project_dir = SOLUTION / project
        assert project_dir.is_dir(), project
        if marker == ".flow":
            assert (project_dir / f"{project}.flow").is_file()
        else:
            assert (project_dir / marker).is_file()


def test_solution_manifest_registers_exactly_three_projects():
    manifest = json.loads((SOLUTION / "ARCollectionsDemo.uipx").read_text())
    projects = manifest["Projects"]
    assert len(projects) == 3
    serialized = json.dumps(projects)
    for name in (
        "ARCollectionsDisputeResolution",
        "LookupPaymentApplication",
        "MockUpdateDispute",
    ):
        assert name in serialized
