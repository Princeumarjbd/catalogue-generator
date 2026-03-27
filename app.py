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
st.set_page_config(page_title="Catalogue Generator Phase 2", page_icon="📄")
st.title("Automated Product Catalogue Generator")
st.write("Upload your CSV, Images (ZIP), and a Logo (PNG) below.")

# --- File Uploaders ---
csv_upload = st.file_uploader("1. Upload CSV File", type=['csv'])
zip_upload = st.file_uploader("2. Upload Images (ZIP File)", type=['zip'])
logo_upload = st.file_uploader("3. Upload Logo (Transparent PNG)", type=['png'])

# --- Placement Dictionary (X, Y Coordinates & Scale) ---
# Yahan hum set karte hain ke logo kahan aur kitna bara lagega
PLACEMENT_RULES = {
    'polo': {'scale': 0.15, 'x_pos': 0.65, 'y_pos': 0.35}, # x=0.65 means wearer's left chest
    't-shirt': {'scale': 0.25, 'x_pos': 0.50, 'y_pos': 0.35}, # x=0.50 means center
    'cap': {'scale': 0.20, 'x_pos': 0.50, 'y_pos': 0.40},
    'bottle': {'scale': 0.30, 'x_pos': 0.50, 'y_pos': 0.60}
}

# --- Generate Button ---
if st.button("Generate Catalogue PDF"):
    if csv_upload and zip_upload:
        with st.spinner('Processing... Please wait!'):
            
            # Read Logo if uploaded
            logo_img = None
            if logo_upload:
                logo_img = Image.open(logo_upload).convert("RGBA")

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
            for root, dirs, files in os.walk(extracted_folder):
                if any(f.lower().endswith(('.png', '.jpg', '.jpeg')) for f in files):
                    image_dir = root
                    break

            # 2. Read CSV
            df = pd.read_csv("temp_data.csv")

            # 3. Process Images
            st.info("Removing backgrounds, adding logos, and aligning...")
            processed_images = {}
            CANVAS_SIZE = 800
            MAX_PRODUCT_SIZE = 650

            for index, row in df.iterrows():
                filename = str(row['image_filename']).strip()
                product_type = str(row.get('Product Type', '')).lower().strip()
                
                img_path = os.path.join(image_dir, filename)
                if os.path.exists(img_path) and filename not in processed_images:
                    
                    # Remove Background
                    input_img = Image.open(img_path).convert("RGBA")
                    output_img = remove(input_img)
                    bbox = output_img.getbbox()
                    if bbox: output_img = output_img.crop(bbox)

                    img_w, img_h = output_img.size
                    ratio = min(MAX_PRODUCT_SIZE / img_w, MAX_PRODUCT_SIZE / img_h)
                    new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                    resized_product = output_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    # --- ADD LOGO LOGIC ---
                    if logo_img and product_type in PLACEMENT_RULES:
                        rule = PLACEMENT_RULES[product_type]
                        l_w, l_h = logo_img.size
                        
                        # Scale logo relative to product width
                        target_l_w = int(new_w * rule['scale'])
                        logo_ratio = target_l_w / l_w
                        target_l_h = int(l_h * logo_ratio)
                        resized_logo = logo_img.resize((target_l_w, target_l_h), Image.Resampling.LANCZOS)
                        
                        # Calculate positions
                        logo_x = int(new_w * rule['x_pos']) - (target_l_w // 2)
                        logo_y = int(new_h * rule['y_pos']) - (target_l_h // 2)
                        
                        # Paste logo onto the product
                        resized_product.paste(resized_logo, (logo_x, logo_y), resized_logo)

                    # Paste product onto final canvas
                    final_canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 0))
                    paste_x, paste_y = (CANVAS_SIZE - new_w) // 2, (CANVAS_SIZE - new_h) // 2
                    final_canvas.paste(resized_product, (paste_x, paste_y), resized_product)

                    temp_png = f"temp_{filename.split('.')[0]}.png"
                    final_canvas.save(temp_png, format="PNG")
                    processed_images[filename] = temp_png

            # 4. Generate PDF
            st.info("Creating Final PDF...")
            pdf_file = "Final_Catalogue_Phase2.pdf"
            c = canvas.Canvas(pdf_file, pagesize=A4)
            width, height = A4
            img_width, img_height = 450, 450
            x_pos, y_pos = (width - img_width) / 2, (height - img_height) / 2 + 50

            for index, row in df.iterrows():
                product_name = str(row['product_name']).strip()
                image_name = str(row['image_filename']).strip()

                if image_name in processed_images:
                    c.drawImage(processed_images[image_name], x_pos, y_pos, width=img_width, height=img_height, mask='auto', preserveAspectRatio=True)
                    c.setFont("Helvetica-Bold", 22)
                    text_width = c.stringWidth(product_name, "Helvetica-Bold", 22)
                    c.drawString((width - text_width) / 2, y_pos - 40, product_name)
                    c.showPage()
            c.save()

            st.success("Catalogue with Logos Generated Successfully! 🎉")
            with open(pdf_file, "rb") as pdf:
                st.download_button("📥 Download PDF", data=pdf, file_name="Catalogue_Phase2.pdf", mime="application/pdf")
    else:
        st.error("Please upload CSV and ZIP files to proceed.")
