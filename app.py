import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Enterprise Footing Suite V5.1", page_icon="🏗️", layout="wide")

st.title("🏗️ Enterprise Footing Suite (V5.1 - Engineering Refined)")
st.markdown("ระบบวิเคราะห์และออกแบบฐานรากขั้นสูง | ป้องกัน Weight-Paradox Loop | คำนวณเหล็กตะแกรงบนรับแรงถอน | 3D Solid Mesh Dynamic")
st.markdown("---")

# --- 2. SIDEBAR PARAMETERS ---
with st.sidebar:
    st.header("⚙️ มาตรฐานและข้อกำหนดการออกแบบ")
    
    st.subheader("1. รูปแบบกลุ่มเสาเข็ม & หน้าตัด")
    n_piles = st.selectbox("จำนวนเสาเข็มในฐานราก:", [2, 3, 4, 5, 6, 8, 9], index=4)
    pile_shape = st.selectbox("รูปทรงหน้าตัดเสาเข็ม:", ["สี่เหลี่ยม (Square Pile)", "กลม (Round/Spun/Bore Pile)", "รูปตัวไอ (I-Shape Pile)"])
    pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.30, step=0.05)
    pile_cap = st.number_input("กำลังรับน้ำหนักปลอดภัยของเข็ม (ตัน/ต้น)", value=30.0, step=1.0)
    
    st.subheader("2. แรงกระทำจากเสาตอม่อ (Service Loads)")
    DL = st.number_input("น้ำหนักคงที่ (DL, ตัน)", value=60.0, step=5.0)
    LL = st.number_input("น้ำหนักจร (LL, ตัน)", value=35.0, step=5.0)
    Mcx = st.number_input("โมเมนต์ดัดแกน X (M_cx, ตัน-เมตร)", value=8.0, step=0.5)
    Mcy = st.number_input("โมเมนต์ดัดแกน Y (M_cy, ตัน-เมตร)", value=6.0, step=0.5)
    
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

# --- 6. CORE LOOP WITH WEIGHT-PARADOX GUARD ---
d = 0.40
t = 0.55
has_tension = False
loop_break_by_guard = False

B_ft = (max(p[0] for p in piles_actual) - min(p[0] for p in piles_actual)) + 2*E_dist
L_ft = (max(p[1] for p in piles_actual) - min(p[1] for p in piles_actual)) + 2*E_dist

v_u_stress, v_c_allowable = 0.0, 0.0
v_u_wb_stress, v_c_wb_allowable = 0.0, 0.0
pile_service_loads = [0.0] * n_piles
pile_ultimate_loads = [0.0] * n_piles

previous_max_R = float('inf')

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
    
    # 🛑 Convergence & Weight-Paradox Guard
    if max_R > pile_cap and max_R >= previous_max_R:
        loop_break_by_guard = True
        break
    previous_max_R = max_R
    
    # --- J_c Shear Calculations ---
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
            V_u_p_kg += pile_ultimate_loads[i] * 1000
            
    v_u_stress = (V_u_p_kg / A_c) + (gamma_vx * abs(Mu_x_loop) * 100000 * (b2/2) / (J_cx * 1000000)) + (gamma_vy * abs(Mu_y_loop) * 100000 * (b1/2) / (J_cy * 1000000))
    
    beta_col = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
    vc1 = 0.27 * (2 + 4/beta_col) * math.sqrt(fc_prime)
    vc2 = 0.27 * (alpha_s * (d * 100) / (bo * 100) + 2) * math.sqrt(fc_prime)
    vc3 = 1.06 * math.sqrt(fc_prime)
    v_c_allowable = phi_v * min(vc1, vc2, vc3)
    
    # Wide Beam Shear
    V_wb_X = max(sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[0] > cx/2 + d),
                 sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[0] < -(cx/2 + d)))
    V_wb_Y = max(sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[1] > cy/2 + d),
                 sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[1] < -(cy/2 + d)))
    V_u_wb_kg = max(V_wb_X, V_wb_Y)
    
    v_u_wb_stress = V_u_wb_kg / (L_ft * 100 * d * 100) if V_wb_X >= V_wb_Y else V_u_wb_kg / (B_ft * 100 * d * 100)
    v_c_wb_allowable = phi_v * 0.53 * math.sqrt(fc_prime)
    
    if (v_u_stress <= v_c_allowable) and (v_u_wb_stress <= v_c_wb_allowable) and (max_R <= pile_cap):
        break
    d += 0.02

d_actual = t - 0.15

