import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Enterprise Footing Suite V5.7", page_icon="🏗️", layout="wide")

st.title("🏗️ Enterprise Footing Suite (V5.7 - Code-Compliant Masterpiece)")
st.markdown("ระบบวิเคราะห์ฐานรากชั้นสูง | แก้ไขตรรกะโมเมนต์ลบ + ระบบดักจับ Over-reinforced + แยกขาดหน่วยแรงเฉือนฐานราก")
st.markdown("---")

# --- 2. SIDEBAR PARAMETERS ---
with st.sidebar:
    st.header("⚙️ มาตรฐานและข้อกำหนดการออกแบบ")
    
    st.subheader("1. รูปแบบกลุ่มเสาเข็ม & รูปทรงเรขาคณิต")
    n_piles = st.selectbox("จำนวนเสาเข็มในฐานราก:", [2, 3, 4, 5, 6, 8, 9], index=4)
    pile_shape = st.selectbox("รูปทรงหน้าตัดเสาเข็ม:", ["สี่เหลี่ยมตัน (Square Pile)", "กลมกลวง/สปัน (Spun Pile)", "กลมตัน/เข็มเจาะ (Solid Round Pile)"])
    pile_size = st.number_input("ขนาดเส้นผ่านศูนย์กลางภายนอก หรือความกว้างเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    # พารามิเตอร์ความหนาผนังเสาเข็มสำหรับ Spun Pile (ใช้สำหรับแสดงผลทางกายภาพเท่านั้น ไม่นำไปลดทอนแรงเฉือนฐานราก)
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

    st.sidebar.markdown("---")
    st.subheader("🎛️ 4. ควบคุมความหนาฐานราก (t)")
    thickness_mode = st.radio("โหมดการคำนวณความหนา:", ["คำนวณอัตโนมัติ (Auto-Optimize)", "ป้อนความหนาเอง (Manual Override)"])
    
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

# --- 5. AS-BUILT DEVIATION ENGINE ---
st.markdown("### 📍 1. ระบบประมวลผลเสาเข็มเยื้องศูนย์หน้างานจริง (True Center of Gravity)")
exp_dev = st.expander("🛠️ คลิกเพื่อใส่ค่ารังวัดความคลาดเคลื่อนของเสาเข็ม (As-Built Coordinate Deviations)", expanded=False)
deviations = []
with exp_dev:
    cc1, cc2, cc3 = st.columns(3)
    for i in range(n_piles):
        if i % 3 == 0: col = cc1
        elif i % 3 == 1: col = cc2
        else: col = cc3
        with col:
            dx_cm = st.number_input(f"เข็มต้นที่ {i+1} หนีศูนย์แกน X (ซม.)", value=0.0, step=1.0, key=f"dev_x_{i}")
            dy_cm = st.number_input(f"เข็มต้นที่ {i+1} หนีศูนย์แกน Y (ซม.)", value=0.0, step=1.0, key=f"dev_y_{i}")
            deviations.append((dx_cm / 100, dy_cm / 100))

piles_actual = [(piles_ideal[i][0] + deviations[i][0], piles_ideal[i][1] + deviations[i][1]) for i in range(n_piles)]
cg_new_x = sum(p[0] for p in piles_actual) / n_piles
cg_new_y = sum(p[1] for p in piles_actual) / n_piles

e_x = 0.0 - cg_new_x
e_y = 0.0 - cg_new_y

piles_relative = [(p[0] - cg_new_x, p[1] - cg_new_y) for p in piles_actual]
sum_x2_new = sum(p[0]**2 for p in piles_relative)
sum_y2_new = sum(p[1]**2 for p in piles_relative)

# มิติขอบเขตภายนอกฐานราก
B_ft = (max(p[0] for p in piles_actual) - min(p[0] for p in piles_actual)) + 2*E_dist
L_ft = (max(p[1] for p in piles_actual) - min(p[1] for p in piles_actual)) + 2*E_dist

x_max_edge = max(p[0] for p in piles_actual) + E_dist
x_min_edge = min(p[0] for p in piles_actual) - E_dist
y_max_edge = max(p[1] for p in piles_actual) + E_dist
y_min_edge = min(p[1] for p in piles_actual) - E_dist

# --- 6. CORE STRUCTURAL EVALUATION ENGINE ---
d = 0.40 if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)" else (manual_t - 0.15)
t = 0.55 if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)" else manual_t

