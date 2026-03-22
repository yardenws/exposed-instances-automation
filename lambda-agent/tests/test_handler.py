from handler import handler


class TestHandler:
    def test_returns_no_instances_when_empty(self):
        result = handler({"instances": []}, None)
        assert result["status"] == "no_instances"

    def test_returns_enriched_with_count(self):
        instances = [
            {"instance_id": "i-abc", "public_ip": "1.2.3.4"},
            {"instance_id": "i-def", "public_ip": "5.6.7.8"},
        ]
        result = handler({"instances": instances}, None)
        assert result["status"] == "enriched"
        assert result["instance_count"] == 2

    def test_handles_missing_instances_key(self):
        result = handler({}, None)
        assert result["status"] == "no_instances"
