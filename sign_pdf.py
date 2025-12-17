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


def guessFontSize(strLength, boxWidth, boxHeight):
    """
    Guess the best font size based on string length and box dimensions.
    Uses very aggressive sizing to fit text in small boxes.
    
    Args:
        strLength: Length of the text string
        boxWidth: Width of the bounding box
        boxHeight: Height of the bounding box
    
    Returns:
        Estimated font size in points (minimum 4, maximum 72)
    """
    if strLength == 0:
        return 12
    
    # Very aggressive sizing - assume narrow character width
    # Estimate based on width (assuming average character width is ~0.35 * font_size for tight fit)
    width_based_size = (boxWidth / strLength) / 0.35
    
    # Estimate based on height (use almost full height)
    height_based_size = boxHeight * 0.95
    
    # Use the smaller of the two to ensure text fits
    font_size = min(width_based_size, height_based_size)
    
    # Clamp to minimum and maximum bounds for consistency
    font_size = max(4, min(font_size, 72))
    
    return font_size


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
        self.mode = tk.StringVar(value="View Mode")  # Default mode
        self.text_dialog = None
        
        # Track text boxes for editing/resizing
        self.text_boxes = []  # List of dict: {rect, text, font_size, page, canvas_items}
        self.signatures = []  # List of dict: {rect, page}
        self.selected_textbox = None
        self.resize_handle = None
        self.resize_start = None
        
        # Load PDF
        try:
            self.pdf_document = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to load PDF: {e}")
        
        # Verify signature file exists
        if not os.path.exists(signature_path):
            raise FileNotFoundError(f"Signature file not found: {signature_path}")
        
        self.setup_ui()
        self.render_page()
    
    def setup_ui(self):
        """Setup the UI components"""
        # Top frame for navigation and controls
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Left section - Sign PDF button
        left_frame = tk.Frame(top_frame)
        left_frame.pack(side=tk.LEFT, padx=5)
        
        self.sign_pdf_button = tk.Button(
            left_frame,
            text="Sign PDF",
            command=self.save_signed_pdf,
            state=tk.DISABLED
        )
        self.sign_pdf_button.pack()
        
        # Center section - Pagination
        center_frame = tk.Frame(top_frame)
        center_frame.pack(side=tk.LEFT, expand=True)
        
        self.prev_button = tk.Button(center_frame, text="Previous", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.page_label = tk.Label(center_frame, text="")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.next_button = tk.Button(center_frame, text="Next", command=self.next_page)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        # Right section - Mode selection
        right_frame = tk.Frame(top_frame)
        right_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Label(right_frame, text="Mode:").pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            right_frame,
            text="Sign Mode",
            variable=self.mode,
            value="Sign Mode"
        ).pack(side=tk.LEFT)
        
        tk.Radiobutton(
            right_frame,
            text="Text Mode",
            variable=self.mode,
            value="Text Mode"
        ).pack(side=tk.LEFT)
        
        tk.Radiobutton(
            right_frame,
            text="View Mode",
            variable=self.mode,
            value="View Mode"
        ).pack(side=tk.LEFT)
        
        # Frame for canvas and scrollbars
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Canvas for PDF display
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        
        # Add scrollbars
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for canvas and scrollbars
        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
        v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        h_scrollbar.grid(row=1, column=0, sticky=tk.EW)
        
        # Configure grid weights
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Bind mouse events for rectangle selection
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
    
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
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Configure scroll region to show entire image
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        
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
        
        # Redraw text box controls for current page
        self.draw_textbox_controls()
    
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
        # Convert window coordinates to canvas coordinates (accounts for scrolling)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Check if clicking on text box control buttons
        if self.check_textbox_button_click(canvas_x, canvas_y):
            return
        
        # Check if clicking on a text box border for resizing
        if self.check_textbox_resize_start(canvas_x, canvas_y):
            return
        
        # Don't allow selection in View Mode
        if self.mode.get() == "View Mode":
            return
        
        self.selection_start = (canvas_x, canvas_y)
        self.selection_end = (canvas_x, canvas_y)
        
        # Clear any existing selection rectangle
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        # Convert window coordinates to canvas coordinates (accounts for scrolling)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Handle text box resizing
        if self.resize_handle:
            self.handle_textbox_resize(canvas_x, canvas_y)
            return
        
        # Don't allow selection in View Mode
        if self.mode.get() == "View Mode":
            return
        
        if self.selection_start:
            self.selection_end = (canvas_x, canvas_y)
            
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
        # Convert window coordinates to canvas coordinates (accounts for scrolling)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Finish text box resizing
        if self.resize_handle:
            self.finish_textbox_resize()
            return
        
        # Don't allow selection in View Mode
        if self.mode.get() == "View Mode":
            return
        
        if self.selection_start:
            self.selection_end = (canvas_x, canvas_y)
            
            # Check if we have a valid selection
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:  # Minimum size threshold
                current_mode = self.mode.get()
                
                if current_mode == "Sign Mode":
                    self.insert_signature()
                elif current_mode == "Text Mode":
                    self.show_text_input_dialog()
    
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
            
            # Track signature for regeneration
            self.signatures.append({
                'rect': rect,
                'page': self.current_page
            })
            
            # Re-render the page to show the signature
            self.render_page()
            
            # Clear selection
            self.selection_start = None
            self.selection_end = None
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
                self.selection_rect = None
            
            # Enable Sign PDF button
            self.sign_pdf_button.config(state=tk.NORMAL)
            self.signed = True
            
            # Switch to View Mode
            self.mode.set("View Mode")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert signature: {e}")
    
    def show_text_input_dialog(self):
        """Show dialog for text input with Put Text and Cancel buttons"""
        if not self.selection_start or not self.selection_end:
            return
        
        # Create a custom dialog window
        self.text_dialog = tk.Toplevel(self.root)
        self.text_dialog.title("Enter Text")
        self.text_dialog.geometry("300x150")
        self.text_dialog.transient(self.root)
        self.text_dialog.grab_set()
        
        # Center the dialog
        self.text_dialog.update_idletasks()
        x = (self.text_dialog.winfo_screenwidth() // 2) - (self.text_dialog.winfo_width() // 2)
        y = (self.text_dialog.winfo_screenheight() // 2) - (self.text_dialog.winfo_height() // 2)
        self.text_dialog.geometry(f"+{x}+{y}")
        
        # Label
        tk.Label(self.text_dialog, text="Enter text to add:").pack(pady=10)
        
        # Text entry
        self.text_entry = tk.Entry(self.text_dialog, width=30)
        self.text_entry.pack(pady=10)
        self.text_entry.focus()
        
        # Bind Enter key to Put Text action
        self.text_entry.bind("<Return>", lambda _: self.put_text())
        
        # Button frame
        button_frame = tk.Frame(self.text_dialog)
        button_frame.pack(pady=10)
        
        # Put Text button
        tk.Button(
            button_frame,
            text="Put Text",
            command=self.put_text
        ).pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        tk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_text_input
        ).pack(side=tk.LEFT, padx=5)
    
    def put_text(self):
        """Insert text at selected coordinates"""
        if not hasattr(self, 'text_entry') or not self.text_entry:
            return
        
        text = self.text_entry.get().strip()
        
        if not text:
            messagebox.showwarning("Warning", "Please enter some text.")
            return
        
        # Close the dialog
        self.text_dialog.destroy()
        self.text_dialog = None
        
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
        
        # Calculate box dimensions
        box_width = pdf_x2 - pdf_x1
        box_height = pdf_y2 - pdf_y1
        
        # Get the current page
        page = self.pdf_document[self.current_page]
        
        # Create rectangle for text placement
        rect = fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
        
        try:
            # Calculate font size using aggressive sizing
            font_size = guessFontSize(len(text), box_width, box_height)
            
            # If text is very long and font is extremely small, consider expanding
            # Only expand for text longer than 21 chars with font < 4pt
            baseline_length = 21
            if len(text) > baseline_length and font_size < 4:
                # Box is likely too small for very long text, expand it
                # Calculate center for expansion
                center_x = (pdf_x1 + pdf_x2) / 2
                center_y = (pdf_y1 + pdf_y2) / 2
                
                # Get page dimensions for bounds checking
                page_rect = page.rect
                
                # Try expanding by 1.5x
                expansion_factor = 1.5
                expanded_width = box_width * expansion_factor
                expanded_height = box_height * expansion_factor
                
                # Calculate new coordinates keeping center fixed
                pdf_x1 = center_x - expanded_width / 2
                pdf_y1 = center_y - expanded_height / 2
                pdf_x2 = center_x + expanded_width / 2
                pdf_y2 = center_y + expanded_height / 2
                
                # Clamp to page boundaries
                pdf_x1 = max(0, pdf_x1)
                pdf_y1 = max(0, pdf_y1)
                pdf_x2 = min(page_rect.width, pdf_x2)
                pdf_y2 = min(page_rect.height, pdf_y2)
                
                # Recalculate font size for expanded box
                font_size = guessFontSize(len(text), pdf_x2 - pdf_x1, pdf_y2 - pdf_y1)
                
                # Update rect
                rect = fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
            
            # Insert text with (possibly expanded) box
            page.insert_textbox(
                rect,
                text,
                fontsize=font_size,
                fontname="helv",
                fontfile=None,
                align=fitz.TEXT_ALIGN_LEFT
            )
            
            # Store text box information for later editing
            textbox_data = {
                'rect': rect,
                'text': text,
                'font_size': font_size,
                'page': self.current_page,
                'canvas_items': []
            }
            self.text_boxes.append(textbox_data)
            
            # Re-render the page to show the text
            self.render_page()
            
            # Clear selection
            self.selection_start = None
            self.selection_end = None
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
                self.selection_rect = None
            
            # Enable Sign PDF button
            self.sign_pdf_button.config(state=tk.NORMAL)
            self.signed = True
            
            # Stay in Text Mode to allow adding more text
            # (Do not switch to View Mode)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert text: {e}")
    
    def cancel_text_input(self):
        """Cancel text input and close dialog"""
        if self.text_dialog:
            self.text_dialog.destroy()
            self.text_dialog = None
        
        # Clear selection
        self.selection_start = None
        self.selection_end = None
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
    
    def draw_textbox_controls(self):
        """Draw interactive controls for text boxes on current page"""
        # Remove old canvas items from all textboxes
        for textbox in self.text_boxes:
            for item in textbox['canvas_items']:
                self.canvas.delete(item)
            textbox['canvas_items'] = []
        
        # Draw controls for text boxes on current page
        for textbox in self.text_boxes:
            if textbox['page'] != self.current_page:
                continue
            
            # Convert PDF coordinates to display coordinates
            rect = textbox['rect']
            scale_x = self.display_width / self.page_width
            scale_y = self.display_height / self.page_height
            
            x1 = rect.x0 * scale_x
            y1 = rect.y0 * scale_y
            x2 = rect.x1 * scale_x
            y2 = rect.y1 * scale_y
            
            # Draw border rectangle
            border = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="blue",
                width=2,
                dash=(5, 3)
            )
            textbox['canvas_items'].append(border)
            
            # Draw resize handles (small squares at corners)
            handle_size = 8
            # Bottom-right corner handle
            handle = self.canvas.create_rectangle(
                x2 - handle_size, y2 - handle_size, x2, y2,
                fill="blue",
                outline="white",
                width=1
            )
            textbox['canvas_items'].append(handle)
            
            # Draw + and - buttons above the text box
            button_size = 20
            button_y = y1 - button_size - 5
            
            # + button (right)
            plus_btn_x = x2 - button_size
            plus_btn = self.canvas.create_rectangle(
                plus_btn_x, button_y, plus_btn_x + button_size, button_y + button_size,
                fill="lightgreen",
                outline="darkgreen",
                width=1
            )
            plus_text = self.canvas.create_text(
                plus_btn_x + button_size / 2, button_y + button_size / 2,
                text="+",
                font=("Arial", 14, "bold")
            )
            textbox['canvas_items'].extend([plus_btn, plus_text])
            
            # - button (left of + button)
            minus_btn_x = plus_btn_x - button_size - 5
            minus_btn = self.canvas.create_rectangle(
                minus_btn_x, button_y, minus_btn_x + button_size, button_y + button_size,
                fill="lightcoral",
                outline="darkred",
                width=1
            )
            minus_text = self.canvas.create_text(
                minus_btn_x + button_size / 2, button_y + button_size / 2,
                text="-",
                font=("Arial", 14, "bold")
            )
            textbox['canvas_items'].extend([minus_btn, minus_text])
    
    def check_textbox_button_click(self, canvas_x, canvas_y):
        """Check if a text box control button was clicked"""
        button_size = 20
        
        for textbox in self.text_boxes:
            if textbox['page'] != self.current_page:
                continue
            
            # Convert PDF coordinates to display coordinates
            rect = textbox['rect']
            scale_x = self.display_width / self.page_width
            scale_y = self.display_height / self.page_height
            
            x1 = rect.x0 * scale_x
            y1 = rect.y0 * scale_y
            x2 = rect.x1 * scale_x
            
            button_y = y1 - button_size - 5
            
            # Check + button
            plus_btn_x = x2 - button_size
            if (plus_btn_x <= canvas_x <= plus_btn_x + button_size and
                button_y <= canvas_y <= button_y + button_size):
                self.increase_font_size(textbox)
                return True
            
            # Check - button
            minus_btn_x = plus_btn_x - button_size - 5
            if (minus_btn_x <= canvas_x <= minus_btn_x + button_size and
                button_y <= canvas_y <= button_y + button_size):
                self.decrease_font_size(textbox)
                return True
        
        return False
    
    def increase_font_size(self, textbox):
        """Increase font size of a text box"""
        # Get the page
        page = self.pdf_document[textbox['page']]
        
        # Remove old text
        # Find and remove the text by redrawing the page content
        # We need to regenerate the page from original and reapply all changes
        self.regenerate_page_content(textbox['page'], exclude_textbox=textbox)
        
        # Increase font size
        textbox['font_size'] = min(textbox['font_size'] + 2, 144)
        
        # Re-insert text with new size
        page.insert_textbox(
            textbox['rect'],
            textbox['text'],
            fontsize=textbox['font_size'],
            fontname="helv",
            fontfile=None,
            align=fitz.TEXT_ALIGN_LEFT
        )
        
        # Re-render page
        self.render_page()
    
    def decrease_font_size(self, textbox):
        """Decrease font size of a text box"""
        # Get the page
        page = self.pdf_document[textbox['page']]
        
        # Remove old text
        self.regenerate_page_content(textbox['page'], exclude_textbox=textbox)
        
        # Decrease font size
        textbox['font_size'] = max(textbox['font_size'] - 2, 4)
        
        # Re-insert text with new size
        page.insert_textbox(
            textbox['rect'],
            textbox['text'],
            fontsize=textbox['font_size'],
            fontname="helv",
            fontfile=None,
            align=fitz.TEXT_ALIGN_LEFT
        )
        
        # Re-render page
        self.render_page()
    
    def check_textbox_resize_start(self, canvas_x, canvas_y):
        """Check if starting to resize a text box"""
        handle_size = 8
        
        for textbox in self.text_boxes:
            if textbox['page'] != self.current_page:
                continue
            
            # Convert PDF coordinates to display coordinates
            rect = textbox['rect']
            scale_x = self.display_width / self.page_width
            scale_y = self.display_height / self.page_height
            
            x2 = rect.x1 * scale_x
            y2 = rect.y1 * scale_y
            
            # Check bottom-right handle
            if (x2 - handle_size <= canvas_x <= x2 and
                y2 - handle_size <= canvas_y <= y2):
                self.resize_handle = textbox
                self.resize_start = (canvas_x, canvas_y)
                return True
        
        return False
    
    def handle_textbox_resize(self, canvas_x, canvas_y):
        """Handle text box resizing during drag"""
        if not self.resize_handle or not self.resize_start:
            return
        
        textbox = self.resize_handle
        rect = textbox['rect']
        
        # Calculate new size in display coordinates
        scale_x = self.display_width / self.page_width
        scale_y = self.display_height / self.page_height
        
        x1 = rect.x0 * scale_x
        y1 = rect.y0 * scale_y
        
        # Update display with live preview
        # Clear old controls and redraw with new size
        for item in textbox['canvas_items']:
            self.canvas.delete(item)
        textbox['canvas_items'] = []
        
        # Draw preview rectangle
        preview = self.canvas.create_rectangle(
            x1, y1, canvas_x, canvas_y,
            outline="blue",
            width=2,
            dash=(5, 3)
        )
        textbox['canvas_items'].append(preview)
    
    def finish_textbox_resize(self):
        """Finish resizing a text box"""
        if not self.resize_handle:
            return
        
        textbox = self.resize_handle
        rect = textbox['rect']
        
        # Get current canvas position from the preview rectangle
        if textbox['canvas_items']:
            coords = self.canvas.coords(textbox['canvas_items'][0])
            if len(coords) >= 4:
                # Convert display coordinates back to PDF coordinates
                scale_x = self.page_width / self.display_width
                scale_y = self.page_height / self.display_height
                
                new_x2 = coords[2] * scale_x
                new_y2 = coords[3] * scale_y
                
                # Ensure valid rectangle (prevent negative width/height)
                if new_x2 <= rect.x0 or new_y2 <= rect.y0:
                    # Invalid resize, cancel operation
                    self.resize_handle = None
                    self.resize_start = None
                    self.render_page()
                    return
                
                # Update rect (keep x0, y0 the same)
                new_rect = fitz.Rect(rect.x0, rect.y0, new_x2, new_y2)
                
                # Regenerate page without this textbox
                self.regenerate_page_content(textbox['page'], exclude_textbox=textbox)
                
                # Update textbox rect
                textbox['rect'] = new_rect
                
                # Recalculate font size for new box dimensions
                box_width = new_rect.x1 - new_rect.x0
                box_height = new_rect.y1 - new_rect.y0
                textbox['font_size'] = guessFontSize(len(textbox['text']), box_width, box_height)
                
                # Re-insert text with new rect and font size
                page = self.pdf_document[textbox['page']]
                page.insert_textbox(
                    new_rect,
                    textbox['text'],
                    fontsize=textbox['font_size'],
                    fontname="helv",
                    fontfile=None,
                    align=fitz.TEXT_ALIGN_LEFT
                )
        
        # Clear resize state
        self.resize_handle = None
        self.resize_start = None
        
        # Re-render page
        self.render_page()
    
    def regenerate_page_content(self, page_num, exclude_textbox=None):
        """Regenerate page content excluding a specific textbox
        
        Note: Due to PyMuPDF's API limitations, we must reload the entire PDF
        to remove a specific textbox. We optimize by only processing the target page.
        """
        # Save current page number to restore later
        original_page = self.current_page
        
        # Close and reopen the PDF to get fresh pages
        old_doc = self.pdf_document
        self.pdf_document = fitz.open(self.pdf_path)
        
        # Only process pages that have modifications
        pages_to_process = set()
        for signature in self.signatures:
            pages_to_process.add(signature['page'])
        for textbox in self.text_boxes:
            pages_to_process.add(textbox['page'])
        
        # Reapply modifications to affected pages
        for i in pages_to_process:
            if i >= len(self.pdf_document):
                continue
            page = self.pdf_document[i]
            
            # Reapply signatures on this page
            for signature in self.signatures:
                if signature['page'] == i:
                    page.insert_image(signature['rect'], filename=self.signature_path)
            
            # Reapply textboxes on this page, except excluded one
            for textbox in self.text_boxes:
                if textbox['page'] == i and textbox != exclude_textbox:
                    page.insert_textbox(
                        textbox['rect'],
                        textbox['text'],
                        fontsize=textbox['font_size'],
                        fontname="helv",
                        fontfile=None,
                        align=fitz.TEXT_ALIGN_LEFT
                    )
        
        # Close old document
        old_doc.close()
    
    def save_signed_pdf(self):
        """Save the signed PDF with _SIGNED suffix"""
        if not self.signed:
            messagebox.showwarning("Warning", "No signature or text has been added yet.")
            return
        
        # Generate output filename with _SIGNED suffix (uppercase)
        base_name = os.path.splitext(self.pdf_path)[0]
        output_path = f"{base_name}_SIGNED.pdf"
        
        try:
            # Clear all text box controls from canvas (they won't be saved)
            for textbox in self.text_boxes:
                for item in textbox['canvas_items']:
                    self.canvas.delete(item)
                textbox['canvas_items'] = []
            
            self.pdf_document.save(output_path)
            messagebox.showinfo("Success", f"PDF saved as: {output_path}")
            self.cleanup()
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None


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
    
    try:
        app = PDFSignerApp(root, pdf_path, signature_path)
        root.mainloop()
    except (ValueError, FileNotFoundError) as e:
        messagebox.showerror("Error", str(e))
        sys.exit(1)
    finally:
        # Ensure cleanup happens
        if 'app' in locals():
            app.cleanup()


if __name__ == "__main__":
    main()
