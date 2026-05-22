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
# SYSTEM STABILITY & FONT MANAGEMENT
# =========================================================================
st.set_page_config(page_title="Enterprise Footing Suite V8.0", page_icon="📐", layout="wide")

@st.cache_resource(show_spinner=False)
def initialize_thai_font_system():
    font_dir = "fonts"
    font_name = "Kanit-Regular.ttf"
    font_path = os.path.join(font_dir, font_name)
    if not os.path.exists(font_dir): os.makedirs(font_dir, exist_ok=True)
    if not os.path.exists(font_path):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Regular.ttf"
            response = requests.get(font_url, timeout=5)
            if response.status_code == 200:
                with open(font_path, "wb") as f: f.write(response.content)
        except Exception: pass
    if os.path.exists(font_path):
        try:
            fm.fontManager.addfont(font_path)
            registered_font = fm.FontProperties(fname=font_path).get_name()
            plt.rcParams['font.family'] = registered_font
            plt.rcParams['axes.unicode_minus'] = False  
            return registered_font
        except Exception: pass
    return "sans-serif"

current_thai_font = initialize_thai_font_system()

# =========================================================================
# ADVANCED GEOMETRY ENGINE (SHOELACE & POLYGON MOMENTS)
# =========================================================================
def compute_polygon_properties(vertices):
    """คำนวณคุณสมบัติทางเรขาคณิตขั้นสูงของรูปหลายเหลี่ยมอิสระโดยใช้ Green's Theorem"""
    n = len(vertices)
    area = 0.0
    cx = 0.0
    cy = 0.0
    Ixx = 0.0
    Iyy = 0.0
    Ixy = 0.0
    
    for i in range(n):
        j = (i + 1) % n
        factor = (vertices[i][0] * vertices[j][1]) - (vertices[j][0] * vertices[i][1])
        area += factor
        cx += (vertices[i][0] + vertices[j][0]) * factor
        cy += (vertices[i][1] + vertices[j][1]) * factor
        
        Ixx += (vertices[i][1]**2 + vertices[i][1]*vertices[j][1] + vertices[j][1]**2) * factor
        Iyy += (vertices[i][0]**2 + vertices[i][0]*vertices[j][0] + vertices[j][0]**2) * factor
        Ixy += (vertices[i][0]*vertices[j][1] + 2*vertices[i][0]*vertices[i][1] + 2*vertices[j][0]*vertices[j][1] + vertices[j][0]*vertices[i][1]) * factor

    area = area / 2.0
    if abs(area) < 1e-6: return 1.0, 0.0, 0.0, 1.0, 1.0, 0.0
    
    area = abs(area)
    cx = cx / (6.0 * area)
    cy = cy / (6.0 * area)
    
    # ย้ายแกนเข้าสู่จุด Centroid (Parallel Axis Theorem)
    Ixx = abs(Ixx / 12.0) - area * cy**2
    Iyy = abs(Iyy / 12.0) - area * cx**2
    Ixy = abs(Ixy / 24.0) - area * cx * cy
    
    return area, cx, cy, max(0.001, Ixx), max(0.001, Iyy), Ixy

def get_polygon_section_width_at_y(target_y, vertices):
    intersections = []
    n = len(vertices)
    for i in range(n):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % n]
        if min(p1[1], p2[1]) <= target_y <= max(p1[1], p2[1]):
            if abs(p2[1] - p1[1]) > 1e-6:
                t = (target_y - p1[1]) / (p2[1] - p1[1])
                x_interp = p1[0] + t * (p2[0] - p1[0])
                intersections.append(x_interp)
            else:
                intersections.extend([p1[0], p2[0]])
    if len(intersections) < 2: return 0.1
    return max(intersections) - min(intersections)

