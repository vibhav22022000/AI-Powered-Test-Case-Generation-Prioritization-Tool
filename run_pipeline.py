"""
AI-Powered Test Case Generation & Prioritization Pipeline
Main script to run the complete end-to-end pipeline
"""

import sys
import os
import time
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pdf_generator import generate_sample_qa_doc
from ocr_extractor import extract_text_from_pdf
from llm_parser import parse_test_cases
from risk_scorer import add_risk_scores
from exporter import export_test_cases


def print_header(title):
    print("\n" + "=" * 70)
    print(f"{Fore.CYAN}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    print("=" * 70)


def print_success(msg):
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")


def print_error(msg):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")


def print_info(msg):
    print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} {msg}")


def print_step(step_num, total, desc):
    print(f"\n{Fore.MAGENTA}[STEP {step_num}/{total}]{Style.RESET_ALL} {desc}")


def run_pipeline(skip_pdf=False, skip_llm=False, input_pdf=None):
    """
    Run the complete AI test case generation pipeline

    Args:
        skip_pdf: Skip PDF generation if it already exists
        skip_llm: Skip LLM parsing (use existing testcases.json)
        input_pdf: Path to custom PDF file (skips sample generation)

    Returns:
        dict with pipeline results
    """

    start_time = time.time()

    results = {
        "success": False,
        "steps_completed": [],
        "errors": []
    }

    total_steps = 5

    print_header("AI-POWERED TEST CASE GENERATION & PRIORITIZATION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # STEP 1: Get PDF (custom or generate sample)
        print_step(1, total_steps, "Generate Sample QA Document PDF")

        if input_pdf:
            if not os.path.exists(input_pdf):
                raise FileNotFoundError(f"PDF file not found: {input_pdf}")
            pdf_path = input_pdf
            print_info(f"Using custom PDF: {pdf_path}")
        elif skip_pdf and os.path.exists("data/raw_docs/sample_qa_doc.pdf"):
            pdf_path = "data/raw_docs/sample_qa_doc.pdf"
            print_info(f"Using existing PDF: {pdf_path}")
        else:
            print("Generating realistic QA test plan document...")
            pdf_path = generate_sample_qa_doc()
            print_success(f"PDF created: {pdf_path}")

        results["steps_completed"].append("PDF Generation")

        # STEP 2: OCR / Text Extraction
        print_step(2, total_steps, "Extract Text from PDF (OCR)")

        ocr_output_path = "data/intermediate/ocr_text.txt"
        print(f"Extracting text from: {pdf_path}")

        extracted_text = extract_text_from_pdf(pdf_path, ocr_output_path)
        print_success(f"Text extracted: {len(extracted_text)} characters")
        print_success(f"Saved to: {ocr_output_path}")

        results["steps_completed"].append("OCR Extraction")

        # STEP 3: LLM Parsing
        print_step(3, total_steps, "Parse Test Cases with LLM")

        testcases_path = "data/outputs/testcases.json"

        if skip_llm:
            print_info("Skipping LLM parsing (skip_llm=True)")
            print_info("Using existing testcases.json if available")

            if not os.path.exists(testcases_path):
                raise FileNotFoundError(
                    "No existing testcases.json found. Cannot skip LLM step."
                )
        else:
            if not os.path.exists('.env'):
                raise FileNotFoundError(
                    ".env file not found! Please create .env with your OpenAI API key."
                )

            print("Calling LLM to parse test cases...")
            print_info("This may take 10-30 seconds depending on API response time...")

            parsed_data = parse_test_cases(ocr_output_path, testcases_path)
            num_tests = len(parsed_data.get('test_cases', []))

            print_success(f"Extracted {num_tests} test cases")
            print_success(f"Saved to: {testcases_path}")

        results["steps_completed"].append("LLM Parsing")

        # STEP 4: Risk Scoring
        print_step(4, total_steps, "Calculate Risk Scores & Prioritization")

        scored_path = "data/outputs/testcases_scored.json"

        print("Calculating risk scores based on:")
        print("  - Priority level (40% weight)")
        print("  - Test type (30% weight)")
        print("  - Component risk (20% weight)")
        print("  - Complexity (10% weight)")

        scored_data = add_risk_scores(testcases_path, scored_path)
        test_cases = scored_data.get('test_cases', [])

        risk_counts = {}
        for tc in test_cases:
            cat = tc.get('risk_category', 'UNKNOWN')
            risk_counts[cat] = risk_counts.get(cat, 0) + 1

        print_success(f"Risk scores calculated for {len(test_cases)} test cases")
        print_success(f"Risk distribution: CRITICAL={risk_counts.get('CRITICAL', 0)}, "
                     f"HIGH={risk_counts.get('HIGH', 0)}, "
                     f"MEDIUM={risk_counts.get('MEDIUM', 0)}, "
                     f"LOW={risk_counts.get('LOW', 0)}")

        results["steps_completed"].append("Risk Scoring")

        # STEP 5: Export to JSON & YAML
        print_step(5, total_steps, "Export to JSON & YAML Formats")

        final_json = "data/outputs/testcases_final.json"
        final_yaml = "data/outputs/testcases_final.yaml"

        print("Exporting test cases with metadata...")
        export_result = export_test_cases(scored_path, final_json, final_yaml)

        print_success(f"JSON exported: {final_json} ({export_result['json_size_kb']:.1f} KB)")
        print_success(f"YAML exported: {final_yaml} ({export_result['yaml_size_kb']:.1f} KB)")

        results["steps_completed"].append("Export")

        # Pipeline Complete
        results["success"] = True
        elapsed = time.time() - start_time

        print_header("PIPELINE COMPLETED SUCCESSFULLY")

        print(f"\n{Fore.GREEN}{Style.BRIGHT}All steps completed!{Style.RESET_ALL}")
        print(f"Total time: {elapsed:.1f} seconds")
        print(f"Steps completed: {len(results['steps_completed'])}/{total_steps}")

        print("\n" + "-" * 70)
        print("OUTPUT FILES:")
        print("-" * 70)
        print(f"1. PDF Document:     {pdf_path}")
        print(f"2. OCR Text:         {ocr_output_path}")
        print(f"3. Parsed Tests:     {testcases_path}")
        print(f"4. Scored Tests:     {scored_path}")
        print(f"5. Final JSON:       {final_json}")
        print(f"6. Final YAML:       {final_yaml}")

        print("\n" + "-" * 70)
        print("QUICK STATS:")
        print("-" * 70)
        metadata = export_result['metadata']
        print(f"Total Test Cases:    {metadata['total_test_cases']}")
        print(f"Critical Risk:       {metadata['risk_summary']['critical']}")
        print(f"High Risk:           {metadata['risk_summary']['high']}")
        print(f"Export Date:         {metadata['export_date']}")

        print("\n" + "-" * 70)
        print("NEXT STEPS:")
        print("-" * 70)
        print("1. Review test cases in: data/outputs/testcases_final.json")
        print("2. Import into test management tool (JIRA, TestRail, etc.)")
        print("3. Execute tests in priority order (by risk_score)")
        print("4. Update PDF with your own QA documents and rerun pipeline")

        print("\n" + "=" * 70 + "\n")

        return results

    except Exception as e:
        import traceback
        results["errors"].append(str(e))
        elapsed = time.time() - start_time

        print_header("PIPELINE FAILED")
        print_error(f"{str(e)}")
        print("\n" + "-" * 70)
        print("FULL ERROR TRACEBACK:")
        print("-" * 70)
        traceback.print_exc()

        print(f"\n{Fore.YELLOW}Steps completed: {len(results['steps_completed'])}/{total_steps}{Style.RESET_ALL}")
        for step in results["steps_completed"]:
            print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {step}")

        print(f"\nTotal time: {elapsed:.1f} seconds")

        print("\n" + "-" * 70)
        print("TROUBLESHOOTING:")
        print("-" * 70)

        if ".env" in str(e):
            print("1. Create .env file by copying .env.example")
            print("2. Add your OpenAI API key: OPENAI_API_KEY=sk-proj-...")
            print("3. Get API key from: https://platform.openai.com/api-keys")

        if "testcases.json" in str(e):
            print("1. Make sure previous steps completed successfully")
            print("2. Check that LLM parsing created testcases.json")

        print("\n" + "=" * 70 + "\n")

        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="AI-Powered Test Case Generation & Prioritization Pipeline"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        help="Path to your own PDF file (skips sample generation)"
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip PDF generation if sample_qa_doc.pdf already exists"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM parsing (use existing testcases.json)"
    )

    args = parser.parse_args()

    result = run_pipeline(
        skip_pdf=args.skip_pdf,
        skip_llm=args.skip_llm,
        input_pdf=args.pdf
    )

    sys.exit(0 if result["success"] else 1)
