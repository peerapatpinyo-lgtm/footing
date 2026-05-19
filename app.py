import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Enterprise Footing Suite V5.2", page_icon="🏗️", layout="wide")

st.title("🏗️ Enterprise Footing Suite (V5.2 - Production-Grade)")
st.markdown("ระบบวิเคราะห์ฐานรากขั้นสูง | สัดส่วนพื้นที่เข็มผ่าหน้าตัดวิกฤต | ตรวจสอบแรงถอนปลอดภัย | ป้องกัน Over-reinforced Math Crash")
st.markdown("---")

# --- 2. SIDEBAR PARAMETERS ---
with st.sidebar:
    st.header("⚙️ มาตรฐานและข้อกำหนดการออกแบบ")
    
    st.subheader("1. รูปแบบกลุ่มเสาเข็ม & หน้าตัด")
    n_piles = st.selectbox("จำนวนเสาเข็มในฐานราก:", [2, 3, 4, 5, 6, 8, 9], index=4)
    pile_shape = st.selectbox("รูปทรงหน้าตัดเสาเข็ม:", ["สี่เหลี่ยม (Square Pile)", "กลม (Round/Spun/Bore Pile)"])
    pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.30, step=0.05)
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

# --- 5. AS-BUILT DEVIATION & TRUE C.G. ENGINE ---
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

# --- 6. CORE LOOP WITH FRACTIONAL SHEAR & CAPACITY GUARDS ---
d = 0.40
t = 0.55
has_tension = False
loop_break_by_guard = False
over_reinforced_error = False

B_ft = (max(p[0] for p in piles_actual) - min(p[0] for p in piles_actual)) + 2*E_dist
L_ft = (max(p[1] for p in piles_actual) - min(p[1] for p in piles_actual)) + 2*E_dist

v_u_stress, v_c_allowable = 0.0, 0.0
v_u_wb_stress, v_c_wb_allowable = 0.0, 0.0
pile_service_loads = [0.0] * n_piles
pile_ultimate_loads = [0.0] * n_piles
previous_max_R = float('inf')

r_pile = pile_size / 2

