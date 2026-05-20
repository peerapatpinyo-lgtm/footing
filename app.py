import streamlit as st
import math
import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import plotly.graph_objects as go

# =========================================================================
# [5] SYSTEM STABILITY & FONT MANAGEMENT
# =========================================================================
st.set_page_config(page_title="Enterprise Footing Suite V7.0", page_icon="📐", layout="wide")

@st.cache_resource(show_spinner=False)
def initialize_thai_font_system():
    """จัดการฟอนต์ภาษาไทยแบบ Local First ป้องกันระบบค้างเมื่อ Cloud Deployment ไม่มีอินเทอร์เน็ต"""
    font_dir = "fonts"
    font_name = "Kanit-Regular.ttf"
    font_path = os.path.join(font_dir, font_name)
    
    if not os.path.exists(font_dir):
        os.makedirs(font_dir, exist_ok=True)
        
    if not os.path.exists(font_path):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Regular.ttf"
            response = requests.get(font_url, timeout=5)
            if response.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(response.content)
        except Exception:
            pass
            
    if os.path.exists(font_path):
        try:
            fm.fontManager.addfont(font_path)
            registered_font = fm.FontProperties(fname=font_path).get_name()
            plt.rcParams['font.family'] = registered_font
            plt.rcParams['axes.unicode_minus'] = False  
            return registered_font
        except Exception:
            pass
    return "sans-serif"

current_thai_font = initialize_thai_font_system()

st.title("📐 Enterprise Footing Suite (V7.0 - Production Architecture)")
st.markdown("### ระบบวิเคราะห์และออกแบบฐานรากขั้นสูงบนมาตรฐานควบคุม วสท. / ACI และกฎบัตรเสาเข็มหนีศูนย์จริง")
st.markdown("---")

# =========================================================================
# HELPERS FOR GEOMETRIC VALIDATION
# =========================================================================
def point_to_segment_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    return math.sqrt((px - (x1 + t * dx))**2 + (py - (y1 + t * dy))**2)

