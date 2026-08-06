import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "config" / "platform-resources.json"

EXPECTED = {
    "folderPath": "JD_Demos/demos",
    "outlookConnection": "james.dickson@uipath.com",
    "resources": [
        {
            "source": "knowledge/triage/ar-dispute-taxonomy-and-examples.txt",
            "bucket": "ar-dispute-triage-kb",
            "index": "ar-dispute-triage-index",
        },
        {
            "source": "knowledge/payment/payment-misapplication-resolution-playbook.txt",
            "bucket": "ar-payment-resolution-kb",
            "index": "ar-payment-resolution-index",
        },
    ],
}


def test_platform_manifest_has_exact_stable_resource_names():
    manifest = json.loads(MANIFEST.read_text())

    assert manifest["folderPath"] == EXPECTED["folderPath"]
    assert manifest["outlookConnection"] == EXPECTED["outlookConnection"]
    assert len(manifest["resources"]) == len(EXPECTED["resources"])

    stable_fields = ("source", "bucket", "index")
    actual_resources = [
        {field: resource[field] for field in stable_fields}
        for resource in manifest["resources"]
    ]
    assert actual_resources == EXPECTED["resources"]


def test_platform_manifest_reserves_only_discovered_identity_fields():
    manifest = json.loads(MANIFEST.read_text())

    assert isinstance(manifest["connectionKey"], str)
    for resource in manifest["resources"]:
        assert isinstance(resource["bucketKey"], str)
        assert isinstance(resource["indexKey"], str)