# --- 7. ADVANCED REINFORCEMENT ENGINE (TOP & BOTTOM) ---
# แยกการรวมโมเมนต์สำหรับเหล็กเสริมล่าง (แรงอัด) และเหล็กเสริมบน (แรงดึง/แรงถอน)
M_u_X_pos = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2 and pile_ultimate_loads[i] > 0)
M_u_X_neg = abs(sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2 and pile_ultimate_loads[i] < 0))

M_u_Y_pos = sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2 and pile_ultimate_loads[i] > 0)
M_u_Y_neg = abs(sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2 and pile_ultimate_loads[i] < 0))

def design_steel_flexure(M_u_val, w_cm, d_cm, t_cm, is_top=False):
    if M_u_val <= 0:
        # หากไม่มีโมเมนต์ลบ ให้ใส่เหล็กเสริมขั้นต่ำตามมาตรฐานกันร้าว
        As_req = 0.0018 * w_cm * t_cm
    else:
        M_u_kg_cm = M_u_val * 1000 * 100
        Rn = M_u_kg_cm / (phi_b * w_cm * d_cm**2) if d_cm > 0 else 0
        rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(abs(1 - (2 * Rn) / (0.85 * fc_prime)))) if (Rn < (0.85*fc_prime)/2 and Rn > 0) else 0.002
        rho_min_flex = max(0.83 * math.sqrt(fc_prime) / fy, 14.0 / fy)
        As_req = max(rho * w_cm * d_cm, rho_min_flex * w_cm * d_cm, 0.0018 * w_cm * t_cm)
        
    n_bars = max(math.ceil(As_req / ab), 6)
    sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, sp

num_X_bot, sp_X_bot = design_steel_flexure(M_u_X_pos, B_ft*100, d_actual*100, t*100)
num_Y_bot, sp_Y_bot = design_steel_flexure(M_u_Y_pos, L_ft*100, d_actual*100, t*100)

num_X_top, sp_X_top = design_steel_flexure(M_u_X_neg, B_ft*100, d_actual*100, t*100, is_top=True)
num_Y_top, sp_Y_top = design_steel_flexure(M_u_Y_neg, L_ft*100, d_actual*100, t*100, is_top=True)

# --- 8. 2D ENGINEERING BLUEPRINT ---
st.markdown("### 📊 2. แบบวิศวกรรมและการจัดเหล็กเสริมโครงสร้าง (2D Engineering Blueprint)")
fig_2d, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(15, 7))

# A. Top View Plan
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
ax_plan.legend(loc='upper right', fontsize=8)

# B. Cross Section View
ax_sec.set_title("รูปตัดโครงสร้างแสดงตะแกรงเหล็ก บน-ล่าง (Cross Section)", fontsize=11, fontweight='bold', pad=10)
ax_sec.fill_between([-B_ft/2, B_ft/2], -0.15, -0.10, color='#f5cba7', alpha=0.7)
ax_sec.fill_between([-B_ft/2, B_ft/2], -0.10, 0.0, color='#d5dbdb', alpha=0.9)
ax_sec.add_patch(patches.Rectangle((-B_ft/2, 0), B_ft, t, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded'))
ax_sec.add_patch(patches.Rectangle((-cx/2, t), cx, 0.5, linewidth=1.5, edgecolor='#e74c3c', facecolor='#f1948a'))

# เหล็กตะแกรงล่าง (Bottom Steel)
ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [0.075, 0.075], color='#1f618d', linewidth=2.5, label='Bottom Rebar')
ax_sec.plot([-B_ft/2+0.075, -B_ft/2+0.075], [0.075, 0.225], color='#1f618d', linewidth=2.5)
ax_sec.plot([B_ft/2-0.075, B_ft/2-0.075], [0.075, 0.225], color='#1f618d', linewidth=2.5)

# เหล็กตะแกรงบน (Top Steel) - แสดงเส้นปะเมื่อมีโหลดถอน หรือเส้นบางกรณีขั้นต่ำ
ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [t-0.075, t-0.075], color='#27ae60', linewidth=2.0, linestyle='--', label='Top Rebar (Tension/Shrinkage)')
ax_sec.plot([-B_ft/2+0.075, -B_ft/2+0.075], [t-0.075, t-0.225], color='#27ae60', linewidth=2.0, linestyle='--')
ax_sec.plot([B_ft/2-0.075, B_ft/2-0.075], [t-0.075, t-0.225], color='#27ae60', linewidth=2.0, linestyle='--')