# =========================================================================
# SERVICEABILITY CRACK CONTROL ENGINE (GERGELY-LUTZ)
# =========================================================================
def calculate_crack_width(M_service_kgcm, As_provided_cm2, d_cm, cover_cm, bar_dia_mm, spacing_cm):
    """คำนวณความกว้างรอยร้าวตามสมการ Gergely-Lutz (ACI)"""
    if M_service_kgcm <= 0 or As_provided_cm2 <= 0: return 0.0
    # ประมาณการหน่วยแรงในเหล็กเสริมตัวคูณสภาพใช้งาน (Service Stress)
    fs = M_service_kgcm / (As_provided_cm2 * 0.85 * d_cm) 
    if fs > 0.6 * 4000: fs = 0.6 * 4000 # ขีดจำกัดทางปฏิบัติ
    
    dc = cover_cm + (bar_dia_mm / 20) # ระยะหุ้มถึงศูนย์กลางเหล็ก (cm)
    # พื้นที่คอนกรีตประสิทธิผลรอบเหล็กเสริมดึงรายเส้น
    A_eff = (2 * dc * (spacing_cm if spacing_cm > 0 else 15.0))
    beta = 1.20 # อัตราส่วนระยะจากแกนสะเทิน
    
    # สมการ Gergely-Lutz: w (มม.)
    w = 11e-6 * beta * fs * (dc * A_eff)**(1/3)
    return w

# =========================================================================
# APPLICATION UI & SIDEBAR INPUTS
# =========================================================================
with st.sidebar:
    st.header("🏗️ Advanced Footing Configurator")
    design_module = st.selectbox("โมดูลการออกแบบเรขาคณิต:", 
        ["Single Arbitrary Polygon", "Combined Footing (>= 2 Columns)", "Strap / Cantilever Footing"])
    
    st.subheader("⚙️ Load Combination Factors")
    factor_dl = st.number_input("γ_DL (Dead Load Factor)", value=1.2, step=0.1)
    factor_ll = st.number_input("γ_LL (Live Load Factor)", value=1.6, step=0.1)
    
    st.subheader("🌪️ Lateral & Seismic Loads (ที่หัวเสาตอม่อรวม)")
    V_x_input = st.number_input("แรงเฉือนแนวราบ V_x (ตัน)", value=5.0)
    V_y_input = st.number_input("แรงเฉือนแนวราบ V_y (ตัน)", value=3.0)
    T_z_input = st.number_input("แรงบิดบิดหมุน T_z (ตัน-เมตร)", value=2.0)
    
    st.subheader("💧 Serviceability & Environment")
    env_condition = st.selectbox("สภาพแวดล้อมเพื่อควบคุมรอยร้าว:", 
        ["General (ทั่วไป - Max 0.30 mm)", "Water-Retaining / Marine (กันน้ำ/ทะเล - Max 0.15 mm)"])
    w_allow = 0.15 if "Water-Retaining" in env_condition else 0.30
    
    st.subheader("🧱 คุณสมบัติวัสดุและกำลัง")
    fc_prime = st.number_input("f'c คอนกรีต (KSC - Cylinder)", value=280)
    fy = st.number_input("fy เหล็กเสริม (KSC)", value=4000)
    bar_dia = st.selectbox("ขนาดเหล็กแกน DB (มม.)", [12, 16, 20, 25, 28, 32], index=2)
    pile_cap = st.number_input("กำลังรับแรงอัดเข็มยอมให้ (ตัน/ต้น)", value=35.0)
    pile_lateral_cap = st.number_input("กำลังรับแรงแนวราบเข็มยอมให้ (ตัน/ต้น)", value=5.0)
    
    st.subheader("📐 มิติและระยะหุ้ม")
    manual_t = st.number_input("ความหนาฐานราก t (ม.)", value=0.70, min_value=0.30)
    concrete_cover_cm = st.number_input("Concrete Covering (ซม.)", value=7.5)
    pile_embed_cm = 5.0
    
    # คำนวณความลึกประสิทธิผล d
    d_actual = manual_t - (concrete_cover_cm / 100) - (pile_embed_cm / 100) - ((bar_dia / 1000) / 2)

# =========================================================================
# CORE MODULE LOGIC
# =========================================================================
columns_data = []
vertices_input = []

if design_module == "Single Arbitrary Polygon":
    st.markdown("### 🗺️ Module: Single Footing with Freeform Polygon Geometry")
    st.write("ระบุพิกัดสลักมุม (Vertices) ของฐานรากเพื่อหลบสิ่งกีดขวาง ระบบจะหาจุดศูนย์ถ่วง (C.G.) อัตโนมัติ")
    
    default_vertices = pd.DataFrame({
        'Vertex': [f"V{i+1}" for i in range(6)],
        'X (ม.)': [-1.5, 1.5, 1.5, 0.5, -0.5, -1.5],
        'Y (ม.)': [1.5, 1.5, -0.5, -1.5, -1.5, -0.5]
    })
    edited_vertices = st.data_editor(default_vertices, use_container_width=True)
    vertices_input = list(zip(edited_vertices['X (ม.)'], edited_vertices['Y (ม.)']))
    
    st.subheader("📥 น้ำหนักบรรทุกลงเสาตอม่อเดี่ยว (ที่พิกัด 0,0)")
    c_dl = st.number_input("Column Dead Load (ตัน)", value=60.0)
    c_ll = st.number_input("Column Live Load (ตัน)", value=35.0)
    columns_data.append({'x': 0.0, 'y': 0.0, 'P_u': (factor_dl * c_dl) + (factor_ll * c_ll), 'P_s': c_dl + c_ll})