while d < 3.0:
    t = math.ceil((d + 0.15) * 20) / 20
    W_f_actual = B_ft * L_ft * t * 2.4
                 
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
    
    # 🛑 Guard 1: Weight-Paradox & Tension Capacity Guard
    if (max_R > pile_cap or (has_tension and abs(min_R) > pile_tension_cap)) and max_R >= previous_max_R:
        loop_break_by_guard = True
        break
    previous_max_R = max_R
    
    # --- J_c Punching Shear Calculations ---
    b1 = cx + d
    b2 = cy + d
    bo = 2 * (b1 + b2)
    A_c = bo * d * 10000  
    
    gamma_vx = 1 - (1 / (1 + (2/3) * math.sqrt(b1 / b2)))
    gamma_vy = 1 - (1 / (1 + (2/3) * math.sqrt(b2 / b1)))
    
    J_cx = (d * (b1**3) / 6) + ((b1 * (d**3)) / 6) + (d * b2 * (b1**2) / 2)
    J_cy = (d * (b2**3) / 6) + ((b2 * (d**3)) / 6) + (d * b1 * (b2**2) / 2)
    
    V_u_p_kg = 0
    for i, (px, py) in enumerate(piles_actual):
        if abs(px) > (cx/2 + d/2) or abs(py) > (cy/2 + d/2):
            V_u_p_kg += max(0, pile_ultimate_loads[i] * 1000)
            
    v_u_stress = (V_u_p_kg / A_c) + (gamma_vx * abs(Mu_x_loop) * 100000 * (b2/2) / (J_cx * 1000000)) + (gamma_vy * abs(Mu_y_loop) * 100000 * (b1/2) / (J_cy * 1000000))
    
    beta_col = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
    vc1 = 0.27 * (2 + 4/beta_col) * math.sqrt(fc_prime)
    vc2 = 0.27 * (alpha_s * (d * 100) / (bo * 100) + 2) * math.sqrt(fc_prime)
    vc3 = 1.06 * math.sqrt(fc_prime)
    v_c_allowable = phi_v * min(vc1, vc2, vc3)
    
    # --- 📐 Advanced Fractional Wide Beam Shear Check (4-Faces) ---
    X_crit_pos = cx/2 + d
    X_crit_neg = -cx/2 - d
    Y_crit_pos = cy/2 + d
    Y_crit_neg = -cy/2 - d
    
    V_wb_X_pos, V_wb_X_neg = 0.0, 0.0
    V_wb_Y_pos, V_wb_Y_neg = 0.0, 0.0
    
    for i, (px, py) in enumerate(piles_actual):
        pu_load = max(0.0, pile_ultimate_loads[i] * 1000)
        
        # X-Positive Face (Resisted by L_ft width)
        if px - r_pile >= X_crit_pos: f_xp = 1.0
        elif px + r_pile <= X_crit_pos: f_xp = 0.0
        else: f_xp = (px + r_pile - X_crit_pos) / pile_size
        V_wb_X_pos += pu_load * f_xp
        
        # X-Negative Face (Resisted by L_ft width)
        if px + r_pile <= X_crit_neg: f_xn = 1.0
        elif px - r_pile >= X_crit_neg: f_xn = 0.0
        else: f_xn = (X_crit_neg - (px - r_pile)) / pile_size
        V_wb_X_neg += pu_load * f_xn
        
        # Y-Positive Face (Resisted by B_ft width)
        if py - r_pile >= Y_crit_pos: f_yp = 1.0
        elif py + r_pile <= Y_crit_pos: f_yp = 0.0
        else: f_yp = (py + r_pile - Y_crit_pos) / pile_size
        V_wb_Y_pos += pu_load * f_yp
        
        # Y-Negative Face (Resisted by B_ft width)
        if py + r_pile <= Y_crit_neg: f_yn = 1.0
        elif py - r_pile >= Y_crit_neg: f_yn = 0.0
        else: f_yn = (Y_crit_neg - (py - r_pile)) / pile_size
        V_wb_Y_neg += pu_load * f_yn

    v_wb_X_pos = V_wb_X_pos / (L_ft * 100 * d * 100)
    v_wb_X_neg = V_wb_X_neg / (L_ft * 100 * d * 100)
    v_wb_Y_pos = V_wb_Y_pos / (B_ft * 100 * d * 100)
    v_wb_Y_neg = V_wb_Y_neg / (B_ft * 100 * d * 100)
    
    v_u_wb_stress = max(v_wb_X_pos, v_wb_X_neg, v_wb_Y_pos, v_wb_Y_neg)
    v_c_wb_allowable = phi_v * 0.53 * math.sqrt(fc_prime)
    
    # --- 🛑 Guard 2: Mathematical Protection for Steel Over-reinforced Check ---
    M_u_X_pos = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2 and pile_ultimate_loads[i] > 0)
    Rn_check = (M_u_X_pos * 1000 * 100) / (phi_b * (B_ft * 100) * (d * 100)**2)
    if (2 * Rn_check) / (0.85 * fc_prime) >= 1.0:
        d += 0.05  # เร่งขยายความหนาหนีโซนพังทลาย
        if d >= 3.0:
            over_reinforced_error = True
        continue
        
    if (v_u_stress <= v_c_allowable) and (v_u_wb_stress <= v_c_wb_allowable) and (max_R <= pile_cap) and (not has_tension or abs(min_R) <= pile_tension_cap):
        break
    d += 0.02

d_actual = t - 0.15

# --- 7. ADVANCED REINFORCEMENT & SPACING ENGINE ---
M_u_X_pos = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2 and pile_ultimate_loads[i] > 0)
M_u_X_neg = abs(sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2 and pile_ultimate_loads[i] < 0))
M_u_Y_pos = sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2 and pile_ultimate_loads[i] > 0)
M_u_Y_neg = abs(sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2 and pile_ultimate_loads[i] < 0))

