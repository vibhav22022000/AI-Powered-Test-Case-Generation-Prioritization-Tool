"""Gradio UI for AI Test Case Generator"""

import gradio as gr
import os
import json
import tempfile
import shutil
from datetime import datetime

from src.ocr_extractor import extract_text_from_pdf
from src.llm_parser import parse_with_openai
from src.risk_scorer import calculate_risk_score, get_risk_category
from src.exporter import export_test_cases

from dotenv import load_dotenv

load_dotenv()


def process_pdf(pdf_file, api_key=None, model_choice="gpt-5-mini"):
    """Run full pipeline: PDF → OCR → LLM → Risk Score → Export"""

    if pdf_file is None:
        return "Please upload a PDF file.", None, None, None

    # Use provided API key or fall back to environment variable
    openai_key = api_key.strip() if api_key and api_key.strip() else os.getenv('OPENAI_API_KEY')

    if not openai_key:
        return "OpenAI API key required. Enter it above or set OPENAI_API_KEY in .env file.", None, None, None

    try:
        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp(prefix="testcase_")

        # Step 1: Extract text from PDF
        ocr_output = os.path.join(temp_dir, "ocr_text.txt")
        extracted_text = extract_text_from_pdf(pdf_file.name, ocr_output)

        if not extracted_text.strip():
            return "Could not extract text from PDF. Make sure it contains readable text.", None, None, None

        # Step 2: Parse with LLM
        model = model_choice if model_choice else "gpt-5-mini"
        parsed_data = parse_with_openai(extracted_text, openai_key, model)

        test_cases = parsed_data.get('test_cases', [])

        if not test_cases:
            return "No test cases found in the document.", None, None, None

        # Step 3: Add risk scores
        for tc in test_cases:
            score = calculate_risk_score(tc)
            tc['risk_score'] = score
            tc['risk_category'] = get_risk_category(score)

        # Sort by risk score (highest first)
        test_cases.sort(key=lambda x: x['risk_score'], reverse=True)

        # Add execution order
        for i, tc in enumerate(test_cases, 1):
            tc['execution_order'] = i

        # Step 4: Export to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_output = os.path.join(temp_dir, f"testcases_{timestamp}.json")
        yaml_output = os.path.join(temp_dir, f"testcases_{timestamp}.yaml")

        # Save intermediate scored JSON
        scored_json = os.path.join(temp_dir, "testcases_scored.json")
        with open(scored_json, 'w', encoding='utf-8') as f:
            json.dump({'test_cases': test_cases}, f, indent=2)

        # Export final files
        export_test_cases(scored_json, json_output, yaml_output)

        # Build results table for display
        table_data = []
        for tc in test_cases:
            table_data.append([
                tc.get('execution_order', ''),
                tc.get('test_id', ''),
                tc.get('title', '')[:50] + ('...' if len(tc.get('title', '')) > 50 else ''),
                tc.get('test_type', ''),
                tc.get('priority', ''),
                tc.get('risk_score', 0),
                tc.get('risk_category', '')
            ])

        # Build status message
        risk_counts = {}
        for tc in test_cases:
            cat = tc.get('risk_category', 'UNKNOWN')
            risk_counts[cat] = risk_counts.get(cat, 0) + 1

        status = f"Successfully extracted {len(test_cases)} test cases!\n"
        status += f"Model used: {model}\n\n"
        status += "Risk Distribution:\n"
        for cat in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = risk_counts.get(cat, 0)
            status += f"  • {cat}: {count}\n"

        return status, table_data, json_output, yaml_output

    except FileNotFoundError as e:
        return f"File error: {str(e)}", None, None, None
    except ValueError as e:
        return f"API Error: {str(e)}", None, None, None
    except Exception as e:
        return f"Error: {str(e)}", None, None, None


def create_ui():
    """Create and configure the Gradio interface"""

    with gr.Blocks(
        title="AI Test Case Generator",
        theme=gr.themes.Soft(),
        css="""
        .main-title { text-align: center; margin-bottom: 1rem; }
        .status-box { font-family: monospace; }
        """
    ) as app:

        gr.Markdown(
            """
            # AI Test Case Generator

            Upload a QA document (PDF) and extract structured, prioritized test cases using AI.

            **Pipeline:** PDF → Text Extraction → LLM Parsing → Risk Scoring → Export
            """,
            elem_classes="main-title"
        )

        with gr.Row():
            with gr.Column(scale=1):
                # Input section
                gr.Markdown("### 1. Upload & Configure")

                pdf_input = gr.File(
                    label="Upload QA Document (PDF)",
                    file_types=[".pdf"],
                    type="filepath"
                )

                api_key_input = gr.Textbox(
                    label="OpenAI API Key (optional if set in .env)",
                    placeholder="sk-...",
                    type="password"
                )

                model_dropdown = gr.Dropdown(
                    label="Select GPT Model",
                    choices=[
                        "gpt-5",
                        "gpt-5-mini",
                        "gpt-5-nano",
                        "gpt-5-reasoning",
                        "gpt-4.1",
                        "gpt-4.1-mini",
                        "gpt-4.1-nano",
                        "gpt-4o",
                        "gpt-4o-mini",
                        "gpt-4o-reasoning",
                        "o3",
                        "o3-mini",
                        "o1",
                        "o1-mini",
                    ],
                    value="gpt-5-mini",
                    info="Choose the model for parsing test cases"
                )

                process_btn = gr.Button(
                    "Process Document",
                    variant="primary",
                    size="lg"
                )

                gr.Markdown(
                    """
                    **Model Tips:**
                    - `gpt-5-nano` - Fastest & cheapest, simple docs
                    - `gpt-5-mini` - Fast & cost-effective (default)
                    - `gpt-5` - Flagship, best quality
                    - `gpt-5-reasoning` - Deep logic & complex docs
                    - `gpt-4o-reasoning` - Strong reasoning variant
                    """
                )

            with gr.Column(scale=1):
                # Status section
                gr.Markdown("### 2. Processing Status")

                status_output = gr.Textbox(
                    label="Status",
                    lines=8,
                    interactive=False,
                    elem_classes="status-box"
                )

        gr.Markdown("### 3. Extracted Test Cases")

        results_table = gr.Dataframe(
            headers=["#", "ID", "Title", "Type", "Priority", "Risk Score", "Risk Level"],
            datatype=["number", "str", "str", "str", "str", "number", "str"],
            label="Test Cases (sorted by risk)",
            wrap=True,
            interactive=False
        )

        gr.Markdown("### 4. Download Results")

        with gr.Row():
            json_download = gr.File(label="JSON Output", interactive=False)
            yaml_download = gr.File(label="YAML Output", interactive=False)

        # Connect the process button
        process_btn.click(
            fn=process_pdf,
            inputs=[pdf_input, api_key_input, model_dropdown],
            outputs=[status_output, results_table, json_download, yaml_download]
        )

        # Example section
        gr.Markdown(
            """
            ---
            ### How It Works

            1. **Upload** a PDF containing test cases or QA documentation
            2. **Text Extraction** pulls all readable text from the PDF
            3. **AI Parsing** uses GPT to structure test cases with steps, priorities, and categories
            4. **Risk Scoring** calculates priority based on test type, components, and complexity
            5. **Export** provides JSON and YAML files for integration with test management tools

            **Supported Test Types:** Functional, Security, Performance, Integration, UI/UX, Error Handling, Edge Case
            """
        )

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7860
    )