has_tension = False
loop_break_by_guard = False
over_reinforced_global_error = False
shear_fail_manual = False

v_u_stress, v_c_allowable = 0.0, 0.0
v_u_wb_stress, v_c_wb_allowable = 0.0, 0.0
pile_service_loads = [0.0] * n_piles
pile_ultimate_loads = [0.0] * n_piles
previous_max_R = float('inf')
r_outer = pile_size / 2

def run_structural_calculation_core(current_d, current_t):
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
    
    # 🛑 [CORRECTION 2] ตรวจสอบ Punching Shear บนเนื้อคอนกรีตฐานรากเต็มหน้าตัด (ไม่มีการหักรูเจาะ Spun Pile)
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
    
    # Wide Beam Shear Check (4-Faces) หน้าตัดเนื้อคอนกรีตฐานรากเต็มพิกัดเช่นกัน
    X_crit_pos = cx/2 + current_d
    X_crit_neg = -cx/2 - current_d
    Y_crit_pos = cy/2 + current_d
    Y_crit_neg = -cy/2 - current_d
    V_wb_X_pos, V_wb_X_neg, V_wb_Y_pos, V_wb_Y_neg = 0.0, 0.0, 0.0, 0.0
    
    for i, (px, py) in enumerate(piles_actual):
        pu_load = max(0.0, pile_ultimate_loads[i] * 1000)
        if px - r_outer >= X_crit_pos: V_wb_X_pos += pu_load
        if px + r_outer <= X_crit_neg: V_wb_X_neg += pu_load
        if py - r_outer >= Y_crit_pos: V_wb_Y_pos += pu_load
        if py + r_outer <= Y_crit_neg: V_wb_Y_neg += pu_load

    v_wb_X_pos = V_wb_X_pos / (L_ft * 100 * current_d * 100)
    v_wb_X_neg = V_wb_X_neg / (L_ft * 100 * current_d * 100)
    v_wb_Y_pos = V_wb_Y_pos / (B_ft * 100 * current_d * 100)
    v_wb_Y_neg = V_wb_Y_neg / (B_ft * 100 * current_d * 100)
    
    v_u_wb_stress = max(v_wb_X_pos, v_wb_X_neg, v_wb_Y_pos, v_wb_Y_neg)
    v_c_wb_allowable = phi_v * 0.53 * math.sqrt(fc_prime)
    
    return (v_u_stress <= v_c_allowable) and (v_u_wb_stress <= v_c_wb_allowable)

# เริ่มต้นลูปคำนวณแยกโหมดทำงาน
if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)":
    while d < 3.0:
        t = math.ceil((d + 0.15) * 20) / 20
        is_safe = run_structural_calculation_core(d, t)
        max_R = max(pile_service_loads)
        min_R = min(pile_service_loads)
        
        if (max_R > pile_cap or (has_tension and abs(min_R) > pile_tension_cap)) and max_R >= previous_max_R:
            loop_break_by_guard = True
            break
        previous_max_R = max_R
        
        if is_safe and (max_R <= pile_cap) and (not has_tension or abs(min_R) <= pile_tension_cap):
            break
        d += 0.02
else:
    t = manual_t
    d = t - 0.15
    is_safe = run_structural_calculation_core(d, t)
    if not is_safe or (max(pile_service_loads) > pile_cap):
        shear_fail_manual = True

d_actual = t - 0.15
w_u_sw_floor = 1.2 * t * 2.4 # น้ำหนักประลัยฐานรากต่อตารางเมตร (ตัน/ตร.ม.)