# =========================================================================
# SIDEBAR CONTROL INTERFACE & INPUT DATA OPTIMIZATION
# =========================================================================
with st.sidebar:
    st.header("🏗️ ข้อกำหนดสถิตศาสตร์และวัสดุ")
    
    footing_shape_type = st.selectbox(
        "รูปทรงเรขาคณิตของฐานราก:", 
        ["ฐานรากสามเหลี่ยมตัดมุม (Truncated Triangular)", "ฐานรากสี่เหลี่ยม (Rectangular Footing)"],
        index=1
    )
    
    st.subheader("1. คุณสมบัติเสาเข็มและการรับน้ำหนัก")
    if footing_shape_type == "ฐานรากสามเหลี่ยมตัดมุม (Truncated Triangular)":
        st.info("ℹ️ รูปทรงสามเหลี่ยมตัดมุม บังคับใช้กลุ่มเสาเข็ม 3 ต้น")
        n_piles = 3
    else:
        n_piles = st.selectbox("จำนวนเสาเข็มในกลุ่ม:", [2, 3, 4, 5, 6, 8, 9], index=2)
        
    pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.30, min_value=0.15, step=0.05)
    pile_cap = st.number_input("กำลังรับแรงอัดปลอดภัยเสาเข็ม (ตัน/ต้น)", value=30.0, min_value=1.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนปลอดภัยเสาเข็ม (ตัน/ต้น)", value=10.0, min_value=0.0)
    
    st.subheader("2. น้ำหนักบรรทุกใช้งาน (Service Loads) & ดินถม")
    DL = st.number_input("น้ำหนักคงที่ปลอดภัย (Dead Load, ตัน)", value=55.0, min_value=0.0)
    LL = st.number_input("น้ำหนักจรปลอดภัย (Live Load, ตัน)", value=30.0, min_value=0.0)
    Mcx = st.number_input("โมเมนต์ใช้งานแกน X (M_cx, ตัน-เมตร)", value=10.0)
    Mcy = st.number_input("โมเมนต์ใช้งานแกน Y (M_cy, ตัน-เมตร)", value=8.0)
    
    soil_depth = st.number_input("ความลึกของดินถมเหนือฐานราก (m)", value=1.0, min_value=0.0, step=0.1)
    soil_density = st.number_input("ความหนาแน่นของดิน (Density, t/m³)", value=1.8, min_value=1.0, step=0.1)
    
    st.subheader("3. หน้าตัดตอม่อและพิกัดกำลังวัสดุ")
    cx = st.number_input("ความกว้างเสาตอม่อแกน X (เมตร)", value=0.35, min_value=0.15, step=0.05)
    cy = st.number_input("ความกว้างเสาตอม่อแกน Y (เมตร)", value=0.35, min_value=0.15, step=0.05)
    col_position = st.selectbox("ตำแหน่งเชิงพิกัดของตอม่อ:", ["เสาภายใน (Interior)", "เสาขอบ (Edge)", "เสามุม (Corner)"])
    fc_prime = st.number_input("กำลังอัดประลัยคอนกรีต fc' (ksc)", value=280, min_value=150, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริมหลัก fy (ksc)", [4000, 5000], index=0)
    
    bar_dia = st.selectbox("ขนาดเส้นผ่านศูนย์กลางเหล็กแกนหลัก (มม.)", [12, 16, 20, 25, 28, 32], index=2)
    
    st.subheader("4. รายละเอียดระยะหุ้มและระยะฝัง")
    pile_embed_cm = st.number_input("ระยะเสาเข็มฝังในฐานราก (Pile Embedment Depth, cm)", value=5.0, min_value=0.0, step=1.0)
    concrete_cover_cm = st.number_input("ระยะหุ้มคอนกรีตสุทธิ (Concrete Covering, cm)", value=7.5, min_value=3.0, step=0.5)

    st.markdown("---")
    st.subheader("🎛️ 5. ระบบวิเคราะห์ความหนาคอนกรีต")
    thickness_mode = st.radio("ระเบียบวิธีหาความหนา:", ["คำนวณอัตโนมัติ (Auto-Optimize)", "กำหนดความหนาเอง (Manual Override)"])
    
    manual_t = 0.65
    if thickness_mode == "กำหนดความหนาเอง (Manual Override)":
        manual_t_cm = st.number_input("ระบุความหนาฐานราก t (ซม.)", min_value=30, max_value=300, value=65, step=5)
        manual_t = manual_t_cm / 100

# ข้อกำหนดตัวคูณกำลังตามมาตรฐานสากล
phi_shear = 0.75  
phi_flexure = 0.90  
ab_area = (math.pi * (bar_dia / 10) ** 2) / 4  # cm^2

# =========================================================================
# INITIAL IDEAL PILE PATTERN GENERATION
# =========================================================================
S_dist = 3.0 * pile_size
E_dist = max(pile_size, 0.35)

if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
    elif n_piles == 3: piles_ideal = [(-S_dist, 0), (0, 0), (S_dist, 0)]
    elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
    elif n_piles == 5: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2), (0, 0)]
    elif n_piles == 6: piles_ideal = [(-S_dist/2, -S_dist), (S_dist/2, -S_dist), (-S_dist/2, 0), (S_dist/2, 0), (-S_dist/2, S_dist), (S_dist/2, S_dist)]
    elif n_piles == 8: piles_ideal = [(-1.5*S_dist, -S_dist/2), (-0.5*S_dist, -S_dist/2), (0.5*S_dist, -S_dist/2), (1.5*S_dist, -S_dist/2), (-1.5*S_dist, S_dist/2), (-0.5*S_dist, S_dist/2), (0.5*S_dist, S_dist/2), (1.5*S_dist, S_dist/2)]
    else: piles_ideal = [(x, y) for x in [-S_dist, 0, S_dist] for y in [-S_dist, 0, S_dist]]
else:
    piles_ideal = [(0, S_dist / math.sqrt(3)), (-S_dist / 2, -S_dist / (2 * math.sqrt(3))), (S_dist / 2, -S_dist / (2 * math.sqrt(3)))]

# =========================================================================
# [2.1] FIELD AS-BUILT DEVIATION MANAGEMENT (st.data_editor)
# =========================================================================
st.markdown("### 📍 1. ข้อมูลสำรวจเสาเข็มหนีศูนย์หน้างานจริง (As-Built Field Survey Analysis)")
st.info("💡 **UX/UI Tip:** คุณสามารถคลิกเลือก คัดลอกพิกัดเบี่ยงเบน หรือ Copy-Paste ค่า $\Delta X$ และ $\Delta Y$ จากไฟล์ Excel ลงในตารางได้โดยตรง")

df_initial = pd.DataFrame({
    'Pile Name': [f"P{i+1}" for i in range(n_piles)],
    'Design X (m)': [round(p[0], 3) for p in piles_ideal],
    'Design Y (m)': [round(p[1], 3) for p in piles_ideal],
    'ΔX (m) - Field': [0.00] * n_piles,
    'ΔY (m) - Field': [0.00] * n_piles
})

edited_df = st.data_editor(
    df_initial,
    disabled=['Pile Name', 'Design X (m)', 'Design Y (m)'],
    hide_index=True,
    use_container_width=True
)

# ดึงค่าพิกัดจริงที่อัปเดตแล้วจากตารางไปคำนวณสถิตศาสตร์ทางวิศวกรรม
piles_actual = []
for _, row in edited_df.iterrows():
    p_act_x = row['Design X (m)'] + row['ΔX (m) - Field']
    p_act_y = row['Design Y (m)'] + row['ΔY (m) - Field']
    piles_actual.append((p_act_x, p_act_y))

cg_actual_x = sum(p[0] for p in piles_actual) / n_piles
cg_actual_y = sum(p[1] for p in piles_actual) / n_piles

