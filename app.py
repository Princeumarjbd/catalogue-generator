import streamlit as st
import os
import pandas as pd
from rembg import remove
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import patoolib
import shutil

# --- Website ka Design aur Title ---
st.set_page_config(page_title="Catalogue Generator", page_icon="📄")
st.title("Automated Product Catalogue Generator")
st.write("Upload your CSV and Images (RAR) below to generate a clean, aligned PDF catalogue.")

# --- File Uploaders (Buttons) ---
csv_upload = st.file_uploader("1. Upload CSV File", type=['csv'])
rar_upload = st.file_uploader("2. Upload Images (RAR File)", type=['rar'])

# --- Generate Button ---
if st.button("Generate Catalogue PDF"):
    if csv_upload and rar_upload:
        with st.spinner('Processing... Please wait!'):
            # Temporary files save karna
            with open("temp_data.csv", "wb") as f:
                f.write(csv_upload.getbuffer())
            with open("temp_images.rar", "wb") as f:
                f.write(rar_upload.getbuffer())

            extracted_folder = "temp_extracted_images"
            if os.path.exists(extracted_folder):
                shutil.rmtree(extracted_folder)
            os.makedirs(extracted_folder)

            # 1. Extract RAR
            st.info("Extracting images...")
            patoolib.extract_archive("temp_images.rar", outdir=extracted_folder, verbosity=-1)

            image_dir = extracted_folder
            for root, dirs, files in os.walk(extracted_folder):
                if any(f.lower().endswith(('.png', '.jpg', '.jpeg')) for f in files):
                    image_dir = root
                    break

            # 2. Read CSV
            df = pd.read_csv("temp_data.csv")

            # 3. Process Images
            st.info("Removing backgrounds and aligning products. This may take a minute...")
            processed_images = {}
            CANVAS_SIZE = 800
            MAX_PRODUCT_SIZE = 650 

            for filename in df['image_filename'].unique():
                img_path = os.path.join(image_dir, str(filename).strip())
                if os.path.exists(img_path):
                    input_img = Image.open(img_path).convert("RGBA")
                    output_img = remove(input_img)
                    
                    bbox = output_img.getbbox()
                    if bbox:
                        output_img = output_img.crop(bbox)
                        
                    img_w, img_h = output_img.size
                    ratio = min(MAX_PRODUCT_SIZE / img_w, MAX_PRODUCT_SIZE / img_h)
                    new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                    
                    resized_product = output_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    final_canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 0))
                    
                    paste_x, paste_y = (CANVAS_SIZE - new_w) // 2, (CANVAS_SIZE - new_h) // 2
                    final_canvas.paste(resized_product, (paste_x, paste_y), resized_product)
                    
                    temp_png = f"temp_{str(filename).split('.')[0]}.png"
                    final_canvas.save(temp_png, format="PNG")
                    processed_images[filename] = temp_png

            # 4. Generate PDF
            st.info("Creating Final PDF...")
            pdf_file = "Final_Catalogue.pdf"
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
            st.success("Catalogue Generated Successfully! 🎉")
            
            # --- Download Button ---
            with open(pdf_file, "rb") as pdf:
                st.download_button(label="📥 Download PDF Catalogue", data=pdf, file_name="Catalogue_Final.pdf", mime="application/pdf")
    else:
        st.error("Please upload both CSV and RAR files first.")