# 🛑 [CORRECTION 3] ตรรกะกลศาสตร์รวมสำหรับโมเมนต์ดัดตามขอบตอม่อ (พิจารณาน้ำหนักฐานรากยื่นร่วมด้วย)
M_u_X_pos_plane = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2) - 0.5 * w_u_sw_floor * ((x_max_edge - cx/2)**2) * L_ft
M_u_X_neg_plane = sum(pile_ultimate_loads[i] * (-cx/2 - p[0]) for i, p in enumerate(piles_actual) if p[0] < -cx/2) - 0.5 * w_u_sw_floor * ((-cx/2 - x_min_edge)**2) * L_ft
M_u_Y_pos_plane = sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2) - 0.5 * w_u_sw_floor * ((y_max_edge - cy/2)**2) * B_ft
M_u_Y_neg_plane = sum(pile_ultimate_loads[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2) - 0.5 * w_u_sw_floor * ((-cy/2 - y_min_edge)**2) * B_ft

M_u_X_bot = max(0.0, M_u_X_pos_plane, M_u_X_neg_plane)
M_u_X_top = max(0.0, -M_u_X_pos_plane, -M_u_X_neg_plane)
M_u_Y_bot = max(0.0, M_u_Y_pos_plane, M_u_Y_neg_plane)
M_u_Y_top = max(0.0, -M_u_Y_pos_plane, -M_u_Y_neg_plane)

# 🛑 [CORRECTION 1] ฟังก์ชันคำนวณจัดเหล็กเสริมพร้อมระบบตรวจสอบ Over-reinforced Section ป้องกันแอปพลิเคชันล่ม
def design_steel_flexure_v57(M_u_val, w_cm, d_cm, t_cm, f_c, f_y):
    As_min = 0.0018 * w_cm * t_cm
    if M_u_val <= 0:
        n_bars = max(math.ceil(As_min / ab), 6)
        sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
        return n_bars, sp, False, False

    M_u_kg_cm = M_u_val * 1000 * 100
    Rn = M_u_kg_cm / (phi_b * w_cm * d_cm**2)
    
    # คำนวณขีดจำกัดสูงสุดตามมาตรฐานวิศวกรรมควบคุมป้องกันการวิบัติแบบเปราะ
    beta_1 = 0.85 if f_c <= 280 else max(0.65, 0.85 - 0.05 * (f_c - 280) / 70)
    rho_b = 0.85 * beta_1 * (f_c / f_y) * (6120 / (6120 + f_y))
    rho_max = 0.75 * rho_b  # อัตราส่วนเหล็กเสริมสูงสุดที่อนุญาตให้สอดคล้องกับมาตรฐานความปลอดภัย
    
    Rn_max = rho_max * f_y * (1 - 0.59 * rho_max * f_y / f_c)
    
    # ตรวจจับวิกฤต Math Crash และ Over-reinforced Section
    if (2 * Rn) / (0.85 * f_c) >= 1.0 or Rn > Rn_max:
        return 0, 0, False, True  # ส่งสัญญาณ Flag ความผิดพลาดทันที
        
    rho = (0.85 * f_c / f_y) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * f_c)))
    if rho > rho_max:
        return 0, 0, False, True

    rho_min_flex = max(0.83 * math.sqrt(f_c) / f_y, 14.0 / f_y)
    As_req = max(rho * w_cm * d_cm, rho_min_flex * w_cm * d_cm, As_min)
    
    n_bars = max(math.ceil(As_req / ab), 6)
    sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    max_allowable_sp = min(3 * t_cm, 45.0)
    while sp > max_allowable_sp:
        n_bars += 1
        sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, sp, (sp < max(1.5 * (bar_dia / 10), 2.5)), False