elif design_module == "Combined Footing (>= 2 Columns)":
    st.markdown("### 👥 Module: Combined Footing Analysis")
    st.write("รองรับการวางเสาตอม่อหลายต้นบนฐานเดียวกันเพื่อเฉลี่ยแรงดันและหลีกเลี่ยงการเกยกัน")
    
    default_cols = pd.DataFrame({
        'เสาต้นที่': ["Col 1 (นอก/ซ้าย)", "Col 2 (ใน/ขวา)"],
        'พิกัด X (ม.)': [-1.2, 1.2],
        'พิกัด Y (ม.)': [0.0, 0.0],
        'Dead Load (ตัน)': [45.0, 65.0],
        'Live Load (ตัน)': [25.0, 35.0]
    })
    edited_cols = st.data_editor(default_cols, use_container_width=True)
    
    for _, r in edited_cols.iterrows():
        pu = (factor_dl * r['Dead Load (ตัน)']) + (factor_ll * r['Live Load (ตัน)'])
        ps = r['Dead Load (ตัน)'] + r['Live Load (ตัน)']
        columns_data.append({'x': r['พิกัด X (ม.)'], 'y': r['พิกัด Y (ม.)'], 'P_u': pu, 'P_s': ps})
        
    # สร้างรูปทรงสี่เหลี่ยมผืนผ้าอัตโนมัติหุ้มเสา
    vertices_input = [(-2.2, -1.2), (2.2, -1.2), (2.2, 1.2), (-2.2, 1.2)]

elif design_module == "Strap / Cantilever Footing":
    st.markdown("### 🔗 Module: Strap Footing with Cantilever Beam Mechanism")
    st.write("กรณีเสาชิดแนวเขต (Exterior Column) ระบบจะใช้คานรัด (Strap Beam) ถ่ายโมเมนต์เยื้องศูนย์กลับสู่ฐานรากต้นใน")
    
    col1_p = st.number_input("พิกัด X เสาต้นนอก (ชิดเขตเยื้องศูนย์)", value=-2.0)
    col2_p = st.number_input("พิกัด X เสาต้นใน (รับสมดุล)", value=2.0)
    p_ext_dl = st.number_input("Dead Load เสานอก (ตัน)", value=40.0)
    p_ext_ll = st.number_input("Live Load เสานอก (ตัน)", value=20.0)
    p_int_dl = st.number_input("Dead Load เสาใน (ตัน)", value=70.0)
    p_int_ll = st.number_input("Live Load เสาใน (ตัน)", value=35.0)
    
    L_strap = abs(col2_p - col1_p)
    e_ecc = 0.50 # ระยะสมมุติของการเยื้องศูนย์กลุ่มเข็มฐานนอก
    
    # กลไกถ่ายแรงสมดุลผ่านคานรัด (Strap Beam Mechanics)
    P_ext_u = (factor_dl * p_ext_dl) + (factor_ll * p_ext_ll)
    P_int_u = (factor_dl * p_int_dl) + (factor_ll * p_int_ll)
    delta_P_u = (P_ext_u * e_ecc) / L_strap
    
    P_ext_s = p_ext_dl + p_ext_ll
    P_int_s = p_int_dl + p_int_ll
    delta_P_s = (P_ext_s * e_ecc) / L_strap
    
    columns_data.append({'x': col1_p + e_ecc, 'y': 0.0, 'P_u': P_ext_u + delta_P_u, 'P_s': P_ext_s + delta_P_s, 'label': 'ฐานรากภายนอก'})
    columns_data.append({'x': col2_p, 'y': 0.0, 'P_u': P_int_u - delta_P_u, 'P_s': P_int_s - delta_P_s, 'label': 'ฐานรากภายใน'})
    
    vertices_input = [(-2.8, -1.0), (2.8, -1.0), (2.8, 1.0), (-2.8, 1.0)]

