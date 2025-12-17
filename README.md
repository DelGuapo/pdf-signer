# pdf-signer
Sign PDFs with a graphical signature using a simple CLI interface.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python sign_pdf.py <pdf_path> <signature_png_path>
```

### Arguments
- `pdf_path`: Path to the PDF file you want to sign
- `signature_png_path`: Path to your signature image (PNG format)

### Example

```bash
python sign_pdf.py document.pdf signature.png
```

## Features

- **PDF Viewer**: Display PDF pages with navigation controls (Previous/Next buttons)
- **Interactive Signing**: Drag to select a rectangle on the PDF where you want to place your signature
- **Signature Placement**: The signature image will be stretched to fit the selected rectangle
- **Multi-Page Support**: Navigate through all pages of the PDF and sign on any page
- **Sign Again**: After placing a signature, you can add more signatures to the same or different pages
- **Save**: Save the signed PDF with "_signed" suffix (e.g., `document_signed.pdf`)

## How It Works

1. Run the script with your PDF and signature image paths
2. A window will open asking "Sign Doc?"
3. The PDF will be displayed in a canvas
4. Click and drag to select a rectangle where you want to place your signature
5. The signature will be inserted at the selected location
6. Use "Sign Again" to add more signatures or "Save" to save the signed PDF
7. The signed PDF will be saved as `{original_filename}_signed.pdf`
