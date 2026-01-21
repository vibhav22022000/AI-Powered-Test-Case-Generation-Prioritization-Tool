"""Risk Scorer - Calculates and prioritizes test cases by risk"""

import json
import os

# Priority weights
PRIORITY_SCORES = {
    "Critical": 10,
    "High": 7,
    "Medium": 4,
    "Low": 2
}

# Test type weights
TEST_TYPE_SCORES = {
    "Security": 8,
    "Integration": 7,
    "Error Handling": 6,
    "Functional": 5,
    "Performance": 4,
    "UI/UX": 3,
    "Edge Case": 3
}

# High-risk component scores
HIGH_RISK_COMPONENTS = {
    "Payment Gateway": 10,
    "Payment": 10,
    "Authentication": 9,
    "Authorization": 9,
    "Security": 9,
    "Database": 7,
    "API Security": 8,
    "Stripe": 9,
    "Password Management": 7,
    "Access Control": 8,
    "Role Management": 7,
    "SQL Injection Prevention": 10,
    "Input Validation": 6,
    "Login": 7,
    "Checkout": 8,
    "Cart": 5,
    "Shopping Cart": 5
}


def get_complexity_score(test_steps):
    """Calculate complexity score based on number of test steps"""
    num_steps = len(test_steps) if test_steps else 0

    if num_steps >= 8:
        return 6
    elif num_steps >= 5:
        return 4
    elif num_steps >= 3:
        return 2
    else:
        return 1


def get_component_risk(components):
    """Calculate average risk score for the components involved"""
    if not components:
        return 0

    total = 0
    for comp in components:
        score = HIGH_RISK_COMPONENTS.get(comp, 1)
        total += score

    avg = total / len(components)
    return min(avg, 10)


def calculate_risk_score(test_case):
    """
    Calculate overall risk score for a test case

    Formula:
        Risk = (Priority * 0.4) + (TestType * 0.3) + (Components * 0.2) + (Complexity * 0.1)

    Returns a score from 0-100
    """

    priority = test_case.get('priority', 'Medium')
    priority_score = PRIORITY_SCORES.get(priority, 4)

    test_type = test_case.get('test_type', 'Functional')
    type_score = TEST_TYPE_SCORES.get(test_type, 5)

    components = test_case.get('components', [])
    component_score = get_component_risk(components)

    test_steps = test_case.get('test_steps', [])
    complexity_score = get_complexity_score(test_steps)

    risk = (
        (priority_score * 0.4 * 10) +
        (type_score * 0.3 * 10) +
        (component_score * 0.2 * 10) +
        (complexity_score * 0.1 * 10)
    )

    return round(risk, 2)


def get_risk_category(score):
    """Convert numeric score to category label"""
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    else:
        return "LOW"


def add_risk_scores(input_path, output_path):
    """
    Read test cases, add risk scores, sort by priority, and save

    Args:
        input_path: testcases.json from LLM parser
        output_path: where to save scored test cases
    """

    print(f"\nReading test cases from: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get('test_cases', [])
    print(f"Found {len(test_cases)} test cases")

    print("\nCalculating risk scores...")
    for tc in test_cases:
        score = calculate_risk_score(tc)
        tc['risk_score'] = score
        tc['risk_category'] = get_risk_category(score)

    test_cases.sort(key=lambda x: x['risk_score'], reverse=True)

    for i, tc in enumerate(test_cases, 1):
        tc['execution_order'] = i

    result = {'test_cases': test_cases}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("RISK SCORER - Prioritize Test Cases")
    print("=" * 60)

    input_file = "data/outputs/testcases.json"
    output_file = "data/outputs/testcases_scored.json"

    try:
        result = add_risk_scores(input_file, output_file)
        test_cases = result['test_cases']

        print(f"\n[SUCCESS] Scored {len(test_cases)} test cases")
        print(f"Saved to: {output_file}")

        print("\n" + "=" * 70)
        print("PRIORITIZED TEST ORDER:")
        print("=" * 70)
        print(f"\n{'#':<3} {'ID':<8} {'Score':<6} {'Risk':<10} {'Title':<40}")
        print("-" * 70)

        for tc in test_cases:
            print(f"{tc['execution_order']:<3} {tc['test_id']:<8} {tc['risk_score']:<6} "
                  f"{tc['risk_category']:<10} {tc['title'][:40]:<40}")

        print("\n" + "-" * 70)
        print("DISTRIBUTION:")
        risk_counts = {}
        for tc in test_cases:
            cat = tc['risk_category']
            risk_counts[cat] = risk_counts.get(cat, 0) + 1

        for cat in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = risk_counts.get(cat, 0)
            pct = (count / len(test_cases)) * 100 if test_cases else 0
            bar = "#" * int(pct / 5)
            print(f"  {cat:<10} {count:>2} ({pct:>5.1f}%) {bar}")

    except FileNotFoundError:
        print("\n[ERROR] Input file not found")
        print("Run the LLM parser first: python src/llm_parser.py")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
