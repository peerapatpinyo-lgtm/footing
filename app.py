import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Enterprise Footing Suite V5.5", page_icon="🏗️", layout="wide")

st.title("🏗️ Enterprise Footing Suite (V5.5 - Hybrid Control Edition)")
st.markdown("ระบบวิเคราะห์ฐานราก | เพิ่มปุ่มควบคุมความหนาฐานรากเอง (Manual Override) + ระบบคำนวณรูเจาะเข็ม Spun Pile")
st.markdown("---")

# --- 2. SIDEBAR PARAMETERS ---
with st.sidebar:
    st.header("⚙️ มาตรฐานและข้อกำหนดการออกแบบ")
    
    st.subheader("1. รูปแบบกลุ่มเสาเข็ม & รูปทรงเรขาคณิต")
    n_piles = st.selectbox("จำนวนเสาเข็มในฐานราก:", [2, 3, 4, 5, 6, 8, 9], index=4)
    pile_shape = st.selectbox("รูปทรงหน้าตัดเสาเข็ม:", ["สี่เหลี่ยมตัน (Square Pile)", "กลมกลวง/สปัน (Spun Pile)", "กลมตัน/เข็มเจาะ (Solid Round Pile)"])
    pile_size = st.number_input("ขนาดเส้นผ่านศูนย์กลางภายนอก หรือความกว้างเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    # ดักจับพารามิเตอร์ความหนาผนังเสาเข็มเฉพาะ Spun Pile
    wall_thickness = 0.0
    if pile_shape == "กลมกลวง/สปัน (Spun Pile)":
        wall_thickness_cm = st.slider("ความหนาของผนังเสาเข็ม Spun Pile (ซม.)", min_value=5, max_value=12, value=6, step=1)
        wall_thickness = wall_thickness_cm / 100
        
    pile_cap = st.number_input("กำลังรับน้ำหนักปลอดภัยของเข็ม - แรงอัด (ตัน/ต้น)", value=30.0, step=1.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนปลอดภัยของเข็ม - แรงดึง (ตัน/ต้น)", value=10.0, step=1.0)
    
    st.subheader("2. แรงกระทำจากเสาตอม่อ (Service Loads)")
    DL = st.number_input("น้ำหนักคงที่ (DL, ตัน)", value=60.0, step=5.0)
    LL = st.number_input("น้ำหนักจร (LL, ตัน)", value=35.0, step=5.0)
    Mcx = st.number_input("โมเมนต์ดัดแกน X (M_cx, ตัน-เมตร)", value=12.0, step=0.5)
    Mcy = st.number_input("โมเมนต์ดัดแกน Y (M_cy, ตัน-เมตร)", value=9.0, step=0.5)
    
    st.subheader("3. มิติตอม่อและวัสดุ")
    cx = st.number_input("ความกว้างเสา cx (เมตร)", value=0.35, step=0.05)
    cy = st.number_input("ความยาวเสา cy (เมตร)", value=0.35, step=0.05)
    col_position = st.selectbox("ตำแหน่งตอม่อบนฐานราก:", ["เสาภายใน (Interior)", "เสาขอบ (Edge)", "เสามุม (Corner)"])
    fc_prime = st.number_input("กำลังอัดประลัยคอนกรีต fc' (ksc)", value=280, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("ขนาดเหล็กแกนหลัก (มม.)", [16, 20, 25], index=1)

    # 🛑 4. ฟีเจอร์ใหม่: ปุ่มสลับโหมดควบคุมความหนาฐานรากตามคำขอ
    st.sidebar.markdown("---")
    st.subheader("🎛️ 4. ควบคุมความหนาฐานราก (t)")
    thickness_mode = st.radio("โหมดการทำงาน:", ["คำนวณอัตโนมัติ (Auto-Optimize)", "ป้อนความหนาเอง (Manual Override)"])
    
    manual_t = 0.60
    if thickness_mode == "ป้อนความหนาเอง (Manual Override)":
        manual_t_cm = st.number_input("ระบุความหนาฐานรากที่ต้องการ t (ซม.)", min_value=30, max_value=300, value=60, step=5)
        manual_t = manual_t_cm / 100

# --- 3. STRENGTH DESIGN METHOD (SDM) CONFIG ---
P_service = DL + LL
P_ultimate = (1.2 * DL) + (1.6 * LL)
load_factor_avg = P_ultimate / P_service if P_service > 0 else 1.4
Mu_cx_direct = Mcx * load_factor_avg
Mu_cy_direct = Mcy * load_factor_avg

phi_v = 0.75  
phi_b = 0.90  
ab = (math.pi * (bar_dia / 10) ** 2) / 4

# --- 4. PILE LAYOUT GENERATOR ---
S_dist = 3.0 * pile_size
E_dist = max(pile_size, 0.35)

if n_piles == 2:
    piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
elif n_piles == 3:
    R_tri = S_dist / math.sqrt(3)
    piles_ideal = [(0, R_tri), (-S_dist/2, -R_tri/2), (S_dist/2, -R_tri/2)]
elif n_piles == 4:
    piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
elif n_piles == 5:
    piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2), (0, 0)]
elif n_piles == 6:
    piles_ideal = [(-S_dist/2, -S_dist), (S_dist/2, -S_dist), (-S_dist/2, 0), (S_dist/2, 0), (-S_dist/2, S_dist), (S_dist/2, S_dist)]
elif n_piles == 8:
    piles_ideal = [(-1.5*S_dist, -S_dist/2), (-0.5*S_dist, -S_dist/2), (0.5*S_dist, -S_dist/2), (1.5*S_dist, -S_dist/2),
                   (-1.5*S_dist, S_dist/2), (-0.5*S_dist, S_dist/2), (0.5*S_dist, S_dist/2), (1.5*S_dist, S_dist/2)]
elif n_piles == 9:
    piles_ideal = [(x, y) for x in [-S_dist, 0, S_dist] for y in [-S_dist, 0, S_dist]]

piles_actual = piles_ideal # เซ็ตค่าดีฟอลต์พิกัดจริง
cg_new_x, cg_new_y = 0.0, 0.0
e_x, e_y = 0.0, 0.0
sum_x2_new, sum_y2_new = sum(p[0]**2 for p in piles_actual), sum(p[1]**2 for p in piles_actual)
piles_relative = piles_actual

# --- 5. SOLVER ENGINE (AUTO LOOP OR MANUAL CHECK) ---
d = 0.40 if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)" else (manual_t - 0.15)
t = 0.55 if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)" else manual_t