ecc_x = 0.0 - cg_actual_x
ecc_y = 0.0 - cg_actual_y

piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group = sum(p[0]**2 for p in piles_relative)  
I_xx_group = sum(p[1]**2 for p in piles_relative)  

# =========================================================================
# [1.0 & 1.1] LOAD COMBINATIONS & SOIL OVERBURDEN PRE-CALCULATIONS
# =========================================================================
P_service = DL + LL
P_ultimate = (1.2 * DL) + (1.6 * LL)

# คำนวณ Load Factor เพื่อแปลงโมเมนต์ใช้งานให้เป็นโมเมนต์ประลัยอย่างถูกต้อง
average_load_factor = P_ultimate / P_service if P_service > 0 else 1.45
Mu_cx = Mcx * average_load_factor
Mu_cy = Mcy * average_load_factor

# -------------------------------------------------------------------------
# DEFINING CONCRETE GEOMETRY BOUNDARIES & FIXING SHAPE VARIABLE SCOPES
# -------------------------------------------------------------------------
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    B_ft = (max(p[0] for p in piles_ideal) - min(p[0] for p in piles_ideal)) + 2*E_dist
    L_ft = (max(p[1] for p in piles_ideal) - min(p[1] for p in piles_ideal)) + 2*E_dist
    footing_area = B_ft * L_ft
    x_max_edge, x_min_edge = B_ft / 2, -B_ft / 2
    y_max_edge, y_min_edge = L_ft / 2, -L_ft / 2
    concrete_vertices = [(x_min_edge, y_min_edge), (x_max_edge, y_min_edge), (x_max_edge, y_max_edge), (x_min_edge, y_max_edge)]
else:
    y_p1 = S_dist / math.sqrt(3)
    y_p23 = -S_dist / (2 * math.sqrt(3))
    v1_tri = (-E_dist / math.sqrt(3), y_p1 + E_dist) 
    v2_tri = (E_dist / math.sqrt(3), y_p1 + E_dist)  
    v3_tri = (S_dist / 2 + 2 * E_dist / math.sqrt(3), y_p23) 
    v4_tri = (S_dist / 2 + E_dist / math.sqrt(3), y_p23 - E_dist) 
    v5_tri = (-S_dist / 2 - E_dist / math.sqrt(3), y_p23 - E_dist) 
    v6_tri = (-S_dist / 2 - 2 * E_dist / math.sqrt(3), y_p23) 
    concrete_vertices = [v1_tri, v2_tri, v3_tri, v4_tri, v5_tri, v6_tri]
    footing_area = (math.sqrt(3)/4)*(S_dist**2) + (3*S_dist*E_dist) + (2*math.sqrt(3)*(E_dist**2))
    
    # [FIXED LOGIC] คำนวณขอบเขตสูงสุดเพื่อส่งค่าให้ระบบคำนวณเหล็กกันร้าว (Shrinkage Rebar) ไม่ให้เกิด NameError
    B_ft = max(v[0] for v in concrete_vertices) - min(v[0] for v in concrete_vertices)
    L_ft = max(v[1] for v in concrete_vertices) - min(v[1] for v in concrete_vertices)

# คำนวณน้ำหนักดินถมสุทธิ W_soil
col_area = cx * cy
W_soil = max(0.0, footing_area - col_area) * soil_depth * soil_density

# ตรวจสอบระยะขอบเสาเข็มขั้นต่ำสากล
net_min_edge_dist = float('inf')
segments = [(concrete_vertices[i], concrete_vertices[(i+1)%len(concrete_vertices)]) for i in range(len(concrete_vertices))]
for px, py in piles_actual:
    p_radius = pile_size / 2
    current_min = min(point_to_segment_dist(px, py, seg[0][0], seg[0][1], seg[1][0], seg[1][1]) - p_radius for seg in segments)
    if current_min < net_min_edge_dist: net_min_edge_dist = current_min

if net_min_edge_dist < 0.10:
    st.error(f"🚨 **[As-Built Edge Distance Alert]** ตรวจพบเสาเข็มมีระยะห่างผิวสัมผัสสุทธิถึงขอบคอนกรีตเพียง {net_min_edge_dist*100:.1f} ซม. ซึ่งน้อยกว่าเกณฑ์จำกัดความปลอดภัยจำเพาะ (10 ซม.)!")

def get_triangular_width_at_y(target_y):
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)": return B_ft
    y_top_bound, y_bot_bound = S_dist / math.sqrt(3) + E_dist, -S_dist / (2 * math.sqrt(3)) - E_dist
    if target_y > y_top_bound or target_y < y_bot_bound: return 0.0
    x_inter = (S_dist / math.sqrt(3) + 2 * E_dist - target_y) / math.sqrt(3) if target_y >= -S_dist / (2 * math.sqrt(3)) else (2 / math.sqrt(3)) * (S_dist / math.sqrt(3) + E_dist + 0.5 * target_y)
    return 2 * max(0.0, x_inter)

