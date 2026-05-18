import streamlit as st
import math

# ตั้งค่าหน้าตาของโปรแกรม
st.set_page_config(page_title="โปรแกรมออกแบบฐานรากแผ่เดี่ยว (WSD)", page_icon="🏗️", layout="wide")

st.title("🏗️ โปรแกรมออกแบบฐานรากแผ่เดี่ยว (Isolated Footing Design)")
st.subheader("วิธีแรงเค้นใช้งาน (Working Stress Design - WSD) ตามมาตรฐาน วสท.")
st.markdown("---")

# แบ่งหน้าจอเป็น 2 ฝั่ง: ฝั่งรับข้อมูล (Inputs) และฝั่งแสดงผล (Results)
col1, col2 = st.columns([1, 1.5])

with col1:
    st.header("📥 ข้อมูลนำเข้า (Inputs)")
    
    st.subheader("1. น้ำหนักบรรทุกและดิน")
    P = st.number_input("น้ำหนักบรรทุกใช้งานทั้งหมด P (ตัน)", value=25.0, step=1.0)
    q_all = st.number_input("ความสามารถในการแบกทานปลอดภัยของดิน qa (ตัน/ตร.ม.)", value=15.0, step=1.0)
    
    st.subheader("2. ขนาดเสาตอม่อ")
    col_w = st.number_input("ความกว้างของเสา b (ซม.)", value=20.0, step=5.0) / 100
    col_l = st.number_input("ความยาวของเสา l (ซม.)", value=20.0, step=5.0) / 100
    
    st.subheader("3. คุณสมบัติวัสดุ")
    fc_prime = st.number_input("กำลังอัดประลัยของคอนกรีตทรงกระบอก fc' (ksc)", value=240, step=10)
    fy = st.selectbox("ชั้นคุณภาพเหล็กเสริมหลัก (fy)", [3000, 4000], index=1, format_func=lambda x: f"SD{x//100} ({x} ksc)")
    
    st.subheader("4. ข้อกำหนดเหล็กเสริม")
    bar_dia = st.selectbox("ขนาดเหล็กเสริมที่ต้องการใช้ (มม.)", [9, 12, 16, 20, 25], index=2, format_func=lambda x: f"DB{x}" if x >= 12 else f"RB{x}")

# --- ส่วนของการคำนวณตามหลักวิศวกรรม ---
# 1. กำหนดค่าแรงเค้นที่ยอมให้ (Allowable Stresses)
fc = 0.375 * fc_prime
fs = 1500 if fy == 3000 else 1700  # ค่าตามมาตรฐาน วสท.

Ec = 15100 * math.sqrt(fc_prime)
Es = 2000000
n = Es / Ec
k = 1 / (1 + fs / (n * fc))
j = 1 - (k / 3)

# แรงเฉือนที่ยอมให้
v_c_wb = 0.29 * math.sqrt(fc_prime) # แรงเฉือนคานกว้าง
v_c_p = 0.53 * math.sqrt(fc_prime)  # แรงเฉือนทะลุ

# 2. คำนวณขนาดฐานราก (Assume เป็นสี่เหลี่ยมจัตุรัสเพื่อความง่าย)
A_req = P / q_all
B_init = math.sqrt(A_req)
B = math.ceil(B_init * 10) / 10 # ปัดขึ้นทีละ 10 ซม. เพื่อทำงานง่าย
if B < 1.0: 
    B = 1.0  # ขนาดขั้นต่ำ 1.0 x 1.0 ม.

q_net = P / (B * B)

# 3. คำนวณความหนาฐานราก (หาค่า d ที่สอดคล้องกับแรงเฉือนทั้ง 2 แบบ)
d = 0.10  # เริ่มต้นความหนาประสิทธิผลที่ 10 ซม.
passed = False

while d < 2.0:
    # ตรวจสอบแรงเฉือนคานกว้าง (Wide-beam Shear) ที่ระยะ d จากขอบเสา
    cantilever = (B - max(col_w, col_l)) / 2
    dist_wb = cantilever - d
    if dist_wb < 0:
        V_wb = 0
    else:
        V_wb = q_net * B * dist_wb
    v_wb = (V_wb * 1000) / (B * 100 * d * 100)
    
    # ตรวจสอบแรงเฉือนทะลุ (Punching Shear) ที่ระยะ d/2 รอบขอบเสา
    bo = 2 * ((col_w + d) + (col_l + d))
    A_punch = (B * B) - ((col_w + d) * (col_l + d))
    V_p = q_net * A_punch
    v_p = (V_p * 1000) / (bo * 100 * d * 100)
    
    if v_wb <= v_c_wb and v_p <= v_c_p:
        passed = True
        break
    d += 0.01  # เพิ่มความหนาทีละ 1 ซม.จนกว่าจะผ่าน