# คำนวณคุณสมบัติของฐานคอนกรีตแผ่นพื้นรูปทรงป้อนเข้า
f_area, f_cx, f_cy, f_Ixx, f_Iyy, f_Ixy = compute_polygon_properties(vertices_input)

# =========================================================================
# AS-BUILT PILE GROUP GENERATION & INDIVIDUAL LOADING
# =========================================================================
st.markdown("---")
st.markdown("### 🎯 2. จัดวางและตรวจสอบพิกัดเสาเข็มรายต้น (As-Built Mapping)")
st.write("ระบุพิกัดหน้างานจริงเพื่อวิเคราะห์การเยื้องศูนย์และแรงบิดระดับอาคาร")

default_piles = pd.DataFrame({
    'ชื่อเข็ม': ["P1", "P2", "P3", "P4", "P5", "P6"],
    'พิกัด X (ม.)': [-1.2, 0.0, 1.2, -1.2, 0.0, 1.2],
    'พิกัด Y (ม.)': [0.8, 0.8, 0.8, -0.8, -0.8, -0.8]
})
edited_piles = st.data_editor(default_piles, use_container_width=True)

piles_list = list(zip(edited_piles['พิกัด X (ม.)'], edited_piles['Y (ม.)' if 'Y (ม.)' in edited_piles.columns else 'พิกัด Y (ม.)']))
n_piles = len(piles_list)

# คำนวณหาจุดศูนย์ถ่วง (C.G.) ของกลุ่มเสาเข็ม
pg_cx = sum(p[0] for p in piles_list) / n_piles
pg_cy = sum(p[1] for p in piles_list) / n_piles

# คุณสมบัติ Inertia ของกลุ่มเสาเข็ม (Pile Group Mechanics)
pg_Ixx = sum((p[1] - pg_cy)**2 for p in piles_list)
pg_Iyy = sum((p[0] - pg_cx)**2 for p in piles_list)
pg_Ixy = sum((p[0] - pg_cx) * (p[1] - pg_cy) for p in piles_list)

if abs(pg_Ixx * pg_Iyy - pg_Ixy**2) < 1e-4:
    pg_Ixx = max(0.01, pg_Ixx); pg_Iyy = max(0.01, pg_Iyy); pg_Ixy = 0.0

# รวมแรงและโมเมนต์ทั้งหมดเข้าสู่จุดศูนย์ถ่วงกลุ่มเสาเข็ม (Global Equilibrium Transformation)
total_P_u = 0.0
total_P_s = 0.0
total_Mx_u = 0.0
total_My_u = 0.0
total_Mx_s = 0.0
total_My_s = 0.0

for col in columns_data:
    total_P_u += col['P_u']
    total_P_s += col['P_s']
    total_Mx_u += col['P_u'] * (col['y'] - pg_cy)
    total_My_u += col['P_u'] * (col['x'] - pg_cx)
    total_Mx_s += col['P_s'] * (col['y'] - pg_cy)
    total_My_s += col['P_s'] * (col['x'] - pg_cx)

# เพิ่มน้ำหนักบรรทุกคอนกรีตฐานรากเนื้อตัวเอง
footing_w_u = factor_dl * (f_area * manual_t * 2.4)
footing_w_s = f_area * manual_t * 2.4
total_P_u += footing_w_u
total_P_s += footing_w_s

# =========================================================================
# LATERAL & SEISMIC DISTRIBUTION ENGINE
# =========================================================================
# คำนวณพิกัดกำลังรัศมีกำลังสอง (Polar Grid Radius) เพื่อบิดกระจายแรงเฉือน
polar_R_sum = sum((p[0] - pg_cx)**2 + (p[1] - pg_cy)**2 for p in piles_list)
if polar_R_sum == 0: polar_R_sum = 1.0

pile_reactions_u = []
pile_reactions_s = []
pile_lateral_forces = []

