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
- **Mode Selection**: Choose between three modes:
  - **Sign Mode**: Drag to select a rectangle and place your signature
  - **Text Mode**: Drag to select a rectangle and add custom text with auto-sized font
  - **View Mode**: View the PDF without making changes (default mode)
- **Interactive Signing**: Drag to select a rectangle on the PDF where you want to place your signature
- **Enhanced Text Features**:
  - **Resizable Text Boxes**: After adding text, a blue dashed border appears with a resize handle at the bottom-right corner
  - **Font Size Controls**: Each text box has "+" and "-" buttons above it to increase or decrease font size
  - **Persistent Text Mode**: Stay in Text Mode after adding text to quickly add more text boxes
  - **Visual-Only Controls**: Borders and controls are not saved to the final PDF
- **Text Addition**: Add custom text to the PDF with automatic font size calculation
- **Signature Placement**: The signature image will be stretched to fit the selected rectangle
- **Multi-Page Support**: Navigate through all pages of the PDF and add signatures or text to any page
- **Auto-Safe Mode**: After placing a signature, the app automatically switches to View Mode to prevent accidental additions
- **Sign PDF Button**: Save the signed/edited PDF with "_SIGNED" suffix (e.g., `document_SIGNED.pdf`)

## How It Works

1. Run the script with your PDF and signature image paths
2. A window will open asking "Sign Doc?"
3. The PDF will be displayed in a canvas
4. Select a mode from the mode radio buttons (Sign Mode, Text Mode, or View Mode)
5. In **Sign Mode**: Click and drag to select a rectangle where you want to place your signature. The signature will be inserted and the mode automatically switches to View Mode
6. In **Text Mode**: Click and drag to select a rectangle where you want to add text. A dialog will appear asking you to enter the text. Click "Put Text" to add it or "Cancel" to dismiss. After adding text:
   - The mode stays in Text Mode so you can add more text boxes
   - A blue dashed border appears around your text box
   - Use the "+" and "-" buttons above the text box to adjust font size
   - Click and drag the blue square at the bottom-right corner to resize the text box
7. Use the "Sign PDF" button to save the signed/edited PDF
8. The signed PDF will be saved as `{original_filename}_SIGNED.pdf`
9. Note: The borders, buttons, and resize handles are visual aids only and will not appear in the saved PDF
