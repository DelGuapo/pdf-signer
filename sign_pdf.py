#!/usr/bin/env python3
"""
PDF Signer CLI Application
Usage: python sign_pdf.py <pdf_path> <signature_png_path>
"""

import sys
import tkinter as tk
from tkinter import messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os


class PDFSignerApp:
    def __init__(self, root, pdf_path, signature_path):
        self.root = root
        self.root.title("PDF Signer")
        self.pdf_path = pdf_path
        self.signature_path = signature_path
        self.current_page = 0
        self.pdf_document = None
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        self.signed = False
        
        # Load PDF
        try:
            self.pdf_document = fitz.open(pdf_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF: {e}")
            sys.exit(1)
        
        # Verify signature file exists
        if not os.path.exists(signature_path):
            messagebox.showerror("Error", f"Signature file not found: {signature_path}")
            sys.exit(1)
        
        self.setup_ui()
        self.render_page()
        
        # Show initial prompt
        self.prompt_sign_doc()
    
    def setup_ui(self):
        """Setup the UI components"""
        # Top frame for navigation
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.prev_button = tk.Button(top_frame, text="Previous", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.page_label = tk.Label(top_frame, text="")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.next_button = tk.Button(top_frame, text="Next", command=self.next_page)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        # Canvas for PDF display
        self.canvas = tk.Canvas(self.root, bg="white")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Bind mouse events for rectangle selection
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bottom frame for action buttons (initially hidden)
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.sign_again_button = tk.Button(
            self.bottom_frame, 
            text="Sign Again", 
            command=self.sign_again,
            state=tk.DISABLED
        )
        self.sign_again_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = tk.Button(
            self.bottom_frame, 
            text="Save", 
            command=self.save_pdf,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
    
    def prompt_sign_doc(self):
        """Show 'Sign Doc?' prompt"""
        result = messagebox.askyesno("Sign Doc?", "Sign Doc?")
        if not result:
            self.root.quit()
    
    def render_page(self):
        """Render the current PDF page to canvas"""
        if self.pdf_document is None:
            return
        
        page = self.pdf_document[self.current_page]
        
        # Render page to pixmap
        zoom = 2  # Zoom factor for better quality
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Keep reference to avoid garbage collection
        self.photo = ImageTk.PhotoImage(img)
        
        # Update canvas
        self.canvas.delete("all")
        self.canvas.config(width=pix.width, height=pix.height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Store page dimensions for coordinate conversion
        self.page_width = page.rect.width
        self.page_height = page.rect.height
        self.display_width = pix.width
        self.display_height = pix.height
        
        # Update page label
        self.page_label.config(
            text=f"Page {self.current_page + 1} of {len(self.pdf_document)}"
        )
        
        # Update navigation buttons
        self.prev_button.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_button.config(
            state=tk.NORMAL if self.current_page < len(self.pdf_document) - 1 else tk.DISABLED
        )
    
    def prev_page(self):
        """Navigate to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()
    
    def next_page(self):
        """Navigate to next page"""
        if self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.render_page()
    
    def on_mouse_down(self, event):
        """Handle mouse button down event"""
        self.selection_start = (event.x, event.y)
        self.selection_end = (event.x, event.y)
        
        # Clear any existing selection rectangle
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        if self.selection_start:
            self.selection_end = (event.x, event.y)
            
            # Update rectangle
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            self.selection_rect = self.canvas.create_rectangle(
                x1, y1, x2, y2, 
                outline="red", 
                width=2
            )
    
    def on_mouse_up(self, event):
        """Handle mouse button release event"""
        if self.selection_start:
            self.selection_end = (event.x, event.y)
            
            # Check if we have a valid selection
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:  # Minimum size threshold
                self.insert_signature()
    
    def insert_signature(self):
        """Insert signature at selected coordinates"""
        if not self.selection_start or not self.selection_end:
            return
        
        # Convert display coordinates to PDF coordinates
        x1, y1 = self.selection_start
        x2, y2 = self.selection_end
        
        # Ensure x1 < x2 and y1 < y2
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        # Scale coordinates from display to PDF
        scale_x = self.page_width / self.display_width
        scale_y = self.page_height / self.display_height
        
        pdf_x1 = x1 * scale_x
        pdf_y1 = y1 * scale_y
        pdf_x2 = x2 * scale_x
        pdf_y2 = y2 * scale_y
        
        # Get the current page
        page = self.pdf_document[self.current_page]
        
        # Create rectangle for signature placement
        rect = fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
        
        try:
            # Insert signature image
            page.insert_image(rect, filename=self.signature_path)
            
            # Re-render the page to show the signature
            self.render_page()
            
            # Clear selection
            self.selection_start = None
            self.selection_end = None
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
                self.selection_rect = None
            
            # Enable action buttons
            self.sign_again_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.signed = True
            
            messagebox.showinfo("Success", "Signature added successfully!")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert signature: {e}")
    
    def sign_again(self):
        """Allow user to sign again"""
        self.prompt_sign_doc()
    
    def save_pdf(self):
        """Save the signed PDF"""
        if not self.signed:
            messagebox.showwarning("Warning", "No signature has been added yet.")
            return
        
        # Generate output filename
        base_name = os.path.splitext(self.pdf_path)[0]
        output_path = f"{base_name}_signed.pdf"
        
        try:
            self.pdf_document.save(output_path)
            messagebox.showinfo("Success", f"PDF saved as: {output_path}")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF: {e}")
    
    def __del__(self):
        """Cleanup"""
        if self.pdf_document:
            self.pdf_document.close()


def main():
    """Main entry point"""
    if len(sys.argv) != 3:
        print("Usage: python sign_pdf.py <pdf_path> <signature_png_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    signature_path = sys.argv[2]
    
    # Verify files exist
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if not os.path.exists(signature_path):
        print(f"Error: Signature file not found: {signature_path}")
        sys.exit(1)
    
    # Create Tkinter root window
    root = tk.Tk()
    app = PDFSignerApp(root, pdf_path, signature_path)
    root.mainloop()


if __name__ == "__main__":
    main()