# =========================================================================
# ENGINEERING CALCULATIONS ROUTINES (SHEAR EVALUATION)
# =========================================================================
def execute_shear_evaluation_routine(eval_d, eval_t):
    w_u_footing_weight = 1.2 * (footing_area * eval_t * 2.4)
    w_u_soil_weight = 1.2 * W_soil 
    
    P_total_factored = P_ultimate + w_u_footing_weight + w_u_soil_weight
    Mu_x_total = Mu_cx + (P_total_factored * (-ecc_y))
    Mu_y_total = Mu_cy + (P_total_factored * (-ecc_x))
    
    p_ult_reactions = []
    for prx, pry in piles_relative:
        R_u = (P_total_factored / n_piles) + \
              (Mu_y_total * prx / I_yy_group if I_yy_group > 0 else 0) + \
              (Mu_x_total * pry / I_xx_group if I_xx_group > 0 else 0)
        p_ult_reactions.append(R_u)
        
    # A. PUNCHING SHEAR ANALYSIS
    b1_box, b2_box = cx + eval_d, cy + eval_d
    b_0 = 2 * (b1_box + b2_box)
    A_punching_cm2 = b_0 * eval_d * 10000
    
    V_u_punching_kg = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_actual) if abs(px) > (cx/2 + eval_d/2) or abs(py) > (cy/2 + eval_d/2))
    v_u_punching_stress = V_u_punching_kg / A_punching_cm2 if A_punching_cm2 > 0 else 0.0
    beta_ratio = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
    v_c_allow_punching = phi_shear * min(0.27*(2 + 4/beta_ratio)*math.sqrt(fc_prime), 0.27*(alpha_s*(eval_d*100)/(b_0*100) + 2)*math.sqrt(fc_prime), 1.06*math.sqrt(fc_prime))
    
    # B. WIDE BEAM SHEAR WITH VARIABLE WIDTH
    cut_y_pos = cy/2 + eval_d
    V_u_wb = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_actual) if py >= cut_y_pos)
    bw_y = get_triangular_width_at_y(cut_y_pos) * 100
    v_u_wb_max = V_u_wb / (bw_y * eval_d * 100) if bw_y > 0 else 0
    v_c_allow_wb = phi_shear * 0.53 * math.sqrt(fc_prime)
    
    return (v_u_punching_stress <= v_c_allow_punching) and (v_u_wb_max <= v_c_allow_wb), v_u_punching_stress, v_c_allow_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions

# [1.3] ปรับปรุงความลึกประสิทธิผล d ตามสมการวิศวกรรมควบคุมเชิงลึก
def compute_effective_depth(t_total):
    return t_total - (concrete_cover_cm / 100) - (pile_embed_cm / 100) - ((bar_dia / 1000) / 2)

if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)":
    d_opt = 0.30
    step_safe = False
    p_ult_out = [0.0] * n_piles
    while d_opt < 3.0:
        t_opt = d_opt + (concrete_cover_cm/100) + (pile_embed_cm/100) + ((bar_dia/1000)/2)
        step_safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(d_opt, t_opt)
        if step_safe: break
        d_opt += 0.02
    d_actual = d_opt
    t_actual = math.ceil(t_opt * 20) / 20
else:
    t_actual = manual_t
    d_actual = compute_effective_depth(t_actual)
    step_safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(d_actual, t_actual)

# คำนวณ Service Reaction สำหรับตรวจสอบความปลอดภัยฐานรากและเข็มใช้งาน
w_s_footing = footing_area * t_actual * 2.4
P_service_total = P_service + w_s_footing + W_soil
Ms_x_total = Mcx + (P_service_total * (-ecc_y))
Ms_y_total = Mcy + (P_service_total * (-ecc_x))

pile_service_reactions = []
for prx, pry in piles_relative:
    R_s = (P_service_total / n_piles) + \
          (Ms_y_total * prx / I_yy_group if I_yy_group > 0 else 0) + \
          (Ms_x_total * pry / I_xx_group if I_xx_group > 0 else 0)
    pile_service_reactions.append(R_s)