# รันระบบคำนวณเหล็กสี่ทิศทาง
num_X_bot, sp_X_bot, cong_X_bot, err_X_bot = design_steel_flexure_v57(M_u_X_bot, B_ft*100, d_actual*100, t*100, fc_prime, fy)
num_Y_bot, sp_Y_bot, cong_Y_bot, err_Y_bot = design_steel_flexure_v57(M_u_Y_bot, L_ft*100, d_actual*100, t*100, fc_prime, fy)
num_X_top, sp_X_top, cong_X_top, err_X_top = design_steel_flexure_v57(M_u_X_top, B_ft*100, d_actual*100, t*100, fc_prime, fy)
num_Y_top, sp_Y_top, cong_Y_top, err_Y_top = design_steel_flexure_v57(M_u_Y_top, L_ft*100, d_actual*100, t*100, fc_prime, fy)

any_over_reinforced = err_X_bot or err_Y_bot or err_X_top or err_Y_top
any_congested = cong_X_bot or cong_Y_bot or cong_X_top or cong_Y_top

# --- 7. 2D ENGINEERING BLUEPRINT ---
st.markdown("### 📊 2. แบบวิศวกรรมและการจัดเหล็กเสริมโครงสร้าง (2D Engineering Blueprint)")
fig_2d, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(15, 6))

rect_cap = patches.Rectangle((min(p[0] for p in piles_actual)-E_dist, min(p[1] for p in piles_actual)-E_dist), B_ft, L_ft, linewidth=2, edgecolor='#2c3e50', facecolor='#ecf0f1', zorder=1)
ax_plan.add_patch(rect_cap)
ax_plan.add_patch(patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.5, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4))
ax_plan.scatter(cg_new_x, cg_new_y, color='#f39c12', marker='X', s=100, zorder=5)

