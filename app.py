import streamlit as st
import os
import pandas as pd
from rembg import remove
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import zipfile
import shutil

# --- Website Design ---
st.set_page_config(page_title="Phase 3: Automated Catalogue", page_icon="📄")
st.title("Automated Grid-Based Catalogue Generator")
st.write("Upload your Master CSV and Images (ZIP) to generate the final catalogue.")

# --- File Uploaders ---
csv_upload = st.file_uploader("1. Upload Master CSV File", type=['csv'])
zip_upload = st.file_uploader("2. Upload Final Images (ZIP File)", type=['zip'])

# --- Generate Button ---
if st.button("Generate Catalogue PDF"):
    if csv_upload and zip_upload:
        with st.spinner('Building grid layout and compiling PDF... Please wait!'):
            
            # Save temporary files
            with open("temp_data.csv", "wb") as f: f.write(csv_upload.getbuffer())
            with open("temp_images.zip", "wb") as f: f.write(zip_upload.getbuffer())
                
            extracted_folder = "temp_extracted_images"
            if os.path.exists(extracted_folder): shutil.rmtree(extracted_folder)
            os.makedirs(extracted_folder)

            # 1. Extract ZIP
            st.info("Extracting images...")
            with zipfile.ZipFile("temp_images.zip", 'r') as zip_ref:
                zip_ref.extractall(extracted_folder)
                
            image_dir = extracted_folder
            # Find the actual folder containing images
            for root, dirs, files in os.walk(extracted_folder):
                if any(f.lower().endswith(('.png', '.jpg', '.jpeg')) for f in files):
                    image_dir = root
                    break

            # 2. Read CSV 
            df = pd.read_csv("temp_data.csv")
            df.columns = df.columns.str.strip()

            # 3. Process Images
            st.info("Formatting images for uniform scaling...")
            processed_images = {}
            CANVAS_SIZE = 600
            MAX_PRODUCT_SIZE = 450

            for index, row in df.iterrows():
                filename = str(row.get('Image File', '')).strip()
                
                # SAFETY CHECK: Skip empty rows or 'nan' values in CSV
                if not filename or filename.lower() == 'nan':
                    continue
                
                img_path = os.path.join(image_dir, filename)
                
                # SAFETY CHECK: Ensure it is actually a file and not a directory
                if os.path.isfile(img_path) and filename not in processed_images:
                    
                    try:
                        # Remove Background to ensure clean whitespace
                        input_img = Image.open(img_path).convert("RGBA")
                        output_img = remove(input_img)
                        bbox = output_img.getbbox()
                        if bbox: output_img = output_img.crop(bbox)

                        img_w, img_h = output_img.size
                        ratio = min(MAX_PRODUCT_SIZE / img_w, MAX_PRODUCT_SIZE / img_h)
                        new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                        resized_product = output_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                        # Center product on square canvas for uniform grid weight
                        final_canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 0))
                        paste_x, paste_y = (CANVAS_SIZE - new_w) // 2, (CANVAS_SIZE - new_h) // 2
                        final_canvas.paste(resized_product, (paste_x, paste_y), resized_product)

                        temp_png = f"temp_{filename.split('.')[0]}.png"
                        final_canvas.save(temp_png, format="PNG")
                        processed_images[filename] = temp_png
                    except Exception as e:
                        # If an image is corrupted, just skip it and don't crash the whole app
                        continue

            # 4. Generate Multi-Page Grid PDF
            st.info("Constructing Multi-Page PDF...")
            pdf_file = "Final_Catalogue_Phase3.pdf"
            c = canvas.Canvas(pdf_file, pagesize=A4)
            width, height = A4
            
            # Grid Layout Coordinates (4 spots)
            img_size = 230
            grid_positions = [
                (45, height - 340),              # Top Left
                (width / 2 + 25, height - 340),  # Top Right
                (45, 130),                       # Bottom Left
                (width / 2 + 25, 130)            # Bottom Right
            ]
            
            item_count = 0
            
            for index, row in df.iterrows():
                product_name = str(row.get('Product Name', '')).strip()
                sku = str(row.get('SKU', '')).strip()
                image_name = str(row.get('Image File', '')).strip()

                if not image_name or image_name.lower() == 'nan':
                    continue

                if image_name in processed_images:
                    if item_count > 0 and item_count % 4 == 0:
                        c.showPage()
                        item_count = 0 
                    
                    pos_x, pos_y = grid_positions[item_count]
                    
                    # Draw Product Image
                    c.drawImage(processed_images[image_name], pos_x, pos_y, width=img_size, height=img_size, mask='auto', preserveAspectRatio=True)
                    
                    # Draw Product Name (Bold)
                    c.setFont("Helvetica-Bold", 12)
                    name_width = c.stringWidth(product_name, "Helvetica-Bold", 12)
                    name_x = pos_x + (img_size - name_width) / 2
                    c.drawString(name_x, pos_y - 20, product_name)
                    
                    # Draw SKU instead of Price (Regular)
                    if sku and sku.lower() != 'nan':
                        c.setFont("Helvetica", 10)
                        sku_text = f"SKU: {sku}"
                        sku_width = c.stringWidth(sku_text, "Helvetica", 10)
                        sku_x = pos_x + (img_size - sku_width) / 2
                        c.setFillColorRGB(0.3, 0.3, 0.3) 
                        c.drawString(sku_x, pos_y - 35, sku_text)
                        c.setFillColorRGB(0, 0, 0)
                    
                    item_count += 1
            
            c.save()

            st.success("Phase 3 Grid Catalogue Generated Successfully! 🎉")
            with open(pdf_file, "rb") as pdf:
                st.download_button("📥 Download Final PDF", data=pdf, file_name="Catalogue_Phase3_Final.pdf", mime="application/pdf")
    else:
        st.error("Please upload CSV and ZIP files to proceed.")
