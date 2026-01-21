"""LLM Parser - Converts OCR text to structured test cases via GPT"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv


PARSING_PROMPT = """You are a QA automation expert. Your task is to parse the provided QA document text and extract ALL test cases into a structured JSON format.

CRITICAL INSTRUCTIONS:
1. Extract EVERY test case you find in the document
2. Parse messy, unstructured test case descriptions into clean, structured format
3. Identify test case IDs (like TC-001, TC-002, etc.)
4. Break down test descriptions into clear steps
5. Categorize each test case by type (Functional, Security, Performance, etc.)
6. Assign priority based on keywords: CRITICAL/HIGH/MEDIUM/LOW
7. Extract components being tested (login, payment, cart, etc.)
8. If preconditions are mentioned, extract them
9. Extract expected results/outcomes

TEST TYPES TO USE:
- Functional: Basic feature testing
- Security: Authentication, authorization, SQL injection, XSS, etc.
- Performance: Load time, response time, scalability
- Integration: API calls, third-party services, database interactions
- UI/UX: User interface, mobile responsiveness, accessibility
- Error Handling: Exception handling, error messages, edge cases
- Edge Case: Boundary conditions, unusual inputs

PRIORITY MAPPING:
- Critical: Payment, security, authentication, data loss prevention
- High: Major features, user-facing functionality
- Medium: Secondary features, minor bugs
- Low: Nice-to-have, cosmetic issues

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this structure (no markdown, no explanation):

{{
  "test_cases": [
    {{
      "test_id": "TC-001",
      "title": "User Login with Valid Credentials",
      "description": "Verify that a user can successfully log in using correct email and password",
      "preconditions": "User account exists in the system",
      "test_steps": [
        "Navigate to login page",
        "Enter valid email address",
        "Enter correct password",
        "Click Login button"
      ],
      "expected_result": "User is redirected to dashboard with welcome message displayed",
      "test_type": "Functional",
      "priority": "High",
      "components": ["Authentication", "Login", "UI"]
    }}
  ]
}}

NOW PARSE THIS QA DOCUMENT:

{ocr_text}

Remember: Return ONLY valid JSON, no additional text or markdown formatting."""


def parse_with_openai(ocr_text, api_key, model="gpt-4o-mini"):
    """Send OCR text to OpenAI and get structured test cases back"""

    try:
        client = OpenAI(api_key=api_key)

        print(f"Calling OpenAI API ({model})...")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a QA automation expert that extracts test cases from documents and returns only valid JSON."
                },
                {
                    "role": "user",
                    "content": PARSING_PROMPT.format(ocr_text=ocr_text)
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = response.choices[0].message.content
        return json.loads(result)

    except Exception as e:
        error_msg = str(e)

        if "invalid_api_key" in error_msg.lower() or "401" in error_msg:
            raise ValueError(
                f"Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env file.\n"
                f"Original error: {error_msg}"
            )
        elif "insufficient_quota" in error_msg.lower() or "429" in error_msg:
            raise ValueError(
                f"OpenAI API quota exceeded or no credits. "
                f"Add billing at https://platform.openai.com/account/billing\n"
                f"Original error: {error_msg}"
            )
        elif "rate_limit" in error_msg.lower():
            raise ValueError(
                f"OpenAI API rate limit reached. Wait a bit and try again.\n"
                f"Original error: {error_msg}"
            )
        else:
            raise ValueError(f"OpenAI API error: {error_msg}")


def parse_test_cases(input_text_path, output_json_path):
    """
    Main function - reads OCR text file and outputs structured JSON

    Args:
        input_text_path: path to the OCR extracted text
        output_json_path: where to save the parsed test cases

    Returns:
        dict with test_cases array
    """

    load_dotenv()

    print(f"\nReading OCR text from: {input_text_path}")
    with open(input_text_path, 'r', encoding='utf-8') as f:
        ocr_text = f.read()

    print(f"Text length: {len(ocr_text)} characters")

    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    llm_model = os.getenv('LLM_MODEL')

    if llm_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        model = llm_model or "gpt-4o-mini"
        result = parse_with_openai(ocr_text, api_key, model)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {llm_provider}. Only 'openai' is supported.")

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("LLM PARSER - Extract Structured Test Cases")
    print("=" * 60)

    input_path = "data/intermediate/ocr_text.txt"
    output_path = "data/outputs/testcases.json"

    try:
        if not os.path.exists('.env'):
            print("\n[ERROR]: .env file not found!")
            print("\nCreate a .env file with your API key:")
            print("  OPENAI_API_KEY=sk-proj-your-key-here")
            print("  LLM_PROVIDER=openai")
            print("  LLM_MODEL=gpt-4o-mini")
            exit(1)

        result = parse_test_cases(input_path, output_path)

        test_cases = result.get('test_cases', [])
        print(f"\n[SUCCESS] Extracted {len(test_cases)} test cases")
        print(f"Saved to: {output_path}")
        print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")

        print("\n" + "-" * 60)
        print("TEST CASES FOUND:")
        print("-" * 60)

        for tc in test_cases:
            print(f"\n{tc['test_id']}: {tc['title']}")
            print(f"  Type: {tc['test_type']} | Priority: {tc['priority']}")

    except FileNotFoundError:
        print(f"\n[ERROR]: Input file not found")
        print("Run OCR extraction first: python src/ocr_extractor.py")

    except Exception as e:
        print(f"\n[ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()