has_tension = False
loop_break_by_guard = False
over_reinforced_error = False
shear_fail_manual = False

B_ft = (max(p[0] for p in piles_actual) - min(p[0] for p in piles_actual)) + 2*E_dist
L_ft = (max(p[1] for p in piles_actual) - min(p[1] for p in piles_actual)) + 2*E_dist

v_u_stress, v_c_allowable = 0.0, 0.0
v_u_wb_stress, v_c_wb_allowable = 0.0, 0.0
pile_service_loads = [0.0] * n_piles
pile_ultimate_loads = [0.0] * n_piles
r_outer = pile_size / 2

# ฟังก์ชันเดี่ยวสำหรับรันการตรวจสอบสถิตศาสตร์ในแต่ละรอบความหนา
def run_structural_check(current_d, current_t):
    global v_u_stress, v_c_allowable, v_u_wb_stress, v_c_wb_allowable, pile_service_loads, pile_ultimate_loads, has_tension
    W_f_actual = B_ft * L_ft * current_t * 2.4
    P_tot_s = P_service + W_f_actual
    P_tot_u = P_ultimate + (1.2 * W_f_actual)
    
    Mu_x_loop = Mu_cx_direct + (P_tot_u * (-e_y))
    Mu_y_loop = Mu_cy_direct + (P_tot_u * (-e_x))
    Mx_loop = Mcx + (P_tot_s * (-e_y))
    My_loop = Mcy + (P_tot_s * (-e_x))

    pile_service_loads = []
    pile_ultimate_loads = []
    for prx, pry in piles_relative:
        R_i = (P_tot_s / n_piles) + (My_loop * prx / sum_x2_new if sum_x2_new > 0 else 0) + (Mx_loop * pry / sum_y2_new if sum_y2_new > 0 else 0)
        U_i = (P_tot_u / n_piles) + (Mu_y_loop * prx / sum_x2_new if sum_x2_new > 0 else 0) + (Mu_x_loop * pry / sum_y2_new if sum_y2_new > 0 else 0)
        pile_service_loads.append(R_i)
        pile_ultimate_loads.append(U_i)
        
    max_R = max(pile_service_loads)
    min_R = min(pile_service_loads)
    has_tension = min_R < 0
    
    # Punching Shear Stress
    b1 = cx + current_d
    b2 = cy + current_d
    bo = 2 * (b1 + b2)
    A_c = bo * current_d * 10000  
    gamma_vx = 1 - (1 / (1 + (2/3) * math.sqrt(b1 / b2)))
    gamma_vy = 1 - (1 / (1 + (2/3) * math.sqrt(b2 / b1)))
    J_cx = (current_d * (b1**3) / 6) + ((b1 * (current_d**3)) / 6) + (current_d * b2 * (b1**2) / 2)
    J_cy = (current_d * (b2**3) / 6) + ((b2 * (current_d**3)) / 6) + (current_d * b1 * (b2**2) / 2)
    
    V_u_p_kg = sum(max(0, pile_ultimate_loads[i] * 1000) for i, (px, py) in enumerate(piles_actual) if abs(px) > (cx/2 + current_d/2) or abs(py) > (cy/2 + current_d/2))
    v_u_stress = (V_u_p_kg / A_c) + (gamma_vx * abs(Mu_x_loop) * 100000 * (b2/2) / (J_cx * 1000000)) + (gamma_vy * abs(Mu_y_loop) * 100000 * (b1/2) / (J_cy * 1000000))
    
    beta_col = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
    vc1 = 0.27 * (2 + 4/beta_col) * math.sqrt(fc_prime)
    vc2 = 0.27 * (alpha_s * (current_d * 100) / (bo * 100) + 2) * math.sqrt(fc_prime)
    vc3 = 1.06 * math.sqrt(fc_prime)
    v_c_allowable = phi_v * min(vc1, vc2, vc3)
    
    # Fractional Wide Beam Shear Check (4-Faces)
    X_crit_pos = cx/2 + current_d
    X_crit_neg = -cx/2 - current_d
    Y_crit_pos = cy/2 + current_d
    Y_crit_neg = -cy/2 - current_d
    V_wb_X_pos, V_wb_X_neg, V_wb_Y_pos, V_wb_Y_neg = 0.0, 0.0, 0.0, 0.0
    
    for i, (px, py) in enumerate(piles_actual):
        pu_load = max(0.0, pile_ultimate_loads[i] * 1000)
        # X-Pos Face
        if px - r_outer >= X_crit_pos: V_wb_X_pos += pu_load
        elif px + r_outer > X_crit_pos: V_wb_X_pos += pu_load * ((px + r_outer - X_crit_pos) / pile_size)
        # Y-Pos Face
        if py - r_outer >= Y_crit_pos: V_wb_Y_pos += pu_load
        elif py + r_outer > Y_crit_pos: V_wb_Y_pos += pu_load * ((py + r_outer - Y_crit_pos) / pile_size)

    v_wb_X_pos = V_wb_X_pos / (L_ft * 100 * current_d * 100)
    v_wb_Y_pos = V_wb_Y_pos / (B_ft * 100 * current_d * 100)
    v_u_wb_stress = max(v_wb_X_pos, v_wb_Y_pos)
    v_c_wb_allowable = phi_v * 0.53 * math.sqrt(fc_prime)
    
    return (v_u_stress <= v_c_allowable) and (v_u_wb_stress <= v_c_wb_allowable)

