"""OCR Extractor - Extracts text from PDFs using pdfplumber"""

import pdfplumber
import os


def extract_text_from_pdf(pdf_path, output_path):
    """
    Extract all text from a PDF and save it to a text file

    Args:
        pdf_path: path to the PDF file
        output_path: where to save the extracted text

    Returns:
        the extracted text as a string
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"\nReading PDF: {pdf_path}")

    all_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")

        for i, page in enumerate(pdf.pages, 1):
            print(f"  Processing page {i}...")

            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n\n"
                all_text += "=" * 80 + "\n\n"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(all_text)

    return all_text


if __name__ == "__main__":
    print("=" * 60)
    print("OCR EXTRACTOR - PDF to Text")
    print("=" * 60)

    pdf_file = "data/raw_docs/sample_qa_doc.pdf"
    output_file = "data/intermediate/ocr_text.txt"

    try:
        text = extract_text_from_pdf(pdf_file, output_file)

        print(f"\n[SUCCESS]")
        print(f"Saved to: {output_file}")
        print(f"Characters: {len(text):,}")
        print(f"Lines: {len(text.splitlines()):,}")
        print(f"Size: {os.path.getsize(output_file) / 1024:.1f} KB")

        print("\n" + "-" * 60)
        print("PREVIEW (first 500 chars):")
        print("-" * 60)
        print(text[:500] + "...")

    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nGenerate the PDF first: python src/pdf_generator.py")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise
