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
        p_type = st.selectbox("نوع