# เริ่มต้นการแยกโหมดทำงานควบคุม Logic
if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)":
    previous_max_R = float('inf')
    while d < 3.0:
        t = math.ceil((d + 0.15) * 20) / 20
        is_safe = run_structural_check(d, t)
        max_R = max(pile_service_loads)
        if is_safe and (max_R <= pile_cap):
            break
        d += 0.02
else:
    # รันรอบเดียวตามตัวเลขที่กรอกมาในปุ่ม Manual
    t = manual_t
    d = t - 0.15
    is_safe = run_structural_check(d, t)
    if not is_safe:
        shear_fail_manual = True

d_actual = d

# --- 6. REINFORCEMENT LOGIC ---
M_u_X_pos = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2 and pile_ultimate_loads[i] > 0)
M_u_Y_pos = sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2 and pile_ultimate_loads[i] > 0)

def design_steel_v55(M_u_val, w_cm, d_cm, t_cm):
    if M_u_val <= 0: As_req = 0.0018 * w_cm * t_cm
    else:
        Rn = (M_u_val * 1000 * 100) / (phi_b * w_cm * d_cm**2)
        rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * fc_prime))) if (2 * Rn) / (0.85 * fc_prime) < 1.0 else 0.002
        rho_min = max(0.83 * math.sqrt(fc_prime) / fy, 14.0 / fy)
        As_req = max(rho * w_cm * d_cm, rho_min * w_cm * d_cm, 0.0018 * w_cm * t_cm)
    n_bars = max(math.ceil(As_req / ab), 6)
    sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, sp

