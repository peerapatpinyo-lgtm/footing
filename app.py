import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- ตั้งค่าหน้าตาของโปรแกรม ---
st.set_page_config(page_title="Pro Footing Design (WSD)", page_icon="🏗️", layout="wide")

st.title("🏗️ โปรแกรมออกแบบฐานรากแผ่เดี่ยวขั้นสูง (WSD)")
st.markdown("ออกแบบตามมาตรฐาน วสท. | **คำนวณขนาด, ตรวจสอบแรงเฉือน, จัดเหล็ก และวาดแบบอัตโนมัติ**")

# --- แถบด้านข้างสำหรับรับข้อมูล (Sidebar Inputs) ---
with st.sidebar:
    st.header("📥 ป้อนข้อมูล (Inputs)")
    
    st.markdown("**1. น้ำหนักบรรทุกและดิน**")
    P = st.number_input("น้ำหนักบรรทุกใช้งาน P (ตัน)", value=30.0, step=1.0)
    q_all = st.number_input("ความสามารถในการแบกทานของดิน qa (ตัน/ตร.ม.)", value=15.0, step=1.0)
    Df = st.number_input("ความลึกของระดับฐานราก Df (เมตร)", value=1.5, step=0.1)
    
    st.markdown("**2. ขนาดเสาตอม่อ**")
    col_w = st.number_input("กว้าง cx (ซม.)", value=20.0, step=5.0) / 100
    col_l = st.number_input("ยาว cy (ซม.)", value=20.0, step=5.0) / 100
    
    st.markdown("**3. คุณสมบัติวัสดุ**")
    fc_prime = st.number_input("กำลังอัดคอนกรีตทรงกระบอก fc' (ksc)", value=240, step=10)
    fy_choice = st.selectbox("ชั้นคุณภาพเหล็กเสริมหลัก (fy)", [3000, 4000], index=1)
    
    st.markdown("**4. เลือกขนาดเหล็ก**")
    bar_dia = st.selectbox("ขนาดเหล็กเสริม (มม.)", [12, 16, 20, 25], index=1)

# --- ส่วนของการคำนวณ (Calculation Engine) ---
# 1. วัสดุและค่าที่ยอมให้
fc = 0.375 * fc_prime
fs = 1500 if fy_choice == 3000 else 1700
Ec = 15100 * math.sqrt(fc_prime)
Es = 2040000
n = Es / Ec
k = 1 / (1 + fs / (n * fc))
j = 1 - (k / 3)

v_c_wb = 0.29 * math.sqrt(fc_prime) # Allowable Wide-beam Shear
v_c_p = 0.53 * math.sqrt(fc_prime)  # Allowable Punching Shear

# 2. คำนวณขนาดฐานราก (หักน้ำหนักดินและฐานรากออก)
# สมมติหน่วยน้ำหนักดิน 1.8 t/m3, คอนกรีต 2.4 t/m3 (เฉลี่ยใช้ 2.0 t/m3 สำหรับดิน+คอนกรีต)
q_net_allow = q_all - (2.0 * Df)
A_req = P / q_net_allow
B_init = math.sqrt(A_req)
B = math.ceil(B_init * 20) / 20 # ปัดขึ้นทีละ 5 ซม.
if B < 1.0: B = 1.0

# แรงดันดินสุทธิที่กระทำต่อฐานรากจริงๆ
q_net = P / (B * B)

# 3. คำนวณความหนาและตรวจสอบแรงเฉือน
d = 0.15 # เริ่มต้น d = 15 cm
passed = False

while d < 2.0:
    cantilever = (B - max(col_w, col_l)) / 2
    dist_wb = cantilever - d
    
    # Wide-beam Shear
    V_wb = q_net * B * dist_wb if dist_wb > 0 else 0
    v_wb = (V_wb * 1000) / (B * 100 * d * 100)
    
    # Punching Shear
    bo = 2 * ((col_w + d) + (col_l + d))
    A_punch = (B * B) - ((col_w + d) * (col_l + d))
    V_p = q_net * A_punch
    v_p = (V_p * 1000) / (bo * 100 * d * 100)
    
    if v_wb <= v_c_wb and v_p <= v_c_p:
        passed = True
        break
    d += 0.01

t_req = d + 0.075 # เผื่อ Covering 7.5 cm
t = math.ceil(t_req * 20) / 20 # ปัดขึ้นทีละ 5 ซม.
d_actual = t - 0.075

# 4. ออกแบบเหล็กเสริม
M = q_net * B * (cantilever ** 2) / 2
M_kg_cm = M * 1000 * 100
As_req = M_kg_cm / (fs * j * d_actual * 100)
As_min = 0.002 * (B * 100) * (t * 100)
As_design = max(As_req, As_min)

ab = (math.pi * (bar_dia / 10) ** 2) / 4
num_bars = math.ceil(As_design / ab)
if num_bars < 4: num_bars = 4

spacing = ((B * 100) - 15) / (num_bars - 1)
spacing_round = math.floor(spacing) # ปัดลงเพื่อความปลอดภัย

# --- ส่วนแสดงผล (Main Display) ---
tab1, tab2, tab3 = st.tabs(["📊 สรุปผลการออกแบบ", "📐 แบบแปลนเบื้องต้น", "📝 รายการคำนวณแบบละเอียด"])

