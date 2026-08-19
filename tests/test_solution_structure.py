import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOLUTION = ROOT / "solution" / "ARCollectionsDemo"
MANIFEST = SOLUTION / "AR Collections Dispute Flow.uipx"


def test_solution_contains_one_flow_two_api_workflows_and_the_coded_agent():
    expected = {
        "ARCollectionsDisputeResolution": ".flow",
        "LookupPaymentApplication": "Workflow.json",
        "MockUpdateDispute": "Workflow.json",
        "MissingPodCodedAgent": "main.py",
    }
    for project, marker in expected.items():
        project_dir = SOLUTION / project
        assert project_dir.is_dir(), project
        if marker == ".flow":
            assert (project_dir / f"{project}.flow").is_file()
        else:
            assert (project_dir / marker).is_file()


def test_solution_manifest_registers_exactly_four_projects():
    manifest = json.loads(MANIFEST.read_text())
    projects = manifest["Projects"]
    assert len(projects) == 4
    by_name = {
        project["ProjectRelativePath"].split("/")[0]: project for project in projects
    }
    assert by_name["ARCollectionsDisputeResolution"]["Type"] == "Flow"
    assert by_name["LookupPaymentApplication"]["Type"] == "Api"
    assert by_name["MockUpdateDispute"]["Type"] == "Api"
    assert by_name["MissingPodCodedAgent"]["Type"] == "Agent"


def test_only_one_solution_manifest_is_checked_in():
    assert [path.name for path in SOLUTION.glob("*.uipx")] == [MANIFEST.name]