for p in piles_list:
    dx = p[0] - pg_cx
    dy = p[1] - pg_cy
    
    # 1. แรงปฏิกิริยาแนวดิ่ง (Vertical Reactions) ด้วยสมการหน้าตัดอสมมาตรเต็มรูปแบบ
    denom = (pg_Ixx * pg_Iyy) - pg_Ixy**2
    R_u = (total_P_u / n_piles) + \
          ((total_Mx_u * pg_Iyy - total_My_u * pg_Ixy) / denom) * dy + \
          ((total_My_u * pg_Ixx - total_Mx_u * pg_Ixy) / denom) * dx
          
    R_s = (total_P_s / n_piles) + \
          ((total_Mx_s * pg_Iyy - total_My_s * pg_Ixy) / denom) * dy + \
          ((total_My_s * pg_Ixx - total_Mx_s * pg_Ixy) / denom) * dx
          
    pile_reactions_u.append(R_u)
    pile_reactions_s.append(R_s)
    
    # 2. การกระจายแรงเฉือนระดับราบและแรงบิด (Horizontal Shear Redistribution)
    V_ix = (V_x_input / n_piles) - (T_z_input * dy / polar_R_sum)
    V_iy = (V_y_input / n_piles) + (T_z_input * dx / polar_R_sum)
    V_combined = math.sqrt(V_ix**2 + V_iy**2)
    pile_lateral_forces.append(V_combined)

# =========================================================================
# RIGID VS FLEXIBLE MATRIX STRUCTURAL ASSESSMENT
# =========================================================================
# ดัชนีประเมินพฤติกรรมการโก่งตัวตามทฤษฎีแผ่นพื้นบนสปริงยืดหยุ่น (Winkler Foundation Criteria)
E_concrete = 4700 * math.sqrt(fc_prime) * 10 # kg/cm2 -> t/m2 format conversion
Flexural_Rigidity_D = (E_concrete * manual_t**3) / (12 * (1 - 0.2**2))
# ดัชนีความยืดหยุ่นสัมพัทธ์ (Characteristic Length) Lambda
K_subgrade = 10000 # สมมุติฐานค่า Stiffness ของเสาเข็มทดแทนดินแวดล้อม (t/m3)
lambda_rigidity = (K_subgrade / (4 * Flexural_Rigidity_D))**(0.25)

is_rigid = "แข็งเกร็งสัมบูรณ์ (Rigid Cap)" if (1.75 / lambda_rigidity) > 2.0 else "ฐานรากยืดหยุ่นสูง (Flexible Cap - แนะนำให้ตรวจสอบพฤติกรรมดัดเพิ่มเติม)"

# =========================================================================
# CRACK WIDTH & STEEL DESIGN INTERFACE
# =========================================================================
Mu_max_design = abs(max(pile_reactions_u)) * 0.60 # ประมาณการโมเมนต์โมดูลย่อยดัดวิกฤต
w_flex_cm = get_polygon_section_width_at_y(pg_cy, vertices_input) * 100

As_min = 0.0018 * w_flex_cm * (manual_t * 100)
ab_area = (math.pi * (bar_dia / 10) ** 2) / 4 
n_bars = max(math.ceil(As_min / ab_area), 4)
spacing_cm = min(45.0, math.floor((w_flex_cm - 15) / (n_bars - 1))) if n_bars > 1 else 20.0

# เรียกใช้ระบบวิเคราะห์ความกว้างรอยร้าว
computed_w_crack = calculate_crack_width(Mu_max_design * 1000 * 100, n_bars * ab_area, d_actual * 100, concrete_cover_cm, bar_dia, spacing_cm)

# =========================================================================
# DASHBOARD RENDERING & ANALYTICAL TWIN PLOTS
# =========================================================================
st.markdown("---")
st.subheader("📊 3. ผลลัพธ์การตรวจสอบความปลอดภัยทางโครงสร้างขั้นสูง (Structural Diagnostic)")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("ความกว้างรอยร้าววิกฤต (Crack Width)", f"{computed_w_crack:.3f} mm", 
              delta=f"Max Allowable: {w_allow} mm", delta_color="inverse" if computed_w_crack > w_allow else "normal")
    if computed_w_crack > w_allow: st.error("❌ ขนาดรอยร้าวเกินค่ากำหนดสำหรับสภาวะแวดล้อมนี้! แนะนำให้เพิ่มเหล็กเสริมหรือความหนาฐานราก")
with c2:
    max_V_pile = max(pile_lateral_forces)
    st.metric("แรงเฉือนหัวเข็มสูงสุด (Max Lateral Pile Load)", f"{max_V_pile:.2f} ตัน", 
              delta=f"Cap: {pile_lateral_cap:.1f} ตัน", delta_color="inverse" if max_V_pile > pile_lateral_cap else "normal")