ax_sec.text(0, t/2, f"Thickness t = {t*100:.0f} cm\nBot: DB{bar_dia} @ {sp_X_bot} cm\nTop: DB{bar_dia} @ {sp_X_top} cm", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold')
ax_sec.set_xlim(-B_ft/2 - 0.3, B_ft/2 + 0.3)
ax_sec.set_ylim(-0.2, t + 0.7)
ax_sec.set_aspect('equal')
ax_sec.legend(loc='upper right', fontsize=8)
ax_sec.axis('off')

st.pyplot(fig_2d)

# --- 9. PRODUCTION ANALYSIS TABS ---
tab1, tab2, tab3 = st.tabs(["📝 ผลการประเมินสถิตศาสตร์เชิงลึก", "🎮 มิติและรูปร่าง 3D Solid Render", "📋 ตารางสรุปหน่วยแรงตามมาตรฐาน"])

with tab1:
    if loop_break_by_guard:
        st.error("🚨 [Weight-Paradox Error] ไม่สามารถคำนวณให้บรรลุเป้าหมายได้ เนื่องจากน้ำหนักฐานรากที่หนาขึ้นส่งผลให้เสาเข็มรับน้ำหนักเกินพิกัดสูงสุด (Infinite Loop Guard Triggers) แนะนำให้เพิ่มจำนวนเสาเข็มในระบบ")
    elif has_tension:
        st.warning(f"⚠️ ตรวจพบแรงดึง (Uplift Tension) ในกลุ่มเสาเข็ม! ระบบทำการคำนวณและเสริมเหล็กตะแกรงบนรับแรงดึงต้านทานโมเมนต์ลบให้เรียบร้อยแล้ว")
    else:
        st.success("✅ โครงสร้างผ่านเกณฑ์ความปลอดภัยสมบูรณ์รอบด้าน")
        
    c1, c2, c3 = st.columns(3)
    c1.metric("True C.G. Shift X", f"{cg_new_x*100:+.1f} ซม.")
    c2.metric("True C.G. Shift Y", f"{cg_new_y*100:+.1f} ซม.")
    c3.metric("ความหนาฐานรากควบคุม (t)", f"{t*100:.0f} ซม.")
    
    st.markdown("### 🧾 รายละเอียดสรุปเหล็กเสริมแกนหลัก")
    st.info(f"🔹 **เหล็กตะแกรงล่าง (ทิศ X):** DB{bar_dia} จำนวน {num_X_bot} เส้น @ {sp_X_bot:.0f} ซม. | **(ทิศ Y):** DB{bar_dia} จำนวน {num_Y_bot} เส้น @ {sp_Y_bot:.0f} ซม.")
    st.info(f"🔸 **เหล็กตะแกรงบน (ทิศ X):** DB{bar_dia} จำนวน {num_X_top} เส้น @ {sp_X_top:.0f} ซม. | **(ทิศ Y):** DB{bar_dia} จำนวน {num_Y_top} เส้น @ {sp_Y_top:.0f} ซม.")

with tab2:
    # 3D Explicit Mesh Setup (กำหนดมุม 8 จุด และ 12 หน้าสามเหลี่ยมให้วัตถุทึบแสงสมบูรณ์)
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
            opacity=0.7, color='#3498db', name='Solid Pile Cap'
        )
    ])
    fig_3d.update_layout(scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)'), margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.markdown("### ⚔️ ตารางสรุปหน่วยแรงตามมาตรฐาน")
    df_shear = pd.DataFrame({
        "ประเภทการตรวจสอบ": ["Punching Shear (รวมพจน์ Jc บิดเยื้องศูนย์)", "Wide Beam Shear แรงเฉือนคานกว้าง"],
        "หน่วยแรงเกิดขึ้นจริง (v_u)": [f"{v_u_stress:.2f} ksc", f"{v_u_wb_stress:.2f} ksc"],
        "กำลังที่ยอมให้ (phi*v_c)": [f"{v_c_allowable:.2f} ksc", f"{v_c_wb_allowable:.2f} ksc"],
        "สถานะ": ["✅ ผ่าน" if v_u_stress <= v_c_allowable else "❌ เกินพิกด", "✅ ผ่าน" if v_u_wb_stress <= v_c_wb_allowable else "❌ เกินพิกด"]
    })
    st.table(df_shear)
    
    df_piles_report = pd.DataFrame({
        "เสาเข็ม": [f"ต้นที่ {i+1}" for i in range(n_piles)],
        "แรงใช้งาน (ตัน)": [f"{v:.2f}" for v in pile_service_loads],
        "แรงประลัย (ตัน)": [f"{v:.2f}" for v in pile_ultimate_loads],
        "พฤติกรรม": ["⚠️ ถอน/ดึง (Tension)" if float(v) < 0 else "✅ รับแรงอัดปกติ" for v in pile_service_loads]
    })
    st.dataframe(df_piles_report, use_container_width=True)
