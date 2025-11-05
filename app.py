import streamlit as st
from pymongo import MongoClient
import tempfile
from upload_image import upload_image_to_cloudinary
from datetime import datetime
import pandas as pd
import random, string
import os

# ------------------ MongoDB ------------------
def get_db():
    url = os.getenv("MONGO_URL")
    client = MongoClient(url)
    db = client["handbook"]
    return db

db = get_db()
collection = db["errors"]

# ------------------ Streamlit config ------------------
st.set_page_config(page_title="Handbook for RYOBI Products", layout="wide")
st.title("Handbook for RYOBI Products")

tab1, tab2, tab3 = st.tabs(["➕ Thêm lỗi mới", "🔍 Tra cứu lỗi", "📘 Quy Trình"])

# ==========================================================
# 🧩 TAB 1: THÊM LỖI MỚI
# ==========================================================
with tab1:
    st.subheader("Thêm lỗi sản phẩm mới")

    def generate_error_code(model, timestamp):
        """Sinh mã lỗi tự động dựa trên model + ngày tháng + ký tự ngẫu nhiên"""
        try:
            model_part = model[3:6] if len(model) >= 6 else model
            date_obj = datetime.strptime(timestamp, "%Y-%m-%d")
            month_letter = chr(64 + date_obj.month)
            day = str(date_obj.day).zfill(2)
            random_part = ''.join(random.choices(string.ascii_uppercase, k=3))
            return f"{model_part}{month_letter}{day}{random_part}"
        except Exception as e:
            print("Lỗi tạo mã:", e)
            return "ERR000"

    model = st.text_input("Model Name", placeholder="VD: 030333011")
    timestamp = st.text_input("Timestamp (YYYY-MM-DD)", placeholder="VD: 2025-10-12")

    if model and timestamp:
        try:
            datetime.strptime(timestamp, "%Y-%m-%d")
            auto_error_code = generate_error_code(model, timestamp)
            st.text_input("Defect Mode (auto)", value=auto_error_code, disabled=True)
        except ValueError:
            st.error("⚠️ Định dạng ngày không hợp lệ! Vui lòng nhập dạng YYYY-MM-DD.")
            auto_error_code = ""
    else:
        auto_error_code = ""

    description = st.text_area("Description")
    root_cause = st.text_area("Root Cause")
    solution = st.text_area("Short-Term Action")
    improvement = st.text_area("Long-Term Action")

    image_files = st.file_uploader("Chọn hình ảnh lỗi", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    pdf_file = st.file_uploader("📎 Upload file báo cáo (PDF)", type=["pdf"])

    if st.button("💾 Lưu vào database"):
        if not all([model, auto_error_code, description]):
            st.error("⚠️ Cần nhập ít nhất model, timestamp và mô tả lỗi!")
        else:
            image_urls = []
            if image_files:
                for image_file in image_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(image_file.getbuffer())
                        tmp_path = tmp.name
                    image_url = upload_image_to_cloudinary(tmp_path)
                    if image_url:
                        image_urls.append(image_url)
                if image_urls:
                    st.success(f"📸 Đã upload {len(image_urls)} ảnh thành công!")
                else:
                    st.warning("⚠️ Không có ảnh nào được upload thành công.")
            else:
                image_urls = []

            pdf_url = ""
            if pdf_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.getbuffer())
                    tmp_path = tmp.name
                pdf_url = upload_image_to_cloudinary(tmp_path)
                if pdf_url:
                    st.success("📄 Upload file PDF thành công!")
                else:
                    st.warning("⚠️ Upload PDF thất bại.")

            new_error = {
                "model": model,
                "error_code": auto_error_code,
                "description": description,
                "root_cause": root_cause,
                "solution": solution,
                "improvement": improvement,
                "timestamp": timestamp,
                "images": image_urls,  # đổi thành list
                "pdf_report": pdf_url
            }

            collection.insert_one(new_error)
            st.success(f"✅ Đã thêm lỗi {auto_error_code} cho model {model}")

# ==========================================================
# 🔍 TAB 2: TRA CỨU LỖI
# ==========================================================
with tab2:
    st.subheader("Tra cứu mã lỗi hoặc model")

    search_model = st.text_input("Nhập model cần tra cứu:")
    if search_model:
        cursor = collection.find({"model": search_model})
        data = list(cursor)
        if data:
            for d in data:
                d.pop("_id", None)
            df = pd.DataFrame(data)
            df1 = df.drop(columns=["image", "images", "pdf_report"], errors='ignore')
            st.dataframe(df1)
        else:
            st.warning("Không tìm thấy dữ liệu cho model này.")

    search_code = st.text_input("Nhập mã lỗi cụ thể (VD: 333J12ABC):")
    if search_code:
        result = collection.find_one({"error_code": search_code})
        if result:
            st.markdown(f"### 📘 Model: `{result['model']}`")
            st.markdown(f"### 🛠 Mã lỗi: `{result['error_code']}`")
            st.markdown(f"### 🕒 Thời gian: `{result.get('timestamp', 'Chưa có thông tin')}`")
            st.markdown(f"### 📜 Mô tả:** {result['description']}")
            st.markdown(f"### 🔍 Nguyên nhân:** {result.get('root_cause', 'Chưa có thông tin')}") 
            st.markdown(f"### 🛠 Giải pháp:** {result.get('solution', 'Chưa có thông tin')}")
            st.markdown(f"### 📈 Cải tiến dài hạn:** {result.get('improvement', 'Chưa có thông tin')}")

            # --- Hiển thị danh sách hình ---
            images = result.get("images", [])
            if images:
                st.write(f"📸 Có {len(images)} hình minh hoạ:")
                cols = st.columns(min(3, len(images)))
                for i, img_url in enumerate(images):
                    cols[i % 3].image(img_url, caption=f"Ảnh {i+1}", width=300)
            else:
                st.info("Không có hình ảnh minh hoạ cho lỗi này.")

            # --- File PDF ---
            pdf_url = result.get("pdf_report")
            if pdf_url:
                st.markdown(f"[📄 Tải báo cáo PDF tại đây]({pdf_url})")
            else:
                st.info("Không có file báo cáo PDF cho lỗi này.")
        else:
            st.error("❌ Không tìm thấy mã lỗi trong database.")

# Procedures Tab
with tab3:
    st.subheader("Quy Trình Xử Lý Lỗi Sản Phẩm RYOBI")
    st.divider()
    st.markdown("Quy Trình Xử Lý Hàng Lỗi Trên Line Sản Xuất ")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/blob/e715218bb20e69eb00814f9bc04f2876446730eb/Quy%20Tr%C3%ACnh.jpg",width=400,output_format="jpg")
    st.markdown("""
    1. **Nhận diện lỗi:** Kỹ thuật viên xác định lỗi dựa trên mô tả và hình ảnh từ khách hàng.
    2. **Tra cứu mã lỗi:** Sử dụng tab '🔍 Tra cứu lỗi' để tìm mã lỗi và thông tin liên quan.
    3. **Phân tích nguyên nhân:** Xem phần 'Nguyên nhân' để hiểu lý do gây ra lỗi.
    4. **Đề xuất giải pháp:** Dựa trên nguyên nhân đã phân tích, kỹ thuật viên đề xuất giải pháp khắc phục.
    5. **Ghi nhận và theo dõi:** Tất cả các bước xử lý lỗi đều được ghi nhận để phục vụ cho việc cải tiến sản phẩm trong tương lai.

    """)
    





