"""Exporter - Exports test cases to JSON and YAML"""

import json
import yaml
import os
from datetime import datetime


def export_test_cases(input_path, json_output, yaml_output):
    """
    Export scored test cases to JSON and YAML with metadata

    Args:
        input_path: path to scored testcases JSON
        json_output: where to save final JSON
        yaml_output: where to save final YAML

    Returns:
        dict with export info (sizes, metadata, etc)
    """

    print(f"\nReading scored test cases from: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get('test_cases', [])
    print(f"Found {len(test_cases)} test cases to export")

    risk_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    priority_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for tc in test_cases:
        risk_cat = tc.get('risk_category', 'UNKNOWN').lower()
        if risk_cat in risk_summary:
            risk_summary[risk_cat] += 1

        priority = tc.get('priority', 'Unknown').lower()
        if priority in priority_summary:
            priority_summary[priority] += 1

    export_data = {
        "metadata": {
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_test_cases": len(test_cases),
            "risk_summary": risk_summary,
            "priority_summary": priority_summary,
            "generated_by": "AI Test Case Generator"
        },
        "test_cases": test_cases
    }

    os.makedirs(os.path.dirname(json_output), exist_ok=True)

    print(f"\nExporting to JSON: {json_output}")
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    json_size = os.path.getsize(json_output)

    print(f"Exporting to YAML: {yaml_output}")
    with open(yaml_output, 'w', encoding='utf-8') as f:
        yaml.dump(export_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    yaml_size = os.path.getsize(yaml_output)

    return {
        "test_cases_count": len(test_cases),
        "json_path": json_output,
        "json_size_kb": json_size / 1024,
        "yaml_path": yaml_output,
        "yaml_size_kb": yaml_size / 1024,
        "metadata": export_data["metadata"]
    }


if __name__ == "__main__":
    print("=" * 60)
    print("EXPORTER - JSON & YAML Output")
    print("=" * 60)

    input_file = "data/outputs/testcases_scored.json"
    json_out = "data/outputs/testcases_final.json"
    yaml_out = "data/outputs/testcases_final.yaml"

    try:
        result = export_test_cases(input_file, json_out, yaml_out)

        print(f"\n[SUCCESS] Exported {result['test_cases_count']} test cases")

        print("\n" + "-" * 60)
        print("OUTPUT FILES:")
        print("-" * 60)
        print(f"JSON: {result['json_path']} ({result['json_size_kb']:.1f} KB)")
        print(f"YAML: {result['yaml_path']} ({result['yaml_size_kb']:.1f} KB)")

        meta = result['metadata']
        print("\n" + "-" * 60)
        print("METADATA:")
        print("-" * 60)
        print(f"Export Date: {meta['export_date']}")
        print(f"Total Tests: {meta['total_test_cases']}")

        print("\nRisk Summary:")
        for cat, count in meta['risk_summary'].items():
            print(f"  {cat.upper()}: {count}")

    except FileNotFoundError:
        print("\n[ERROR] Input file not found")
        print("Run risk scoring first: python src/risk_scorer.py")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