with tab1:
    st.subheader("✅ สรุปขนาดและเหล็กเสริม")
    col1, col2, col3 = st.columns(3)
    col1.metric("ขนาดฐานราก (B x L)", f"{B:.2f} x {B:.2f} ม.")
    col2.metric("ความหนา (t)", f"{t*100:.0f} ซม.")
    col3.metric("แรงดันดินที่เกิดขึ้น", f"{q_net:.2f} ตัน/ตร.ม.")
    
    st.info(f"**เหล็กเสริมตะแกรง (Bottom Mesh):** ใช้เหล็ก **DB{bar_dia} จำนวน {num_bars} เส้น @ {spacing_round:.0f} ซม.** ทั้งสองทิศทาง")
    
    # สร้างข้อความสำหรับดาวน์โหลด
    report_text = f"""--- สรุปผลการออกแบบฐานรากแผ่ (WSD) ---
น้ำหนักบรรทุก P: {P} Tons
กำลังรับน้ำหนักดิน qa: {q_all} t/sq.m.
-----------------------------------
ขนาดฐานรากที่ใช้: {B:.2f} x {B:.2f} เมตร
ความหนาฐานราก: {t*100:.0f} ซม.
เหล็กเสริม: DB{bar_dia} - {num_bars} เส้น @ {spacing_round:.0f} ซม. (ตะแกรง)
แรงดันดินใช้งาน: {q_net:.2f} t/sq.m.
"""
    st.download_button(label="📥 ดาวน์โหลดสรุปผล (TXT)", data=report_text, file_name="Footing_Design_Report.txt")

with tab2:
    st.subheader("ภาพแสดงผังฐานรากและเหล็กเสริม")
    # ใช้ matplotlib วาดแปลน
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # วาดฐานราก
    footing = patches.Rectangle((-B/2, -B/2), B, B, linewidth=2, edgecolor='black', facecolor='none')
    ax.add_patch(footing)
    
    # วาดเสา
    column = patches.Rectangle((-col_w/2, -col_l/2), col_w, col_l, linewidth=2, edgecolor='black', facecolor='gray', alpha=0.5)
    ax.add_patch(column)
    
    # วาดเส้นเหล็กเสริม (จำลอง)
    rebar_spacing_m = spacing_round / 100
    start_pos = -B/2 + 0.075 # หัก cover
    for i in range(num_bars):
        pos = start_pos + (i * rebar_spacing_m)
        ax.plot([pos, pos], [-B/2 + 0.075, B/2 - 0.075], color='blue', linestyle='-', linewidth=1, alpha=0.6) # แนวแกน Y
        ax.plot([-B/2 + 0.075, B/2 - 0.075], [pos, pos], color='red', linestyle='-', linewidth=1, alpha=0.6) # แนวแกน X

    ax.set_xlim(-B/2 - 0.2, B/2 + 0.2)
    ax.set_ylim(-B/2 - 0.2, B/2 + 0.2)
    ax.set_aspect('equal', adjustable='box')
    plt.title(f"Footing Plan: {B} x {B} m.\nRebar: DB{bar_dia} @ {spacing_round} cm.")
    plt.xlabel("Meters")
    plt.ylabel("Meters")
    plt.grid(False)
    
    st.pyplot(fig)

with tab3:
    st.subheader("🔍 รายละเอียดการตรวจสอบทางวิศวกรรม")
    st.markdown(f"""
    **1. การหาขนาดหน้าตัด:**
    - พื้นที่ต้องการ: $A_{{req}} = {A_req:.2f}$ m$^2$ (ใช้จริง $A = {B*B:.2f}$ m$^2$)
    - แรงดันดินสุทธิ: $q_{{net}} = {q_net:.2f}$ t/m$^2$ (น้อยกว่าค่า allowable = ผ่าน)
    
    **2. การตรวจสอบแรงเฉือน:**
    - ระยะความหนาใช้งานจริง $d_{{actual}} = {d_actual * 100:.1f}$ ซม.
    - **Wide-Beam Shear:** เกิดขึ้น {v_wb:.2f} ksc $\le$ ยอมให้ {v_c_wb:.2f} ksc $\rightarrow$ **{'✅ ผ่าน' if v_wb <= v_c_wb else '❌ ไม่ผ่าน'}**
    - **Punching Shear:** เกิดขึ้น {v_p:.2f} ksc $\le$ ยอมให้ {v_c_p:.2f} ksc $\rightarrow$ **{'✅ ผ่าน' if v_p <= v_c_p else '❌ ไม่ผ่าน'}**
    
    **3. การคำนวณเหล็กเสริม (Flexure):**
    - โมเมนต์ดัดวิกฤตที่ขอบเสา $M = {M:.2f}$ t-m
    - พื้นที่เหล็กต้องการ $A_{{s(req)}} = {As_req:.2f}$ cm$^2$
    - พื้นที่เหล็กขั้นต่ำ (0.002) $A_{{s(min)}} = {As_min:.2f}$ cm$^2$
    - พื้นที่เหล็กที่จัดจริง = {num_bars * ab:.2f} cm$^2$ $\rightarrow$ **✅ ผ่าน**
    """)
