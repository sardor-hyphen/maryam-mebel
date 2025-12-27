import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import os
from tkinter import filedialog

class PhotoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Photo Editor")
        self.root.geometry("1200x800")
        
        # Set CustomTkinter appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize variables
        self.original_image = None
        self.display_image = None
        self.processed_image = None
        self.brush_size = 5
        self.brush_color = "red"
        self.drawing = False
        self.last_x, self.last_y = 0, 0
        self.current_tool = "move"  # move, erase, draw, line
        self.line_start = None
        
        # Create UI
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Toolbar frame
        self.toolbar_frame = ctk.CTkFrame(self.main_frame)
        self.toolbar_frame.pack(fill="x", padx=5, pady=5)
        
        # Tool buttons
        self.btn_open = ctk.CTkButton(self.toolbar_frame, text="Open Image", command=self.open_image)
        self.btn_open.pack(side="left", padx=5, pady=5)
        
        self.btn_save = ctk.CTkButton(self.toolbar_frame, text="Save Image", command=self.save_image)
        self.btn_save.pack(side="left", padx=5, pady=5)
        
        # Tools
        self.btn_move = ctk.CTkButton(self.toolbar_frame, text="Move", command=lambda: self.set_tool("move"))
        self.btn_move.pack(side="left", padx=5, pady=5)
        
        self.btn_erase = ctk.CTkButton(self.toolbar_frame, text="Erase", command=lambda: self.set_tool("erase"))
        self.btn_erase.pack(side="left", padx=5, pady=5)
        
        self.btn_sharpen = ctk.CTkButton(self.toolbar_frame, text="Auto Sharpen", command=self.auto_sharpen)
        self.btn_sharpen.pack(side="left", padx=5, pady=5)
        
        self.btn_enhance = ctk.CTkButton(self.toolbar_frame, text="Auto Enhance", command=self.auto_enhance)
        self.btn_enhance.pack(side="left", padx=5, pady=5)
        
        self.btn_draw = ctk.CTkButton(self.toolbar_frame, text="Draw", command=lambda: self.set_tool("draw"))
        self.btn_draw.pack(side="left", padx=5, pady=5)
        
        self.btn_line = ctk.CTkButton(self.toolbar_frame, text="Draw Line", command=lambda: self.set_tool("line"))
        self.btn_line.pack(side="left", padx=5, pady=5)
        
        # Brush size slider
        self.brush_size_label = ctk.CTkLabel(self.toolbar_frame, text="Brush Size:")
        self.brush_size_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.brush_size_slider = ctk.CTkSlider(self.toolbar_frame, from_=1, to=50, command=self.change_brush_size)
        self.brush_size_slider.set(self.brush_size)
        self.brush_size_slider.pack(side="left", padx=5, pady=5)
        
        self.brush_size_value = ctk.CTkLabel(self.toolbar_frame, text=str(self.brush_size))
        self.brush_size_value.pack(side="left", padx=5, pady=5)
        
        # Color picker
        self.color_button = ctk.CTkButton(self.toolbar_frame, text="Color", command=self.choose_color, fg_color=self.brush_color)
        self.color_button.pack(side="left", padx=5, pady=5)
        
        # Reset button
        self.btn_reset = ctk.CTkButton(self.toolbar_frame, text="Reset", command=self.reset_image)
        self.btn_reset.pack(side="right", padx=5, pady=5)
        
        # Image display frame
        self.image_frame = ctk.CTkFrame(self.main_frame)
        self.image_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Canvas for image display
        self.canvas = ctk.CTkCanvas(self.image_frame, bg="gray20")
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        
        # Status bar
        self.status_bar = ctk.CTkLabel(self.main_frame, text="Ready", anchor="w")
        self.status_bar.pack(fill="x", padx=5, pady=(0, 5))
        
    def set_tool(self, tool):
        self.current_tool = tool
        self.status_bar.configure(text=f"Tool: {tool.capitalize()}")
        
    def change_brush_size(self, value):
        self.brush_size = int(float(value))
        self.brush_size_value.configure(text=str(self.brush_size))
        
    def choose_color(self):
        # For simplicity, we'll cycle through some colors
        colors = ["red", "blue", "green", "yellow", "white", "black", "purple", "orange"]
        current_index = colors.index(self.brush_color) if self.brush_color in colors else 0
        self.brush_color = colors[(current_index + 1) % len(colors)]
        self.color_button.configure(fg_color=self.brush_color)
        
    def open_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if file_path:
            try:
                # Open image with PIL
                self.original_image = Image.open(file_path)
                self.processed_image = self.original_image.copy()
                self.display_image = self.original_image.copy()
                self.show_image()
                self.status_bar.configure(text=f"Opened: {os.path.basename(file_path)}")
            except Exception as e:
                self.status_bar.configure(text=f"Error opening image: {str(e)}")
                
    def save_image(self):
        if self.processed_image:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if file_path:
                try:
                    self.processed_image.save(file_path)
                    self.status_bar.configure(text=f"Saved: {os.path.basename(file_path)}")
                except Exception as e:
                    self.status_bar.configure(text=f"Error saving image: {str(e)}")
        else:
            self.status_bar.configure(text="No image to save")
            
    def show_image(self):
        if self.display_image:
            # Resize image to fit canvas while maintaining aspect ratio
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:  # Check if canvas has been rendered
                img_width, img_height = self.display_image.size
                
                # Calculate scaling factor
                scale_w = canvas_width / img_width
                scale_h = canvas_height / img_height
                scale = min(scale_w, scale_h)
                
                # Calculate new dimensions
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # Resize image
                resized_img = self.display_image.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to PhotoImage
                self.photo_img = ImageTk.PhotoImage(resized_img)
                
                # Clear canvas and display image
                self.canvas.delete("all")
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.canvas.create_image(x, y, anchor="nw", image=self.photo_img)
                
    def reset_image(self):
        if self.original_image:
            self.processed_image = self.original_image.copy()
            self.display_image = self.original_image.copy()
            self.show_image()
            self.status_bar.configure(text="Image reset to original")
            
    def start_draw(self, event):
        if not self.processed_image:
            return
            
        self.drawing = True
        self.last_x, self.last_y = event.x, event.y
        
        if self.current_tool == "line":
            self.line_start = (event.x, event.y)
            
    def draw(self, event):
        if not self.drawing or not self.processed_image:
            return
            
        if self.current_tool == "erase":
            self.erase_at(event.x, event.y)
        elif self.current_tool == "draw":
            self.draw_on_image(self.last_x, self.last_y, event.x, event.y)
        elif self.current_tool == "line":
            # For line tool, we'll draw a preview line
            pass
            
        self.last_x, self.last_y = event.x, event.y
        
    def stop_draw(self, event):
        if not self.drawing or not self.processed_image:
            return
            
        self.drawing = False
        
        if self.current_tool == "line" and self.line_start:
            self.draw_line(self.line_start[0], self.line_start[1], event.x, event.y)
            self.line_start = None
            
        # Update display
        self.convert_pil_to_display()
        self.show_image()
        
    def erase_at(self, x, y):
        if not self.processed_image:
            return
            
        # Convert canvas coordinates to image coordinates
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = self.processed_image.size
        
        # Calculate scaling factor
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        scale = min(scale_w, scale_h)
        
        # Calculate image coordinates
        img_x = int((x - (canvas_width - img_width * scale) // 2) / scale)
        img_y = int((y - (canvas_height - img_height * scale) // 2) / scale)
        
        # Create a mask for erasing
        mask = Image.new("L", self.processed_image.size, 255)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((img_x - self.brush_size, img_y - self.brush_size, 
                     img_x + self.brush_size, img_y + self.brush_size), fill=0)
        
        # Apply mask to make area transparent (if image has alpha) or white
        if self.processed_image.mode == "RGBA":
            # For RGBA images, make erased area transparent
            erased_area = Image.new("RGBA", self.processed_image.size, (255, 255, 255, 0))
            self.processed_image = Image.composite(erased_area, self.processed_image, mask)
        else:
            # For RGB images, make erased area white
            erased_area = Image.new("RGB", self.processed_image.size, (255, 255, 255))
            self.processed_image = Image.composite(erased_area, self.processed_image, mask)
            
    def draw_on_image(self, x1, y1, x2, y2):
        if not self.processed_image:
            return
            
        # Convert canvas coordinates to image coordinates
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = self.processed_image.size
        
        # Calculate scaling factor
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        scale = min(scale_w, scale_h)
        
        # Calculate image coordinates
        img_x1 = int((x1 - (canvas_width - img_width * scale) // 2) / scale)
        img_y1 = int((y1 - (canvas_height - img_height * scale) // 2) / scale)
        img_x2 = int((x2 - (canvas_width - img_width * scale) // 2) / scale)
        img_y2 = int((y2 - (canvas_height - img_height * scale) // 2) / scale)
        
        # Draw on image
        from PIL import ImageDraw
        draw = ImageDraw.Draw(self.processed_image)
        draw.line((img_x1, img_y1, img_x2, img_y2), fill=self.brush_color, width=self.brush_size)
        
    def draw_line(self, x1, y1, x2, y2):
        if not self.processed_image:
            return
            
        # Convert canvas coordinates to image coordinates
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = self.processed_image.size
        
        # Calculate scaling factor
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        scale = min(scale_w, scale_h)
        
        # Calculate image coordinates
        img_x1 = int((x1 - (canvas_width - img_width * scale) // 2) / scale)
        img_y1 = int((y1 - (canvas_height - img_height * scale) // 2) / scale)
        img_x2 = int((x2 - (canvas_width - img_width * scale) // 2) / scale)
        img_y2 = int((y2 - (canvas_height - img_height * scale) // 2) / scale)
        
        # Draw line on image
        from PIL import ImageDraw
        draw = ImageDraw.Draw(self.processed_image)
        draw.line((img_x1, img_y1, img_x2, img_y2), fill=self.brush_color, width=self.brush_size)
        
    def convert_pil_to_display(self):
        """Convert processed PIL image to displayable format"""
        self.display_image = self.processed_image.copy()
        
    def auto_sharpen(self):
        if not self.processed_image:
            self.status_bar.configure(text="No image to sharpen")
            return
            
        try:
            # Apply sharpening using PIL
            enhancer = ImageEnhance.Sharpness(self.processed_image)
            self.processed_image = enhancer.enhance(2.0)  # Increase sharpness by 2x
            self.convert_pil_to_display()
            self.show_image()
            self.status_bar.configure(text="Auto sharpen applied")
        except Exception as e:
            self.status_bar.configure(text=f"Error sharpening image: {str(e)}")
            
    def auto_enhance(self):
        if not self.processed_image:
            self.status_bar.configure(text="No image to enhance")
            return
            
        try:
            # Apply multiple enhancements
            # Enhance color
            color_enhancer = ImageEnhance.Color(self.processed_image)
            self.processed_image = color_enhancer.enhance(1.2)
            
            # Enhance contrast
            contrast_enhancer = ImageEnhance.Contrast(self.processed_image)
            self.processed_image = contrast_enhancer.enhance(1.1)
            
            # Enhance brightness
            brightness_enhancer = ImageEnhance.Brightness(self.processed_image)
            self.processed_image = brightness_enhancer.enhance(1.1)
            
            self.convert_pil_to_display()
            self.show_image()
            self.status_bar.configure(text="Auto enhance applied")
        except Exception as e:
            self.status_bar.configure(text=f"Error enhancing image: {str(e)}")

if __name__ == "__main__":
    # Try to import required modules
    try:
        from PIL import ImageDraw
    except ImportError:
        print("Installing required packages...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "customtkinter", "opencv-python"])
        from PIL import ImageDraw
    
    root = ctk.CTk()
    app = PhotoEditor(root)
    root.mainloop()