with c3:
    st.metric("พฤติกรรมโครงสร้างฐานราก", is_rigid, f"λ Characteristic: {lambda_rigidity:.2f}")

# ตารางรายงานผลลัพธ์รายเข็ม
df_summary = pd.DataFrame({
    'เสาเข็ม': edited_piles['ชื่อเข็ม'],
    'พิกัด X (ม.)': [p[0] for p in piles_list],
    'พิกัด Y (ม.)': [p[1] for p in piles_list],
    'แรงแนวแกนอัด R_u (ตัน)': pile_reactions_u,
    'แรงแนวแกนใช้งาน R_s (ตัน)': pile_reactions_s,
    'แรงเฉือนแนวราบ V_combined (ตัน)': pile_lateral_forces
})
st.dataframe(df_summary.style.highlight_max(axis=0, color='#f2d7d5'), use_container_width=True)

# แผนภาพกราฟฟิกจำลองพฤติกรรมแบบวิศวกรรม (Engineering Graphical Twin)
st.markdown("---")
st.subheader("🗺️ 4. แผนภูมิวิเคราะห์พิกัดเรขาคณิตและแรงปฏิกิริยาแนวราบ (2D & 3D Interactive)")

col_p1, col_p2 = st.columns(2)
with col_p1:
    fig, ax = plt.subplots(figsize=(6, 6))
    # วาดรูปขอบเขตฐานรากขอบเขตอิสระ
    x_v = [v[0] for v in vertices_input] + [vertices_input[0][0]]
    y_v = [v[1] for v in vertices_input] + [vertices_input[0][1]]
    ax.plot(x_v, y_v, '-', color='#27ae60', linewidth=2.5, label='ขอบเขตคอนกรีต')
    ax.fill(x_v, y_v, color='#2ecc71', alpha=0.15)
    
    # วาดเสาตอม่อ
    for col in columns_data:
        ax.plot(col['x'], col['y'], 's', color='#c0392b', markersize=12, label='เสาตอม่อ')
        
    # วาดเข็มพร้อม Vector แรงแนวราบ
    for i, p in enumerate(piles_list):
        ax.plot(p[0], p[1], 'o', color='#2c3e50', markersize=14)
        ax.text(p[0], p[1], f"P{i+1}", color='white', ha='center', va='center', fontsize=8, fontweight='bold')
        # เวกเตอร์ลูกศรแสดงทิศทางและสัดส่วนแรงเฉือนแนวราบที่หัวเข็ม
        ax.quiver(p[0], p[1], V_x_input/n_piles, V_y_input/n_piles, color='#d35400', alpha=0.6, width=0.007)
        
    ax.axhline(pg_cy, color='blue', linestyle=':', alpha=0.5, label='Pile Group Centroid')
    ax.axvline(pg_cx, color='blue', linestyle=':', alpha=0.5)
    ax.set_title("แผนผัง 2D แสดงพิกัดร่วมและเวกเตอร์แรงเฉือนหัวเข็ม", fontsize=11, fontweight='bold')
    ax.axis('equal')
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)

with col_p2:
    # การจำลองโมเดลสามมิติแบบมีปฏิสัมพันธ์ (3D Interactive Render Engine)
    fig_3d = go.Figure()
    
    # วาดแผ่นพื้นคอนกรีตฐานรากขอบรูปทรงสุ่ม
    x_c = [v[0] for v in vertices_input]
    y_c = [v[1] for v in vertices_input]
    n_v = len(vertices_input)
    
    # สร้าง Mesh3D ปริมาตรแบบโพลีกอนทรงปริซึม
    fig_3d.add_trace(go.Mesh3d(
        x=x_c * 2, y=y_c * 2,
        z=[0]*n_v + [manual_t]*n_v,
        alphahull=0, color='#2ecc71', opacity=0.4, name='ฐานรากคอนกรีต'
    ))
    
    fig_3d.add_trace(go.Scatter3d(
        x=[p[0] for p in piles_list],
        y=[p[1] for p in piles_list],
        z=[0]*n_piles,
        mode='markers+text',
        marker=dict(size=10, color='#34495e', symbol='circle'), # ✅ เปลี่ยนเป็น 'circle'
        text=[f"P{i+1}" for i in range(n_piles)],
        name='เสาเข็มหน้างานจริง'
    ))
    
    fig_3d.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=10))
    st.plotly_chart(fig_3d, use_container_width=True)
