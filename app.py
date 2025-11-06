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
st.set_page_config(page_title="Process Engineering Technical Handbook", layout="wide")
st.title("Process Engineering Technical Handbook")

tab1, tab2, tab3, tab4 = st.tabs(["➕ Thêm lỗi mới", "🔍 Tra cứu lỗi", "📘 Quy Trình Phân tích", "⚛ ERP System"])

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
            st.write(f"### 📘 Model: `{result['model']}`")
            st.write(f"### 🛠 Mã lỗi: `{result['error_code']}`")
            st.write(f"### 🕒 Thời gian: `{result.get('timestamp', 'Chưa có thông tin')}`")
            st.write(f"### 📜 Mô tả:** {result['description']}")
            st.write(f"### 🔍 Nguyên nhân:** {result.get('root_cause', 'Chưa có thông tin')}") 
            st.write(f"### 🛠 Giải pháp:** {result.get('solution', 'Chưa có thông tin')}")
            st.write(f"### 📈 Cải tiến dài hạn:** {result.get('improvement', 'Chưa có thông tin')}")

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
    st.subheader("**Quy Trình Xử Lý Hàng Lỗi Trên Line Sản Xuất** ")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/5d53967118908656d91d073f0f723b3653267d95/3.jpg")
    st.markdown("""
    1. *Sản xuất:* Vai trò làm đúng thao tác theo WI, nếu phát sinh hàng lỗi về chức năng tại trạm thao tác phải thông báo cho PIE và điền Form"RPDNF0020".
    2. *IPQC:* Vai trò xác nhận bất thường về ngoại quan và cùng với MQA hoặc PIE phán định bất thường đó có là lỗi hay không.
    3. *PIE:* Vai trò chính phân tích lỗi ảnh hưởng tới chức năng sản phẩm và nếu phát hiện lỗi đó liên quan tới bộ phận nào thì báo đến bộ phận đó tìm cách cải thiện & hỗ trợ sản xuất & cùng với MQA tìm giải pháp tạm thời để tránh đứt quãng sản xuất .
    4. *MQA:* Vai trò hỗ trợ cùng với PIE phân tích & xác nhận kết quả & xác nhận bất thường có phải là lỗi hay không & đưa ra mức độ cho phép nếu bất thường đó không ảnh hưởng tới chức năng sản phẩm .
    5. *SQE:* Chịu trách nhiệm phân loại vật tư NG nếu lỗi đến từ vật tư đầu vào sau khi PIE/MQA phân tích & cải thiện vật tư đầu vào .
    """)
    st.markdown("""**Lưu ý: Hàng sau khi phân tích phải đánh dấu tròn "O" lên phích cắm trước khi trả lại cho sản xuất**""")         
    
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/7d1b28335ebbd203552ea93084496b16ff2946a7/2.jpg")

    st.divider()
    st.subheader("Quy trình Cảnh Báo Line Down")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/346bf96fec732bc713c93e9749bfa64d29509de8/1.jpg")
    st.markdown("***Điều Kiện Dừng Line***")
    st.markdown("""
    1. *Vấn đề an toàn*
    2. *Vấn đề chức năng sản phẩm nghiêm trọng*
    3. *Tỉ lệ sản phẩm AC/DC/BP/Charger không đạt 2pcs/giờ*
    4. *Nhân lực sản xuất nhàn rỗi quá 10 phút*
    """)
    st.markdown("***Quy Trình Xử Lý***")
    st.markdown("""
    1. Đối với vấn đề 4M thông thường thì PIE chủ đạo & MQA hỗ trợ cùng với PIE đánh giá đối sách cải thiện và kết quả.
    2. Đối với vấn đề liên quan tới thiết kế và thông số PCP/PM/Check Card: PIE/MQA/Engineering/QE phải cùng tạo 1 nhóm để giải quyết vấn đề.
    """)
    st.markdown("***Vai trò sau khi biết nguyên nhân***")
    st.markdown("""
    1. Vật tư đầu vào/sai liệu trong thùng nguyên: SQE/IQC
    2. Vấn đề thiết bị & Khuôn: Mass Production: PM or EB/QB/1stMP: PM/APE
    3. Vấn đề thiếu liệu: PMC
    4. Phát Sai liệu/phát liệu không kịp/Sai liệu trong thùng lẻ: RWH
    5. Vấn đề thao tác: PROD
    6. Vấn đề vẫn chưa ra nguyên nhân: PIE/MQA tiếp tục phân tích
    7. Vấn đề về phương pháp: IE
    """)
    st.markdown("***Lưu ý nếu sau 30 phút vấn đề được giải quyết và đảm bảo những yếu tố cho line sản xuất hoạt động thì sản xuất phải khôi phục hoạt động và bỏ cảnh báo line down này đi.***")
    st.markdown("***Lưu ý nếu vẫn chưa ra nguyên nhân và nguy cơ cao ảnh hưởng chất lượng thì sản xuất sắp xếp nhân lực qua khu vực khác để giảm tổn thất cho nhà máy và bộ phận PC điều chỉnh kế hoạch nếu có thể.***")





