num_X_bot, sp_X_bot = design_steel_v55(M_u_X_pos, B_ft*100, d_actual*100, t*100)
num_Y_bot, sp_Y_bot = design_steel_v55(M_u_Y_pos, L_ft*100, d_actual*100, t*100)

# --- 7. UI RENDERING AND REPORT ---
st.markdown("### 📊 ผลการตรวจสอบและจัดมิติฐานรากควบคุม")
st.info(f"📐 **โหมดที่เลือก:** {thickness_mode} | **ความหนารวม t:** {t*100:.0f} ซม. | **ความหนาประสิทธิผล d:** {d_actual*100:.0f} ซม.")

if shear_fail_manual:
    st.error("🚨 [CRITICAL WEAKNESS] ความหนาที่คุณป้อนเข้ามา 'น้อยเกินไป' ทำให้คอนกรีตพังทลายจากแรงเฉือนทะลุหรือแรงเฉือนคานกว้าง! กรุณาเพิ่มความหนา t ในช่องกรอก")
else:
    st.success("✅ ค่าหน่วยแรงเฉือนและพฤติกรรมโครงสร้างผ่านเกณฑ์ทั้งหมดอย่างปลอดภัย")

# ตารางเปรียบเทียบค่าแรงเฉือน
df_shear = pd.DataFrame({
    "ประเภทหน่วยแรงเฉือนวิกฤต": ["Punching Shear (แรงเฉือนทะลุ)", "Wide Beam Shear (แรงเฉือนคานกว้าง)"],
    "หน่วยแรงเกิดขึ้นจริง": [v_u_stress, v_u_wb_stress],
    "กำลังต้านทานคอนกรีตที่ยอมให้": [v_c_allowable, v_c_wb_allowable]
})
st.dataframe(df_shear, column_config={
    "หน่วยแรงเกิดขึ้นจริง": st.column_config.NumberColumn("หน่วยแรงจริง (v_u)", format="%.2f ksc"),
    "กำลังต้านทานคอนกรีตที่ยอมให้": st.column_config.NumberColumn("กำลังควบคุม (phi * vc)", format="%.2f ksc")
}, use_container_width=True, hide_index=True)

# แปลนรูปตัดแบบย่อ
fig, ax = plt.subplots(figsize=(6, 2))
ax.add_patch(patches.Rectangle((-B_ft/2, 0), B_ft, t, facecolor='#eaeded', edgecolor='#2c3e50', linewidth=2))
ax.plot([-B_ft/2+0.075, B_ft/2-0.075], [0.075, 0.075], color='#1f618d', linewidth=2)
ax.text(0, t/2, f"t = {t*100:.0f} cm\nDB{bar_dia} @ {sp_X_bot} cm", ha='center', va='center', fontweight='bold', fontsize=9)
ax.set_xlim(-B_ft/2-0.2, B_ft/2+0.2)
ax.set_ylim(-0.1, t+0.2)
ax.axis('off')
st.pyplot(fig)