# =========================================================================
# [1.2] BI-DIRECTIONAL FLEXURAL DESIGN
# =========================================================================
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    Mu_x_face = max(abs(sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2)),
                    abs(sum(p_ult_out[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2)))
    w_flex_x = B_ft * 100 
    
    Mu_y_face = max(abs(sum(p_ult_out[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2)),
                    abs(sum(p_ult_out[i] * (-cx/2 - p[0]) for i, p in enumerate(piles_actual) if p[0] < -cx/2)))
    w_flex_y = L_ft * 100 
else:
    Mu_x_face = max(abs(sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2)),
                    abs(sum(p_ult_out[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2)))
    w_flex_x = get_triangular_width_at_y(cy/2) * 100
    
    Mu_y_face = 0.0
    w_flex_y = get_triangular_width_at_y(-cy/2) * 100

def design_rebar_by_axis(Mu_ton_m, width_cm, d_cm, t_cm):
    width_cm = max(width_cm, 30.0)
    As_min = 0.0018 * width_cm * t_cm
    if Mu_ton_m <= 0:
        n_bars = max(math.ceil(As_min / ab_area), 4)
        return n_bars, math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15, False, As_min
        
    Mu_kg_cm = Mu_ton_m * 1000 * 100
    Rn = Mu_kg_cm / (phi_flexure * width_cm * d_cm**2)
    beta_1 = 0.85 if fc_prime <= 280 else max(0.65, 0.85 - 0.05 * (fc_prime - 280) / 70)
    rho_max = 0.75 * (0.85 * beta_1 * (fc_prime / fy) * (6120 / (6120 + fy)))
    
    if Rn > (rho_max * fy * (1 - 0.59 * rho_max * fy / fc_prime)):
        return 0, 0, True, 0.0
        
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * fc_prime)))
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 4)
    spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, 45.0), False, As_req

n_main_bars_x, sp_main_x, crash_fx, As_req_x = design_rebar_by_axis(Mu_x_face, w_flex_x, d_actual*100, t_actual*100)
n_main_bars_y, sp_main_y, crash_fy, As_req_y = design_rebar_by_axis(Mu_y_face, w_flex_y, (d_actual - bar_dia/1000)*100, t_actual*100)

is_structure_crashed = crash_fx or crash_fy or (not step_safe)
is_pile_overstressed = any(r > pile_cap for r in pile_service_reactions) or any(r < -pile_tension_cap for r in pile_service_reactions)

# [3.1] เหล็กเสริมต้านการยืดหดตัว (Shrinkage Rebar - ปลอดภัยไร้ NameError 100%)
As_shrinkage_top = 0.0
if t_actual >= 0.50:
    As_shrinkage_top = 0.0018 * (max(B_ft, L_ft) * 100) * (t_actual * 100)
    n_shrinkage_bars = max(math.ceil(As_shrinkage_top / ((math.pi * (12 / 10) ** 2) / 4)), 4)

# =========================================================================
# [2.2] ENGINEERING ADVISORY SYSTEM
# =========================================================================
st.markdown("### 🔍 2. รายงานสถานะสุขภาพโครงสร้างและคำแนะนำเชิงวิศวกรรม")

col_adv1, col_adv2 = st.columns(2)
with col_adv1:
    if not step_safe:
        st.error("🚨 **สถานะแรงเฉือน:** ไม่ผ่านเกณฑ์จำกัดกำลัง (Shear Failure Detector)")
        st.warning("💡 **คำแนะนำเชิงวิศวกรรม:**\n1. ระบบตรวจพบแรงเฉือนทะลุ (Punching Shear) หรือ แรงเฉือนคานกว้าง (Wide Beam Shear) เกินค่ากำหนด ให้ทำการ **เพิ่มความหนาฐานราก (t)** ในแถบควบคุม\n2. หรือทำการเพิ่มเกรดชั้นคุณภาพคอนกรีต ($fc'$) เพื่อขยายขีดความสามารถการต้านทานแรงเฉือนคอนกรีต")
    else:
        st.success("✅ **สถานะแรงเฉือน:** ผ่านเกณฑ์ความปลอดภัยตามมาตรฐาน วสท./ACI ทั้งหมด")

with col_adv2:
    if is_pile_overstressed:
        st.error("🚨 **สถานะเสาเข็ม:** ตรวจพบการรับแรงเกินพิกัดความปลอดภัย (Pile Overstressed)")
        st.warning("💡 **คำแนะนำเชิงวิศวกรรม:**\n1. เสาเข็มบางต้นรับน้ำหนักเกินกำลังเสาเข็มปลอดภัยอันเนื่องมาจากเอฟเฟกต์ของการเยื้องศูนย์จริง (As-Built Deviation) แนะนำให้ **ขยายขนาดระยะห่างเสาเข็ม (S)** หรือทำการ **เพิ่มพูนเข็มแซม** ในตําแหน่งที่เยื้องศูนย์วิกฤต\n2. หรือทำการขยายมิติขอบฐานรากเพื่อกระจายโมเมนต์ภายนอก")
    else:
        st.success("✅ **สถานะเสาเข็ม:** แรงปฏิกิริยารายต้นเสาเข็มผ่านเกณฑ์พิกัดต้านทานใช้งาน")