def design_steel_flexure_v52(M_u_val, w_cm, d_cm, t_cm):
    if M_u_val <= 0:
        As_req = 0.0018 * w_cm * t_cm
    else:
        M_u_kg_cm = M_u_val * 1000 * 100
        Rn = M_u_kg_cm / (phi_b * w_cm * d_cm**2)
        if (2 * Rn) / (0.85 * fc_prime) >= 1.0:
            rho = 0.002
        else:
            rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * fc_prime)))
        rho_min_flex = max(0.83 * math.sqrt(fc_prime) / fy, 14.0 / fy)
        As_req = max(rho * w_cm * d_cm, rho_min_flex * w_cm * d_cm, 0.0018 * w_cm * t_cm)
        
    n_bars = max(math.ceil(As_req / ab), 6)
    sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    
    # 📏 Max Spacing Control Check
    max_allowable_sp = min(3 * t_cm, 45.0)
    while sp > max_allowable_sp:
        n_bars += 1
        sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
        
    # 📏 Min Spacing Verification
    min_allowable_sp = max(1.5 * (bar_dia / 10), 2.5)
    is_congested = sp < min_allowable_sp
    
    return n_bars, sp, is_congested

num_X_bot, sp_X_bot, cong_X_bot = design_steel_flexure_v52(M_u_X_pos, B_ft*100, d_actual*100, t*100)
num_Y_bot, sp_Y_bot, cong_Y_bot = design_steel_flexure_v52(M_u_Y_pos, L_ft*100, d_actual*100, t*100)
num_X_top, sp_X_top, cong_X_top = design_steel_flexure_v52(M_u_X_neg, B_ft*100, d_actual*100, t*100)
num_Y_top, sp_Y_top, cong_Y_top = design_steel_flexure_v52(M_u_Y_neg, L_ft*100, d_actual*100, t*100)

any_congested = cong_X_bot or cong_Y_bot or cong_X_top or cong_Y_top

# --- 8. 2D ENGINEERING BLUEPRINT ---
st.markdown("### 📊 2. แบบวิศวกรรมและการจัดเหล็กเสริมโครงสร้าง (2D Engineering Blueprint)")
fig_2d, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(15, 7))

ax_plan.set_title("แปลนการจัดเรียงเสาเข็มและระยะขอบฐานราก (Top View)", fontsize=11, fontweight='bold', pad=10)
rect_cap = patches.Rectangle((min(p[0] for p in piles_actual)-E_dist, min(p[1] for p in piles_actual)-E_dist), B_ft, L_ft, linewidth=2, edgecolor='#2c3e50', facecolor='#ecf0f1', zorder=1)
ax_plan.add_patch(rect_cap)
rect_col = patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.5, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4, label='Column')
ax_plan.add_patch(rect_col)
ax_plan.scatter(cg_new_x, cg_new_y, color='#f39c12', marker='X', s=120, zorder=5, label='True C.G. (Shifted)')

