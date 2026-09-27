import streamlit as st
import sqlite3
import qrcode
import io
import os
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# تنظیمات اولیه صفحه
st.set_page_config(page_title="تاسیسات بیمارستان ابن سینا", layout="wide")

# ---------------------------------------------------------
# ۱. اتصال به پایگاه داده و ساخت جداول
# ---------------------------------------------------------
conn = sqlite3.connect('hospital_facility.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
username TEXT PRIMARY KEY,
password TEXT,
role TEXT,
signature_path TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS projects (
id INTEGER PRIMARY KEY AUTOINCREMENT,
section TEXT,
project_type TEXT,
technician TEXT,
description TEXT,
assignee_facility TEXT,
assignee_engineering TEXT,
assignee_head_nurse TEXT,
requester TEXT,
status TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS checklists (
id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT,
technician TEXT,
answers TEXT,
pdf_path TEXT
)
''')
conn.commit()

# ایجاد کاربر مدیر پیش‌فرض در صورت عدم وجود
c.execute("SELECT * FROM users WHERE username='admin'")
if not c.fetchone():
c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'admin', '')")
conn.commit()

# ---------------------------------------------------------
# ۲. احراز هویت (Login)
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
st.session_state['logged_in'] = False
st.session_state['username'] = ''
st.session_state['role'] = ''

if not st.session_state['logged_in']:
st.title("🏥 سامانه تاسیسات بیمارستان ابن سینا")
st.subheader("ورود به سیستم")
username = st.text_input("نام کاربری")
password = st.text_input("رمز عبور", type="password")
if st.button("ورود"):
c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
user = c.fetchone()
if user:
st.session_state['logged_in'] = True
st.session_state['username'] = username
st.session_state['role'] = user[0]
st.rerun()
else:
st.error("نام کاربری یا رمز عبور اشتباه است.")
st.stop()

# ---------------------------------------------------------
# ۳. پنل مدیریت (مدیر دفتر فنی و مهندسی)
# ---------------------------------------------------------
st.sidebar.title(f"کاربر: {st.session_state['username']}")
st.sidebar.text(f"نقش: {st.session_state['role']}")
if st.sidebar.button("خروج"):
st.session_state['logged_in'] = False
st.rerun()

if st.session_state['role'] == 'admin':
st.header("⚙️ پنل مدیریت دفتر فنی و مهندسی")
tab1, tab2, tab3 = st.tabs(["مدیریت پرسنل و امضاها", "ارجاع پروژه جدید", "چک‌لیست‌های دریافتی"])

with tab1:
st.subheader("تعریف پرسنل جدید و بارگذاری امضا")
new_user = st.text_input("نام کاربری پرسنل")
new_pass = st.text_input("رمز عبور پرسنل")
sig_file = st.file_uploader("تصویر اسکن امضا (PNG/JPG)", type=['png', 'jpg', 'jpeg'])

if st.button("ثبت کاربر"):
if new_user and new_pass and sig_file:
if not os.path.exists("signatures"):
os.makedirs("signatures")
sig_path = f"signatures/{new_user}.png"
with open(sig_path, "wb") as f:
f.write(sig_file.getbuffer())

try:
c.execute("INSERT INTO users VALUES (?, ?, 'tech', ?)", (new_user, new_pass, sig_path))
conn.commit()
st.success(f"کاربر {new_user} با موفقیت تعریف شد.")
except:
st.error("این نام کاربری قبلاً تعریف شده است.")

with tab2:
st.subheader("ارجاع پروژه/کار جدید به پرسنل")
sec = st.text_input("نام بخش")
p_type = st.selectbox("نوع پروژه", ["برقی", "مکانیکی", "بنایی", "سایر"], key="admin_ptype")
techs = [row[0] for row in c.execute("SELECT username FROM users WHERE role='tech'").fetchall()]
selected_tech = st.selectbox("ارسال به کارشناس", techs if techs else ["هیچ کارشناسی تعریف نشده"])
req = st.text_input("درخواست دهنده")

if st.button("ثبت و ارجاع پروژه"):
c.execute("""INSERT INTO projects (section, project_type, technician, requester, status)
VALUES (?, ?, ?, ?, 'در حال انجام')""", (sec, p_type, selected_tech, req))
conn.commit()
st.success("پروژه با موفقیت ارجاع داده شد.")

with tab3:
st.subheader("📄 چک‌لیست‌ها و گزارش‌های نهایی (غیرقابل تغییر)")
checklists = c.execute("SELECT id, title, technician, pdf_path FROM checklists").fetchall()
for chk in checklists:
st.write(f"**عنوان:** {chk[1]} | **کارشناس:** {chk[2]}")
if os.path.exists(chk[3]):
with open(chk[3], "rb") as pdf_file:
st.download_button(f"دانلود PDF (کد {chk[0]})", pdf_file, file_name=f"Checklist_{chk[0]}.pdf", key=f"dl_{chk[0]}")

# ---------------------------------------------------------
# ۴. پنل کارشناس تاسیسات
# ---------------------------------------------------------
else:
st.header("🔧 پنل کارشناس تاسیسات")
tab1, tab2 = st.tabs(["پروژه‌ها و ثبت گزارش", "تکمیل چک‌لیست و PM"])

with tab1:
st.subheader("ثبت / بروزرسانی پروژه")
sec = st.text_input("نام بخش")
p_type = st.selectbox("نوع پروژه", ["برقی", "مکانیکی", "بنایی", "سایر"], key="tech_ptype")
desc = st.text_area("توضیحات فنی")

col1, col2, col3 = st.columns(3)
rec_fac = col1.text_input("تحویل گیرنده (مسئول تاسیسات)")
rec_eng = col2.text_input("تحویل گیرنده (مدیر دفتر فنی)")
rec_nurse = col3.text_input("تحویل گیرنده (سرپرستار)")
req = st.text_input("درخواست دهنده")

img_files = st.file_uploader("تصاویر پیشرفت کار", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if st.button("ثبت پروژه و تولید QR Code"):
c.execute("""INSERT INTO projects
(section, project_type, technician, description, assignee_facility, assignee_engineering, assignee_head_nurse, requester, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'تکمیل شده')""",
(sec, p_type, st.session_state['username'], desc, rec_fac, rec_eng, rec_nurse, req))
conn.commit()
p_id = c.lastrowid

project_url = f"https://tasisat.streamlit.app/?project_id={p_id}"

qr = qrcode.make(project_url)
qr_img_bytes = io.BytesIO()
qr.save(qr_img_bytes)

st.success(f"پروژه با موفقیت ثبت شد (کد پروژه: {p_id})")
st.image(qr_img_bytes, caption="QR کد اختصاصی پروژه (جهت نصب در محل یا مشاهده گزارش)")

with tab2:
st.subheader("تکمیل چک‌لیست روزانه / PM")
chk_type = st.selectbox("انتخاب چک‌لیست", ["چک‌لیست روزانه ژنراتور", "چک‌لیست PM موتورخانه", "چک‌لیست سیستم اعلام حریق"])

q1 = st.radio("وضعیت ولتاژ و جریان نرمال است؟", ["بله", "خیر"])
q2 = st.radio("نشتی روغن/آب مشاهده شد؟", ["خیر", "بله"])
notes = st.text_area("توضیحات تکمیلی چک‌لیست")

if st.button("ثبت نهایی و ارسال به مدیر"):
c.execute("SELECT signature_path FROM users WHERE username=?", (st.session_state['username'],))
sig_res = c.fetchone()
sig_path = sig_res[0] if sig_res else ""

if not os.path.exists("reports"):
os.makedirs("reports")

pdf_path = f"reports/chk_{st.session_state['username']}_{chk_type}.pdf"
pdf = canvas.Canvas(pdf_path, pagesize=letter)

pdf.setFont("Helvetica-Bold", 16)
pdf.drawString(100, 750, f"Hospital Facility Checklist: {chk_type}")
pdf.setFont("Helvetica", 12)
pdf.drawString(100, 720, f"Technician: {st.session_state['username']}")
pdf.drawString(100, 690, f"Q1 (Voltage Normal): {q1}")
pdf.drawString(100, 660, f"Q2 (Leakage Observed): {q2}")
pdf.drawString(100, 630, f"Notes: {notes}")

if sig_path and os.path.exists(sig_path):
pdf.drawString(100, 530, "Automated Signature:")
pdf.drawImage(sig_path, 100, 420, width=150, height=100)

pdf.save()

c.execute("INSERT INTO checklists (title, technician, answers, pdf_path) VALUES (?, ?, ?, ?)",
(chk_type, st.session_state['username'], f"{q1}, {q2}, {notes}", pdf_path))
conn.commit()

st.success("چک‌لیست با موفقیت ثبت شد و امضای دیجیتال شما به فایل PDF اضافه گردید. اطلاعات قفل شد.")