# =========================================================================
# [4] ADVANCED 2D VISUALIZATIONS (UPDATED: VISUAL EMBEDDED DEVIATIONS CORRELATION)
# =========================================================================
if not is_structure_crashed:
    st.markdown("### 📊 3. แบบวิศวกรรมสถาปัตยกรรมฐานราก (2D Engineering Blueprint)")
    fig, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(14, 6))
    
    # แปลน (Top View)
    footing_shape_patch = patches.Polygon(concrete_vertices, closed=True, linewidth=2.5, edgecolor='#2c3e50', facecolor='#eaeded', zorder=1)
    ax_plan.add_patch(footing_shape_patch)
    
    x_coords = [v[0] for v in concrete_vertices]
    y_coords = [v[1] for v in concrete_vertices]
    ax_plan.set_xlim(min(x_coords) - 0.4, max(x_coords) + 0.4)
    ax_plan.set_ylim(min(y_coords) - 0.4, max(y_coords) + 0.4)
    
    ax_plan.add_patch(patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.8, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4))
    ax_plan.scatter(0, 0, color='red', marker='+', s=200, linewidths=3, label='Column Center (0,0)', zorder=6)
    ax_plan.scatter(cg_actual_x, cg_actual_y, color='#f39c12', marker='X', s=130, label='True C.G. of Piles', zorder=5)
    ax_plan.plot([0, cg_actual_x], [0, cg_actual_y], color='#8e44ad', linestyle='--', linewidth=2, label='Global Eccentricity', zorder=4)
    
    # วาดตำแหน่งเสาเข็มเปรียบเทียบ (ตามตารางที่ 1 เพื่อเห็นภาพชัดเจน)
    for idx, (px, py) in enumerate(piles_actual):
        ix, iy = piles_ideal[idx]
        
        # 1. วาดเสาเข็มตามแบบดั้งเดิม (Design Ideal) -> เส้นปรุ สีเทาจาง
        pile_ideal_draw = patches.Circle((ix, iy), pile_size/2, linewidth=1.2, edgecolor='#bdc3c7', facecolor='none', linestyle='--', alpha=0.7, zorder=2)
        ax_plan.add_patch(pile_ideal_draw)
        
        # 2. วาดเสาเข็มที่ขยับหนีศูนย์จริง (As-Built Actual) -> สีทึบ
        pile_draw = patches.Circle((px, py), pile_size/2, linewidth=1.5, edgecolor='#34495e', facecolor='#7f8c8d', alpha=0.8, zorder=3)
        ax_plan.add_patch(pile_draw)
        ax_plan.text(px, py, f"P{idx+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold', zorder=4)
        
        # 3. ลากเส้นแสดงระยะเบี่ยงเบนจากตาราง 1 (Deviation Vector) หากมีค่าหนีศูนย์จริง
        if ix != px or iy != py:
            ax_plan.plot([ix, px], [iy, py], color='#e74c3c', linestyle='-', linewidth=1.8, zorder=4)
            ax_plan.scatter(ix, iy, color='#e74c3c', marker='.', s=40, zorder=4)
            
    # เพิ่มรายการสัญลักษณ์ (Legend Customization) ให้สัมพันธ์กับตารางสำรวจ
    ax_plan.plot([], [], color='#bdc3c7', linestyle='--', linewidth=1.5, label='Design Pile Position (ตามแผน)')
    ax_plan.plot([], [], color='#34495e', marker='o', markersize=8, markerfacecolor='#7f8c8d', linestyle='none', label='As-Built Pile Position (หน้างานจริง)')
    ax_plan.plot([], [], color='#e74c3c', linestyle='-', linewidth=1.8, label='Field Deviation Vector (ระยะหนีศูนย์)')
        
    ax_plan.set_aspect('equal')
    ax_plan.grid(True, linestyle=':', alpha=0.6)
    ax_plan.legend(loc="upper right", fontsize=8)
    ax_plan.set_title("แปลนแสดงตำแหน่งฐานรากและเสาเข็มเยื้องศูนย์จริง (Top View)", fontsize=11, fontweight='bold')
    
    # รูปตัด (Section View)
    sec_w = max(x_coords) - min(x_coords)
    ax_sec.add_patch(patches.Rectangle((-sec_w/2, 0), sec_w, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#f2f4f4', zorder=2))
    
    embed_m = pile_embed_cm / 100
    for idx, (px, py) in enumerate(piles_actual):
        ix, iy = piles_ideal[idx]
        if abs(py) < L_ft/2: 
            # เสาเข็มตำแหน่งตามทฤษฎีในรูปตัด (เงาเส้นปรุ)
            ax_sec.add_patch(patches.Rectangle((ix - pile_size/2, -0.4), pile_size, 0.4 + embed_m, linewidth=1.2, edgecolor='#bdc3c7', facecolor='none', linestyle='--', alpha=0.5, zorder=1))
            # เสาเข็มตามตำแหน่งจริงเยื้องศูนย์หน้างาน (รูปตัดคอนกรีตทึบ)
            ax_sec.add_patch(patches.Rectangle((px - pile_size/2, -0.4), pile_size, 0.4 + embed_m, linewidth=1.8, edgecolor='#34495e', facecolor='#95a5a6', zorder=1))
    
    cov_m = concrete_cover_cm / 100
    rb_rad_m = (bar_dia / 1000) / 2
    ax_sec.plot([-sec_w/2 + cov_m, sec_w/2 - cov_m], [cov_m + embed_m, cov_m + embed_m], color='#1f618d', linewidth=3.5, label='Main Rebar X', zorder=3)
    
    dots_count = max(int(n_main_bars_y), 4)
    for i in range(dots_count):
        dot_x = (-sec_w/2 + cov_m) + i * ((sec_w - 2*cov_m) / max(1, dots_count - 1))
        ax_sec.add_patch(patches.Circle((dot_x, cov_m + embed_m + rb_rad_m*2), rb_rad_m, color='#c0392b', zorder=4))
        
    if t_actual >= 0.50:
        ax_sec.plot([-sec_w/2 + cov_m, sec_w/2 - cov_m], [t_actual - cov_m, t_actual - cov_m], color='#27ae60', linestyle='-.', linewidth=2.0, label='Top Shrinkage Rebar')
    
    blueprint_text = f"ความหนาฐานราก t = {t_actual*100:.0f} cm\n" \
                     f"Effective Depth d = {d_actual*100:.1f} cm\n" \
                     f"ระยะเข็มฝังในฐาน = {pile_embed_cm:.1f} cm\n\n" \
                     f"เหล็กเสริมหลักแกน X: DB{bar_dia} @ {sp_main_x:.0f} cm ({n_main_bars_x} เส้น)\n" \
                     f"เหล็กเสริมกระจายแกน Y: DB{bar_dia} @ {sp_main_y:.0f} cm ({n_main_bars_y} เส้น)"
                     
    if t_actual >= 0.50:
        blueprint_text += f"\nเหล็กกันร้าวผิวบน: DB12 (ACI Compliant Min)"
        
    ax_sec.text(0, t_actual + 0.15, blueprint_text, ha='center', va='bottom', color='#2c3e50', fontsize=9, fontweight='bold', bbox=dict(boxstyle='round,pad=0.5', facecolor='#fcf3cf', alpha=0.5))
    
    ax_sec.set_xlim(-sec_w/2 - 0.3, sec_w/2 + 0.3)
    ax_sec.set_ylim(-0.5, t_actual + 0.6)
    ax_sec.set_aspect('equal')
    ax_sec.axis('off')
    ax_sec.set_title("รูปตัดแสดงโครงสร้างคอนกรีตและการจัดเหล็กตะกร้าคู่ทิศทาง (Section View)", fontsize=11, fontweight='bold')
    st.pyplot(fig)

# =========================================================================
# INTERACTIVE MULTI-TAB MATRIX OUTPUTS
# =========================================================================
tab1, tab2, tab3 = st.tabs(["📝 สรุปพิกัดความปลอดภัยสถิตศาสตร์", "🌐 แบบจำลองพิกัด 3D Solid Model Mesh", "📋 รายการคำนวณและหน่วยแรงเชิงเลข"])

with tab1:
    st.subheader("📋 บทสรุปมิติรูปทรงวิศวกรรม")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1: st.metric("ความหนารวมฐานราก (t)", f"{t_actual*100:.1f} ซม.")
    with col_m2: st.metric("ระยะลึกประสิทธิผลหน้าตัด (d)", f"{d_actual*100:.1f} ซม.")
    with col_m3: st.metric("เนื้อที่ผิวคอนกรีตฐานราก", f"{footing_area:.3f} ตร.ม.")
    with col_m4: st.metric("น้ำหนักดินถมเหนือก้อนฐานราก", f"{W_soil:.2f} ตัน")

with tab2:
    st.subheader("🌐 Interactive 3D Solid Model Mesh (Parametric Structural View)")
    
    def create_3d_prism_trace(vertices, z_start, z_end, face_color, opacity, name, show_legend=True):
        n = len(vertices)
        x_coords = [v[0] for v in vertices] * 2
        y_coords = [v[1] for v in vertices] * 2
        z_coords = [z_start] * n + [z_end] * n
        i_idx, j_idx, k_idx = [], [], []
        for idx in range(1, n - 1): i_idx.append(0); j_idx.append(idx); k_idx.append(idx + 1)
        for idx in range(1, n - 1): i_idx.append(n); j_idx.append(n + idx + 1); k_idx.append(n + idx)
        for idx in range(n):
            next_idx = (idx + 1) % n
            i_idx.extend([idx, idx]); j_idx.extend([next_idx, n + next_idx]); k_idx.extend([n + next_idx, n + idx])
        return go.Mesh3d(x=x_coords, y=y_coords, z=z_coords, i=i_idx, j=j_idx, k=k_idx, color=face_color, opacity=opacity, name=name, showlegend=show_legend)

    def draw_3d_wireframe_lines(fig, vertices, z_start, z_end, line_color='#2c3e50'):
        n = len(vertices)
        bx, by = [v[0] for v in vertices] + [vertices[0][0]], [v[1] for v in vertices] + [vertices[0][1]]
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=[z_start]*(n+1), mode='lines', line=dict(color=line_color, width=2.5), showlegend=False))
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=[z_end]*(n+1), mode='lines', line=dict(color=line_color, width=2.5), showlegend=False))
        for v in vertices: fig.add_trace(go.Scatter3d(x=[v[0], v[0]], y=[v[1], v[1]], z=[z_start, z_end], mode='lines', line=dict(color=line_color, width=2), showlegend=False))

    fig_3d = go.Figure()
    fig_3d.add_trace(create_3d_prism_trace(concrete_vertices, 0, t_actual, '#2ecc71', 0.6, 'ฐานรากคอนกรีต'))
    draw_3d_wireframe_lines(fig_3d, concrete_vertices, 0, t_actual, '#1e8449')

    column_vertices = [(-cx/2, -cy/2), (cx/2, -cy/2), (cx/2, cy/2), (-cx/2, cy/2)]
    fig_3d.add_trace(create_3d_prism_trace(column_vertices, t_actual, t_actual + 0.60, '#e74c3c', 0.85, 'เสาตอม่อ'))
    draw_3d_wireframe_lines(fig_3d, column_vertices, t_actual, t_actual + 0.60, '#922b21')

    for idx, (px, py) in enumerate(piles_actual):
        segments_count = 8
        pile_nodes = [(px + (pile_size/2)*math.cos(s*2*math.pi/segments_count), py + (pile_size/2)*math.sin(s*2*math.pi/segments_count)) for s in range(segments_count)]
        fig_3d.add_trace(create_3d_prism_trace(pile_nodes, -1.5, embed_m, '#34495e', 0.8, 'เสาเข็ม As-Built', show_legend=(idx == 0)))
        draw_3d_wireframe_lines(fig_3d, pile_nodes, -1.5, embed_m, '#2c3e50')

    fig_3d.update_layout(scene=dict(xaxis=dict(title='X (m)'), yaxis=dict(title='Y (m)'), zaxis=dict(title='Z Height (m)'), aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30))
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.subheader("📊 ตารางวิเคราะห์หน่วยแรงเฉือนควบคุมระดับประลัย (Critical Shear Evaluation)")
    df_shear_matrix = pd.DataFrame({
        "รายการดักจับแรงเฉือนวิกฤตหน้าตัด": ["Punching Shear (แรงเฉือนทะลุรอบขอบตอม่อ)", "Wide Beam Shear (แรงเฉือนคานกว้าง)"],
        "หน่วยแรงที่เกิดขึ้นจริง (v_u)": [v_up, v_uwb],
        "หน่วยแรงคอนกรีตที่ยอมให้ (phi * v_c)": [v_cp, v_cwb],
        "สถานะวิศวกรรมโครงสร้าง": ["ผ่านเกณฑ์ (Passed)" if v_up<=v_cp else "❌ หน่วยแรงเกินพิกัด", "ผ่านเกณฑ์ (Passed)" if v_uwb<=v_cwb else "❌ หน่วยแรงเกินพิกัด"]
    })
    st.dataframe(df_shear_matrix, use_container_width=True, hide_index=True)
    
    st.subheader("📊 ตารางสรุปการกระจายแรงปฏิกิริยาลงเสาเข็ม (As-Built Pile Load & Tension Matrix)")
    pile_status = []
    for r_s in pile_service_reactions:
        if r_s > pile_cap: pile_status.append("❌ แรงอัดเกินพิกัดบรรทุกปลอดภัย")
        elif r_s < 0 and abs(r_s) > pile_tension_cap: pile_status.append("❌ แรงถอนเกินพิกัดปลอดภัย")
        elif r_s < 0: pile_status.append("⚠️ มีแรงดึงสุทธิ (Tension Pass)")
        else: pile_status.append("✅ ผ่านเกณฑ์ปกติ (Compression Pass)")

    df_pile_output = pd.DataFrame({
        "เสาเข็มลำดับ": [f"เสาเข็มต้นที่ {i+1}" for i in range(n_piles)],
        "พิกัด X สัมบูรณ์หน้างาน (ม.)": [p[0] for p in piles_actual],
        "พิกัด Y สัมบูรณ์หน้างาน (ม.)": [p[1] for p in piles_actual],
        "แรงใช้งานจริง Service Load (ตัน)": pile_service_reactions,
        "แรงประลัยรวม Ultimate Load (ตัน)": p_ult_out,
        "สถานะวิศวกรรมปฏิกิริยา": pile_status
    })
    
    def highlight_pile_rows(val):
        if "❌" in val: return 'background-color: #fad1d1; color: #721c24; font-weight: bold;'
        elif "⚠️" in val: return 'background-color: #fff3cd; color: #856404;'
        return 'background-color: #d4edda; color: #155724;'

    st.dataframe(df_pile_output.style.map(highlight_pile_rows, subset=['สถานะวิศวกรรมปฏิกิริยา']), use_container_width=True, hide_index=True)