for i, (px, py) in enumerate(piles_actual):
    if "กลม" in pile_shape:
        p_draw = patches.Circle((px, py), pile_size/2, linewidth=1.2, edgecolor='#7f8c8d', facecolor='#bdc3c7', zorder=3)
    else:
        p_draw = patches.Rectangle((px-pile_size/2, py-pile_size/2), pile_size, pile_size, linewidth=1.2, edgecolor='#7f8c8d', facecolor='#bdc3c7', zorder=3)
    ax_plan.add_patch(p_draw)
    ax_plan.text(px, py, f"P{i+1}", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold', zorder=4)

ax_plan.set_xlim(min(p[0] for p in piles_actual)-E_dist-0.3, max(p[0] for p in piles_actual)+E_dist+0.3)
ax_plan.set_ylim(min(p[1] for p in piles_actual)-E_dist-0.3, max(p[1] for p in piles_actual)+E_dist+0.3)
ax_plan.grid(True, linestyle=':', alpha=0.5)
ax_plan.set_aspect('equal')

ax_sec.set_title("รูปตัดโครงสร้างแสดงตะแกรงเหล็ก บน-ล่าง (Cross Section)", fontsize=11, fontweight='bold', pad=10)
ax_sec.fill_between([-B_ft/2, B_ft/2], -0.15, -0.10, color='#f5cba7', alpha=0.7)
ax_sec.fill_between([-B_ft/2, B_ft/2], -0.10, 0.0, color='#d5dbdb', alpha=0.9)
ax_sec.add_patch(patches.Rectangle((-B_ft/2, 0), B_ft, t, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded'))
ax_sec.add_patch(patches.Rectangle((-cx/2, t), cx, 0.5, linewidth=1.5, edgecolor='#e74c3c', facecolor='#f1948a'))

ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [0.075, 0.075], color='#1f618d', linewidth=2.5, label='Bottom Rebar')
ax_sec.plot([-B_ft/2+0.075, -B_ft/2+0.075], [0.075, 0.225], color='#1f618d', linewidth=2.5)
ax_sec.plot([B_ft/2-0.075, B_ft/2-0.075], [0.075, 0.225], color='#1f618d', linewidth=2.5)

ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [t-0.075, t-0.075], color='#27ae60', linewidth=2.0, linestyle='--', label='Top Rebar')
ax_sec.plot([-B_ft/2+0.075, -B_ft/2+0.075], [t-0.075, t-0.225], color='#27ae60', linewidth=2.0, linestyle='--')
ax_sec.plot([B_ft/2-0.075, B_ft/2-0.075], [t-0.075, t-0.225], color='#27ae60', linewidth=2.0, linestyle='--')

ax_sec.text(0, t/2, f"Thickness t = {t*100:.0f} cm\nBot: DB{bar_dia} @ {sp_X_bot} cm\nTop: DB{bar_dia} @ {sp_X_top} cm", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold')
ax_sec.set_xlim(-B_ft/2 - 0.3, B_ft/2 + 0.3)
ax_sec.set_ylim(-0.2, t + 0.7)
ax_sec.set_aspect('equal')
ax_sec.axis('off')

st.pyplot(fig_2d)

# --- 9. PRODUCTION ANALYSIS TABS ---
tab1, tab2, tab3 = st.tabs(["📝 ผลการประเมินสถิตศาสตร์เชิงลึก", "🎮 มิติและรูปร่าง 3D Solid Render", "📋 ตารางสรุปหน่วยแรงและการจัดเรียงตัวเลข"])

with tab1:
    if over_reinforced_error:
        st.error("🚨 [Over-reinforced Error] โมเมนต์ดัดสูงเกินกว่าความสามารถสูงสุดของหน้าตัดคอนกรีตจะรับได้ (พจน์สมการถอดรากติดลบ) กรุณาเพิ่มขนาดยังหน้าตัดตอม่อ หรือเพิ่มกำลังอัดคอนกรีต fc'")
    elif loop_break_by_guard:
        st.error("🚨 [Uplift / Self-Weight Paradox Triggered] ไม่สามารถประมวลผลให้ปลอดภัยได้ เนื่องจากเสาเข็มโอเวอร์โหลดทั้งจากน้ำหนักตัวเองหรือแรงถอนที่เกินลิมิต ปรับปรุงโดยเพิ่มจำนวนเข็ม")
    else:
        st.success("✅ การประมวลผลผ่านเกณฑ์มาตรฐานด้านกำลังและระยะตรวจสอบเชิงเส้นเรียบร้อย")

    if t >= 0.60:
        st.warning(f"⚠️ [Skin Reinforcement Note] เนื่องจากความหนาฐานราก t = {t*100:.0f} ซม. ($\ge 60$ ซม.) ตามมาตรฐานวิศวกรรมแนะนำให้พิจารณาเสริมเหล็กผิวข้าง (Side Face Reinforcement) เพื่อควบคุมการแตกร้าวเนื่องจากอุณหภูมิ")
        
    if any_congested:
        st.error("❌ [Spacing Alert] ตรวจพบระยะห่างเหล็กเสริมบางทิศทางต่ำกว่าเกณฑ์ควบคุมหน้างาน ($\le 1.5\phi$ หรือ 2.5 ซม.) เสี่ยงต่อการเกิดโพรงคอนกรีต (Honeycomb) กรุณาปรับเปลี่ยนเพิ่มขนาดหน้าตัดเหล็กเสริมเพื่อถ่างระยะแอด")

    c1, c2, c3 = st.columns(3)
    c1.metric("True C.G. Shift X", f"{cg_new_x*100:+.1f} ซม.")
    c2.metric("True C.G. Shift Y", f"{cg_new_y*100:+.1f} ซม.")
    c3.metric("ความหนาฐานรากควบคุม (t)", f"{t*100:.0f} ซม.")

    st.markdown("### 🧾 สรุปผลใบถอดแบบสั่งเหล็กเส้น")
    st.info(f"🔹 **เหล็กตะแกรงล่าง (ทิศ X):** DB{bar_dia} จำนวน {num_X_bot} เส้น @ {sp_X_bot:.0f} ซม. | **(ทิศ Y):** DB{bar_dia} จำนวน {num_Y_bot} เส้น @ {sp_Y_bot:.0f} ซม.")
    st.info(f"🔸 **เหล็กตะแกรงบน (ทิศ X):** DB{bar_dia} จำนวน {num_X_top} เส้น @ {sp_X_top:.0f} ซม. | **(ทิศ Y):** DB{bar_dia} จำนวน {num_Y_top} เส้น @ {sp_Y_top:.0f} ซม.")

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
            opacity=0.7, color='#2ecc71', name='Solid Base'
        )
    ])
    fig_3d.update_layout(scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)'))
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.markdown("### ⚔️ ตารางสรุปหน่วยแรงตามมาตรฐาน (Numerical Format Enabled)")
    
    df_shear = pd.DataFrame({
        "ประเภทการตรวจสอบ": ["Punching Shear (Combined Jc)", "Wide Beam Shear (Fractional Method)"],
        "หน่วยแรงเกิดขึ้นจริง": [v_u_stress, v_u_wb_stress],
        "กำลังที่ยอมให้ตามกฎหมาย": [v_c_allowable, v_c_wb_allowable]
    })
    
    st.dataframe(df_shear, column_config={
        "หน่วยแรงเกิดขึ้นจริง": st.column_config.NumberColumn("หน่วยแรงเกิดขึ้นจริง (v_u)", format="%.2f ksc"),
        "กำลังที่ยอมให้ตามกฎหมาย": st.column_config.NumberColumn("กำลังที่ยอมให้ตามกฎหมาย (phi*vc)", format="%.2f ksc")
    }, use_container_width=True, hide_index=True)
    
    st.markdown("### 📊 ตารางแสดงแรงปฏิกิริยารายต้น (Clean Numbers for Excel Export)")
    
    df_piles_report = pd.DataFrame({
        "เสาเข็ม": [f"ต้นที่ {i+1}" for i in range(n_piles)],
        "พิกัด X จริง": [p[0] for p in piles_actual],
        "พิกัด Y จริง": [p[1] for p in piles_actual],
        "แรงใช้งาน Service Load": pile_service_loads,
        "แรงประลัย Ultimate Load": pile_ultimate_loads
    })
    
    st.dataframe(df_piles_report, column_config={
        "พิกัด X จริง": st.column_config.NumberColumn("พิกัด X จริง", format="%.3f ม."),
        "พิกัด Y จริง": st.column_config.NumberColumn("พิกัด Y จริง", format="%.3f ม."),
        "แรงใช้งาน Service Load": st.column_config.NumberColumn("แรงใช้งาน Service Load", format="%.2f ตัน"),
        "แรงประลัย Ultimate Load": st.column_config.NumberColumn("แรงประลัย Ultimate Load", format="%.2f ตัน")
    }, use_container_width=True, hide_index=True)