for i, (px, py) in enumerate(piles_actual):
    if "กลม" in pile_shape:
        ax_plan.add_patch(patches.Circle((px, py), r_outer, linewidth=1.2, edgecolor='#7f8c8d', facecolor='#bdc3c7', zorder=3))
        if wall_thickness > 0:
            ax_plan.add_patch(patches.Circle((px, py), r_outer - wall_thickness, linewidth=0.8, edgecolor='#95a5a6', facecolor='#ecf0f1', linestyle=':', zorder=3))
    else:
        ax_plan.add_patch(patches.Rectangle((px-r_outer, py-r_outer), pile_size, pile_size, linewidth=1.2, edgecolor='#7f8c8d', facecolor='#bdc3c7', zorder=3))
    ax_plan.text(px, py, f"P{i+1}", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold', zorder=4)

ax_plan.set_xlim(min(p[0] for p in piles_actual)-E_dist-0.3, max(p[0] for p in piles_actual)+E_dist+0.3)
ax_plan.set_ylim(min(p[1] for p in piles_actual)-E_dist-0.3, max(p[1] for p in piles_actual)+E_dist+0.3)
ax_plan.set_aspect('equal')
ax_plan.grid(True, linestyle=':', alpha=0.5)

# Cross Section Plot
ax_sec.add_patch(patches.Rectangle((-B_ft/2, 0), B_ft, t, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded'))
ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [0.075, 0.075], color='#1f618d', linewidth=2.5)
ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [t-0.075, t-0.075], color='#27ae60', linewidth=2.0, linestyle='--')
ax_sec.text(0, t/2, f"Thickness t = {t*100:.0f} cm\nBot X: DB{bar_dia} @ {sp_X_bot} cm\nTop X: DB{bar_dia} @ {sp_X_top} cm" if not any_over_reinforced else "CRITICAL ERROR:\nOVER-REINFORCED", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold')
ax_sec.set_xlim(-B_ft/2 - 0.3, B_ft/2 + 0.3)
ax_sec.set_ylim(-0.1, t + 0.5)
ax_sec.set_aspect('equal')
ax_sec.axis('off')
st.pyplot(fig_2d)

# --- 8. OUTPUT DATA TABS ---
tab1, tab2, tab3 = st.tabs(["📝 ผลการประเมินสถิตศาสตร์เชิงลึก", "🎮 มิติและรูปร่าง 3D Solid Render", "📋 ตารางสรุปหน่วยแรงและการจัดเรียงตัวเลข"])

with tab1:
    st.markdown("### 🏢 สรุปความหนาและมิติโครงสร้างควบคุม")
    st.info(f"📐 **ความหนาฐานรากทั้งหมด (Total Thickness, t):** {t*100:.0f} ซม. | **ความหนาประสิทธิผล (Effective Depth, d):** {d_actual*100:.0f} ซม.")
    
    # แสดงบล็อกแจ้งเตือนข้อผิดพลาดพฤติกรรมโครงสร้างตามจริง
    if any_over_reinforced:
        st.error("🚨 [CRITICAL FLEXURE ERROR - OVER-REINFORCED SECTION] ปริมาณเหล็กเสริมดึงหน้าตัดวิกฤตสูงเกินพิกัดควบคุม ($\rho > \rho_{max}$) เสี่ยงต่อการวิบัติพังทลายแบบเปราะในเนื้อคอนกรีตทันที มาตรฐาน ACI/มยผ. ห้ามออกแบบลักษณะนี้เด็ดขาด! แก้ไข: กรุณาเพิ่มความหนาฐานราก t ในช่องกรอกไซด์บาร์ทันที")
    elif shear_fail_manual:
        st.error("🚨 [OVERSTRESS ALERT] ในโหมดกรอกมือ ความหนาที่ใส่เข้ามาต่ำเกินไปจนหน่วยแรงเฉือนทะลุพังลิมิต! กรุณาเพิ่มค่าตัวเลขหนา t")
    else:
        st.success("✅ พฤติกรรมแรงเฉือนและสัดส่วนปริมาณเหล็กเสริมผ่านเกณฑ์ตามมาตรฐานวิศวกรรมควบคุมความปลอดภัย")

    st.caption("ℹ️ *หมายเหตุความปลอดภัยแรงเฉือน:* ตามหลักกลศาสตร์ร่วม หน่วยแรงเฉือนวิกฤตจะถูกคำนวณและตรวจสอบบนเนื้อคอนกรีตฐานรากเต็มหน้าตัดโดยไม่มีการหักพื้นที่รูกลวงของเข็มสปันออก เพื่อรักษามาตรฐานความต้านทานแรงทะลุสูงสุดให้หน้างาน")

    if t >= 0.60:
        st.warning(f"⚠️ [Skin Reinforcement Note] ความหนาฐานราก t = {t*100:.0f} ซม. ($\ge 60$ ซม.) ต้องเสริมเหล็กผิวข้าง (Side Face) เพื่อต้านทานการแตกร้าวเนื่องจากอุณหภูมิ")

    c1, c2, c3 = st.columns(3)
    c1.metric("ขนาดฐานราก กว้าง x ยาว", f"{B_ft:.2f} x {L_ft:.2f} ม.")
    c2.metric("แรงอัดเข็มสูงสุด (Max Compression)", f"{max(pile_service_loads):.2f} ตัน/ต้น")
    c3.metric("แรงดึงเข็มสูงสุด (Max Uplift/Tension)", f"{min(pile_service_loads):.2f} ตัน/ต้น")

    if not any_over_reinforced:
        st.markdown("### 🧾 รายละเอียดปริมาณเหล็กเส้นสั่งตัดหน้างาน")
        st.markdown(f"* 🔹 **เหล็กตะแกรงล่าง (ทิศ X):** DB{bar_dia} จำนวน **{num_X_bot}** เส้น @ **{sp_X_bot:.0f}** ซม.")
        st.markdown(f"* 🔹 **เหล็กตะแกรงล่าง (ทิศ Y):** DB{bar_dia} จำนวน **{num_Y_bot}** เส้น @ **{sp_Y_bot:.0f}** ซม.")
        st.markdown(f"* 🔸 **เหล็กตะแกรงบน (ทิศ X):** DB{bar_dia} จำนวน **{num_X_top}** เส้น @ **{sp_X_top:.0f}** ซม. *(คำนวณถ่วงดุลปีกฐานรากยื่นแล้ว)*")
        st.markdown(f"* 🔸 **เหล็กตะแกรงบน (ทิศ Y):** DB{bar_dia} จำนวน **{num_Y_top}** เส้น @ **{sp_Y_top:.0f}** ซม. *(คำนวณถ่วงดุลปีกฐานรากยื่นแล้ว)*")

with tab2:
    x_cap = [min(p[0] for p in piles_actual)-E_dist, max(p[0] for p in piles_actual)+E_dist]
    y_cap = [min(p[1] for p in piles_actual)-E_dist, max(p[1] for p in piles_actual)+E_dist]
    v_x = [x_cap[0], x_cap[1], x_cap[1], x_cap[0], x_cap[0], x_cap[1], x_cap[1], x_cap[0]]
    v_y = [y_cap[0], y_cap[0], y_cap[1], y_cap[1], y_cap[0], y_cap[0], y_cap[1], y_cap[1]]
    v_z = [0, 0, 0, 0, t, t, t, t]
    
    fig_3d = go.Figure(data=[
        go.Mesh3d(
            x=v_x, y=v_y, z=v_z,
            i=[0, 0, 4, 4, 0, 1, 2, 3, 0, 1, 5, 4],
            j=[1, 2, 5, 6, 4, 5, 6, 7, 3, 2, 6, 7],
            k=[2, 3, 6, 7, 1, 2, 3, 0, 4, 5, 2, 3],
            opacity=0.6, color='#3498db', name='Footing Body'
        )
    ])
    fig_3d.update_layout(scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)'), title="3D Interactive Real Geometry View")
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.markdown("### ⚔️ ตารางสรุปหน่วยแรงเฉือนวิกฤต")
    df_shear = pd.DataFrame({
        "ประเภทการตรวจสอบ": ["Punching Shear (Combined Jc Method)", "Wide Beam Shear (Fractional Surface Method)"],
        "หน่วยแรงเกิดขึ้นจริง": [v_u_stress, v_u_wb_stress],
        "กำลังต้านทานคอนกรีตที่ยอมให้": [v_c_allowable, v_c_wb_allowable]
    })
    st.dataframe(df_shear, column_config={
        "หน่วยแรงเกิดขึ้นจริง": st.column_config.NumberColumn("หน่วยแรงเกิดขึ้นจริง (v_u)", format="%.2f ksc"),
        "กำลังต้านทานคอนกรีตที่ยอมให้": st.column_config.NumberColumn("กำลังที่ยอมให้ (phi * vc)", format="%.2f ksc")
    }, use_container_width=True, hide_index=True)
    
    st.markdown("### 📊 ตารางแสดงแรงปฏิกิริยารายต้น (Copy ไปลง Excel ได้เลย)")
    df_piles_report = pd.DataFrame({
        "เสาเข็ม": [f"ต้นที่ {i+1}" for i in range(n_piles)],
        "พิกัด X จริง (ม.)": [p[0] for p in piles_actual],
        "พิกัด Y จริง (ม.)": [p[1] for p in piles_actual],
        "แรงใช้งาน Service Load": pile_service_loads,
        "แรงประลัย Ultimate Load": pile_ultimate_loads
    })
    st.dataframe(df_piles_report, column_config={
        "พิกัด X จริง (ม.)": st.column_config.NumberColumn("พิกัด Xจริง", format="%.3f ม."),
        "พิกัด Y จริง (ม.)": st.column_config.NumberColumn("พิกัด Yจริง", format="%.3f ม."),
        "แรงใช้งาน Service Load": st.column_config.NumberColumn("แรงใช้งาน Service Load", format="%.2f ตัน"),
        "แรงประลัย Ultimate Load": st.column_config.NumberColumn("แรงประลัย Ultimate Load", format="%.2f ตัน")
    }, use_container_width=True, hide_index=True)
