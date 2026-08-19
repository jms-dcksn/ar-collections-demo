import json
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "config" / "platform-resources.json"

EXPECTED = {
    "folderPath": "JD/demos",
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

ALLOWED_MANIFEST_KEYS = {
    "folderPath",
    "folderKey",
    "connectionFolderPath",
    "connectionFolderKey",
    "outlookConnection",
    "connectionKey",
    "dataFabricConnection",
    "dataFabricConnectionKey",
    "dataFabricEntities",
    "resources",
}
ALLOWED_RESOURCE_KEYS = {
    "source",
    "bucket",
    "bucketKey",
    "index",
    "indexKey",
}


def _assert_canonical_uuid(value):
    assert isinstance(value, str)
    assert value
    assert str(UUID(value)) == value


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


def test_platform_manifest_has_final_provisioned_identity_fields():
    manifest = json.loads(MANIFEST.read_text())

    assert set(manifest) == ALLOWED_MANIFEST_KEYS

    connection_key = manifest["connectionKey"]
    assert isinstance(connection_key, str)
    if connection_key:
        _assert_canonical_uuid(connection_key)

    identity_keys = []
    for resource in manifest["resources"]:
        assert set(resource) == ALLOWED_RESOURCE_KEYS
        for field in ("bucketKey", "indexKey"):
            identity_key = resource[field]
            _assert_canonical_uuid(identity_key)
            identity_keys.append(identity_key)

    assert len(identity_keys) == len(set(identity_keys))


def test_platform_manifest_declares_the_approved_data_fabric_entity():
    manifest = json.loads(MANIFEST.read_text())
    entity = manifest.get(
        "dataFabricEntities",
        [{"folderKey": None, "displayName": None, "systemName": None, "fields": []}],
    )[0]

    assert entity["folderKey"] is None
    assert entity["displayName"] == "JD AR Collections Entity"
    assert entity["systemName"] == "JDARCollectionsEntity"
    assert entity["entityKey"] == "81a5f874-d79b-f111-9b33-6045bdd6658d"
    assert entity["fields"] == [
        {"name": "caseId", "type": "STRING", "required": True, "unique": True},
        {"name": "customerName", "type": "STRING", "required": True, "unique": False},
        {
            "name": "customerAccountId",
            "type": "STRING",
            "required": True,
            "unique": False,
        },
        {"name": "invoiceNumber", "type": "STRING", "required": True, "unique": False},
        {
            "name": "outstandingBalance",
            "type": "DECIMAL",
            "required": True,
            "unique": False,
            "decimalPrecision": 2,
        },
        {
            "name": "customerReason",
            "type": "MULTILINE_TEXT",
            "required": True,
            "unique": False,
        },
        {"name": "openedDate", "type": "DATE", "required": True, "unique": False},
        {"name": "evidence", "type": "MULTILINE_TEXT", "required": True, "unique": False},
        {"name": "recipientEmail", "type": "STRING", "required": True, "unique": False},
        {"name": "lifecycleState", "type": "STRING", "required": False, "unique": False},
        {"name": "disputeType", "type": "STRING", "required": False, "unique": False},
        {
            "name": "triageRationale",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {
            "name": "triageConfidence",
            "type": "DECIMAL",
            "required": False,
            "unique": False,
            "decimalPrecision": 4,
        },
        {
            "name": "evidenceSummary",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {"name": "rootCause", "type": "MULTILINE_TEXT", "required": False, "unique": False},
        {
            "name": "recommendedAction",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {"name": "actionCode", "type": "STRING", "required": False, "unique": False},
        {
            "name": "adjustmentAmount",
            "type": "DECIMAL",
            "required": False,
            "unique": False,
            "decimalPrecision": 2,
        },
        {
            "name": "specialistConfidence",
            "type": "DECIMAL",
            "required": False,
            "unique": False,
            "decimalPrecision": 4,
        },
        {
            "name": "approvalSummary",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {"name": "emailSubject", "type": "STRING", "required": False, "unique": False},
        {"name": "emailBody", "type": "MULTILINE_TEXT", "required": False, "unique": False},
        {
            "name": "resourcesUsed",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {
            "name": "approvalDecision",
            "type": "STRING",
            "required": False,
            "unique": False,
        },
        {"name": "approvedBy", "type": "STRING", "required": False, "unique": False},
        {
            "name": "approvalComments",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {
            "name": "updateResult",
            "type": "MULTILINE_TEXT",
            "required": False,
            "unique": False,
        },
        {"name": "emailSent", "type": "BOOLEAN", "required": False, "unique": False},
        {"name": "auditSummary", "type": "MULTILINE_TEXT", "required": False, "unique": False},
    ]
