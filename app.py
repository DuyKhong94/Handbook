import streamlit as st
from pymongo import MongoClient
import tempfile
from upload_image import upload_image_to_cloudinary
from datetime import datetime
import pandas as pd
import random, string
import os
import numpy as np
import matplotlib.pyplot as plt
import requests

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["➕ Thêm lỗi mới", "🔍 Tra cứu lỗi", "📘 Quy Trình Phân tích", 
                                        "⚛ ERP System","☯ Team Center & FAI","Production Schedule","Sách Tham Khảo"])

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
    prefix=search_model[:6]
    if search_model:
        cursor = collection.find({"model": {"$regex":f"^{prefix[:6]}"}})
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
            st.write(f" 📘 Model: {result['model']}")
            st.write(f" 🛠 Mã lỗi: {result['error_code']}")
            st.write(f" 🕒 Thời gian: {result.get('timestamp', 'Chưa có thông tin')}")
            st.write(f" 📜 Mô tả:** {result['description']}")
            st.write(f" 🔍 Nguyên nhân:** {result.get('root_cause', 'Chưa có thông tin')}") 
            st.write(f" 🛠 Giải pháp:** {result.get('solution', 'Chưa có thông tin')}")
            st.write(f" 📈 Cải tiến dài hạn:** {result.get('improvement', 'Chưa có thông tin')}")

            # --- Hiển thị danh sách hình ---
            images = result.get("images", [])
            if images:
                st.write(f"📸 Có {len(images)} hình minh hoạ:")
                cols = st.columns(min(3, len(images)))
                for i, img_url in enumerate(images):
                    cols[i % 3].image(img_url, caption=f"Ảnh {i+1}")
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
    st.markdown("**Quy Trình Xử Lý Hàng Lỗi Trên Line Sản Xuất** ")
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
    st.markdown("Quy trình Cảnh Báo Line Down")
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

    st.divider()
    st.subheader("Sơ đồ liên hệ - Hotline:")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/276302b6f5a16ba5f5db7089cabe410b7cf19206/MQAchart.jpg")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/710c394ac305c7c018753d3bd5ec1dc58c541d7e/094237.jpg")
with tab4:
    st.subheader("Xử lý trên hệ thống ERP")
    st.markdown("***Công dụng của ERP***")
    st.markdown("""
    1. *ERP dùng để tra cứu BOM theo mã model được ghi trên bảng sản lượng đầu line, ví dụ: 030383007, 030247012...*
    2. *ERP dùng để tra cứu ECO xem BOM job hoặc mã liệu đó có ECO hay không, thông thường để tra cứu phiên bản của mã vật tư đó có được sử dụng hay không.*
    3. *ERP cũng được dùng để tra cứu lý do và lịch sử thay đổi của mã vật tư.*
    4. *ERP dùng để tra cứu On Hand/ vật tư đó sử dụng cho model gì? và tra cứu model đó chạy từ bao lâu.*
    """)
    st.write(" Link: http://hkerpapp.hk.globaltti.net:8068/OA_HTML/AppsLocalLogin.jsp")
    st.divider()
    st.markdown("**Tra cứu BOM & Mã WI của Console và Packing**")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/64b2d8e6548a748ac417d222ef945b5e821bb936/ERP.jpg")
    st.divider()
    st.markdown("**Tra cứu ECO**")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/283f48edd8d4c515187a5eab35f2a5215f29e03d/ECO.jpg")
    st.divider()
    st.markdown("**Tra cứu lượng vật tư tồn kho**")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/108246c370090edbf580a1021b98d1e6d912c6cd/091950.jpg")
with tab5:
    st.subheader("Tra cứu Bản vẽ trên Team Center")
    st.write(" Link: https://cnstclb01.cn.globaltti.net/awc/#/showHome")
    st.markdown("""
    1. **Phải tra cứu BOM theo model đang chạy hoặc tìm đến tem nhãn của thùng vật tư để lấy mã vật tư và phiên bản
    2. **Đảm bảo tra cứu đúng mã, đúng phiên bản của vật tư để phân tích chính xác nhất.
    """)
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/e20c0fccc62799dad6c71c31240d7e284b60d26f/174513.jpg")
    st.divider()
    st.subheader("Tra cứu FAI Report")
    st.write(" Link: http://cnsserprod01:8080/")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/54a6630ad2224f86f85dc8beb2f33fb1670d9b17/131859.jpg")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/b6fb7809341b8a50b781037f300749dc273a1bf4/133456.jpg")
with tab6:
    st.write("hello")
    uploaded_file=st.file_uploader("chọn file DPS mới nhất",type=["xlsx","xlsb"])
    if uploaded_file is not None:
        df=pd.read_excel(uploaded_file,sheet_name="Combine",skiprows=3)
        df.columns=df.columns.str.strip()
        column_to_keep=['TTI Model No','Job No','Curent line','QTY']
        df=df[column_to_keep]
        st.dataframe(df)
with tab7:
   st.markdown("[1. Six Sigma Black Belt Handbook Third Edition](https://raw.githubusercontent.com/DuyKhong94/Handbook/90925edaa2a9c904df7d211e738daf0826aacee0/0.%20MUST%20READ_Hand%20Book%20Black.pdf)")

  









































































