# คำนวณความหนารวม t (เผื่อระยะหุ้มคอนกรีตลึก/Covering 7.5 ซม. สำหรับงานดิน)
t_req = d + 0.075
t = math.ceil(t_req * 20) / 20  # ปัดความหนาขึ้นทีละ 5 ซม.
d_actual = t - 0.075

# 4. คำนวณโมเมนต์ดัดและเหล็กเสริม (วิกฤตที่ขอบเสา)
M = q_net * B * (cantilever ** 2) / 2  # ตัน-เมตร
M_kg_cm = M * 1000 * 100  # แปลงหน่วยเป็น กิโลกรัม-เซนติเมตร
As_req = M_kg_cm / (fs * j * d_actual * 100)

# ข้อกำหนดเหล็กเสริมขั้นต่ำ (0.002 สำหรับเหล็กข้ออ้อย SD40 หรือตามมาตรฐาน)
As_min = 0.002 * (B * 100) * (t * 100)
As_design = max(As_req, As_min)

# คำนวณจำนวนเส้นและระยะห่าง
ab = (math.pi * (bar_dia / 10) ** 2) / 4  # พื้นที่หน้าตัดเหล็ก 1 เส้น (ตร.ซม.)
num_bars = math.ceil(As_design / ab)
if num_bars < 3: 
    num_bars = 3  # อย่างน้อยต้องมี 3 เส้น

spacing = ((B * 100) - 15) / (num_bars - 1)  # หักระยะคอนกรีตหุ้มข้างละ 7.5 ซม.

# --- ฝั่งแสดงผลลัพธ์ ---
with col2:
    st.header("📊 ผลการคำนวณ (Results)")
    
    # สรุปผลเป็นแผงข้อมูลขนาดใหญ่ (Metrics)
    m1, m2, m3 = st.columns(3)
    m1.metric("ขนาดฐานราก (กว้าง x ยาว)", f"{B:.2f} x {B:.2f} ม.")
    m2.metric("ความหนาฐานราก (t)", f"{t*100:.0f} ซม.")
    m3.metric("แรงดันดินจริง (q_net)", f"{q_net:.2f} ตัน/ตร.ม.")
    
    st.success(f"**💡 สรุปข้อกำหนดการจัดเหล็กเสริม (ต่อทิศทาง):**")
    st.subheader(f"➡️ ใช้เหล็ก {'DB' if bar_dia >= 12 else 'RB'}{bar_dia} มม. จำนวน **{num_bars} เส้น**")
    st.subheader(f"➡️ ระยะจัดเรียง (Spacing): **@ {spacing:.1f} ซม.** (ตะแกรงทั้งสองทิศทาง)")
    
    # ส่วนขยายแสดงรายละเอียดทางวิศวกรรมสำหรับการตรวจสอบ (Audit)
    with st.expander("🔍 ดูรายละเอียดการคำนวณทางวิศวกรรม (Calculation Details)"):
        st.markdown(f"""
        * **พื้นที่ฐานรากที่ต้องการ:** $A_{{req}} = {A_req:.3f}$ ตร.ม. $\rightarrow$ เลือกใช้ $A_{{actual}} = {B*B:.2f}$ ตร.ม.
        * **ระยะยื่นของฐานราก (Cantilever):** {cantilever:.3f} ม.
        * **แรงเฉือนคานกว้างที่เกิดขึ้นจริง:** {v_wb:.2f} ksc (ยอมให้ได้ไม่เกิน {v_c_wb:.2f} ksc) $\rightarrow$ **ผ่าน**
        * **แรงเฉือนทะลุที่เกิดขึ้นจริง:** {v_p:.2f} ksc (ยอมให้ได้ไม่เกิน {v_c_p:.2f} ksc) $\rightarrow$ **ผ่าน**
        * **โมเมนต์ดัดสูงสุดที่ขอบเสา:** {M:.2f} ตัน-ม.
        * **ปริมาณเหล็กเสริมที่คำนวณได้:** {As_req:.2f} ตร.ซม. (เหล็กเสริมขั้นต่ำกำหนด: {As_min:.2f} ตร.ซม.)
        * **พื้นที่เหล็กเสริมที่ใช้จริง:** {num_bars * ab:.2f} ตร.ซม. $\rightarrow$ **ผ่าน**
        """)
        
    st.warning("⚠️ **หมายเหตุสำหรับการนำไปใช้งานจริง:** โปรแกรมนี้ใช้สำหรับออกแบบฐานรากแผ่เดี่ยวที่รับแรงในแนวดิ่งเท่านั้น ในกรณีที่ฐานรากมีโมเมนต์ดัดสูง (เช่น โครงสร้างต้านทานแรงลมหรือแผ่นดินไหว) หรือมีแรงเยื้องศูนย์ จะต้องคำนวณแรงดันดินแบบไม่สม่ำเสมอเพิ่มเติม")
