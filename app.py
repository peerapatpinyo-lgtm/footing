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
st.set_page_config(page_title="Enterprise Footing Suite V7.3", page_icon="📐", layout="wide")

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

st.title("📐 Enterprise Footing Suite (V7.3 - Fixed Triangular Manual Input)")
st.markdown("### Footing Analysis System: Fixed Manual Triangular Dimensioning and Edge Safety Check")
st.markdown("---")

def point_to_segment_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0: return math.sqrt((px - x1)**2 + (py - y1)**2)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    return math.sqrt((px - (x1 + t * dx))**2 + (py - (y1 + t * dy))**2)

# =========================================================================
# SIDEBAR CONTROL INTERFACE
# =========================================================================
with st.sidebar:
    st.header("🏗️ Statics and Material Specifications")
    footing_shape_type = st.selectbox(
        "Footing Geometry Shape:", 
        ["Truncated Triangular Footing", "Rectangular Footing"],
        index=0
    )
    
    st.subheader("1. Pile Properties and Load Capacity")
    if footing_shape_type == "Truncated Triangular Footing":
        n_piles = 3
    else:
        n_piles = st.selectbox("Number of Piles in Group:", [2, 3, 4, 5, 6, 8, 9], index=2)
        
    pile_size = st.number_input("Pile Cross-Section Size (m)", value=0.30, min_value=0.15, step=0.05)
    pile_cap = st.number_input("Safe Pile Compressive Capacity (tons/pile)", value=30.0, min_value=1.0)
    pile_tension_cap = st.number_input("Safe Pile Uplift Capacity (tons/pile)", value=10.0, min_value=0.0)
    
    S_dist = 3.0 * pile_size
    E_dist = max(pile_size, 0.35)

    # Calculate Geometric Minimum Limit
    if footing_shape_type == "Rectangular Footing":
        if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
        elif n_piles == 3: piles_ideal = [(-S_dist, 0), (0, 0), (S_dist, 0)]
        elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
        elif n_piles == 5: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2), (0, 0)]
        elif n_piles == 6: piles_ideal = [(-S_dist/2, -S_dist), (S_dist/2, -S_dist), (-S_dist/2, 0), (S_dist/2, 0), (-S_dist/2, S_dist), (S_dist/2, S_dist)]
        elif n_piles == 8: piles_ideal = [(-1.5*S_dist, -S_dist/2), (-0.5*S_dist, -S_dist/2), (0.5*S_dist, -S_dist/2), (1.5*S_dist, -S_dist/2), (-1.5*S_dist, S_dist/2), (-0.5*S_dist, S_dist/2), (0.5*S_dist, S_dist/2), (1.5*S_dist, S_dist/2)]
        else: piles_ideal = [(x, y) for x in [-S_dist, 0, S_dist] for y in [-S_dist, 0, S_dist]]
        
        B_min_geometry = (max(p[0] for p in piles_ideal) - min(p[0] for p in piles_ideal)) + 2 * E_dist
        L_min_geometry = (max(p[1] for p in piles_ideal) - min(p[1] for p in piles_ideal)) + 2 * E_dist
    else:
        piles_ideal = [(0, S_dist / math.sqrt(3)), (-S_dist / 2, -S_dist / (2 * math.sqrt(3))), (S_dist / 2, -S_dist / (2 * math.sqrt(3)))]
        # Calculate minimum dimensions for truncated triangular edge
        y_p1, y_p23 = S_dist / math.sqrt(3), -S_dist / (2 * math.sqrt(3))
        v1_t = (-E_dist / math.sqrt(3), y_p1 + E_dist)
        v2_t = (E_dist / math.sqrt(3), y_p1 + E_dist)
        v3_t = (S_dist / 2 + 2 * E_dist / math.sqrt(3), y_p23)
        v4_t = (S_dist / 2 + E_dist / math.sqrt(3), y_p23 - E_dist)
        v5_t = (-S_dist / 2 - E_dist / math.sqrt(3), y_p23 - E_dist)
        v6_t = (-S_dist / 2 - 2 * E_dist / math.sqrt(3), y_p23)
        base_v_temp = [v1_t, v2_t, v3_t, v4_t, v5_t, v6_t]
        B_min_geometry = max(v[0] for v in base_v_temp) - min(v[0] for v in base_v_temp)
        L_min_geometry = max(v[1] for v in base_v_temp) - min(v[1] for v in base_v_temp)

    st.subheader("2. Define Footing Dimensions (B x L)")
    dim_mode = st.radio("Dimensioning Method:", ["Auto-Size", "Manual Override"])
    
    # Allows manual override for all footing types
    if dim_mode == "Manual Override":
        st.caption(f"⚠️ Minimum Geometric Limits based on Pile Coordinates: B ≥ {B_min_geometry:.2f} m | L ≥ {L_min_geometry:.2f} m")
        B_input = st.number_input("Specify Total Width on X-axis (B, meters)", value=float(round(B_min_geometry, 2)), min_value=0.4, step=0.05)
        L_input = st.number_input("Specify Total Length on Y-axis (L, meters)", value=float(round(L_min_geometry, 2)), min_value=0.4, step=0.05)
        
        B_ft = max(B_input, B_min_geometry)
        L_ft = max(L_input, L_min_geometry)
        
        if B_input < B_min_geometry or L_input < L_min_geometry:
            st.error("🚨 Specified dimensions are smaller than pile centers + edge distance! The system has adjusted to minimum values for safety.")
    else:
        B_ft = B_min_geometry
        L_ft = L_min_geometry

    st.subheader("3. Service Loads & Soil Backfill")
    DL = st.number_input("Dead Load (tons)", value=55.0, min_value=0.0)
    LL = st.number_input("Live Load (tons)", value=30.0, min_value=0.0)
    Mcx = st.number_input("Moment M_cx (ton-m)", value=10.0)
    Mcy = st.number_input("Moment M_cy (ton-m)", value=8.0)
    soil_depth = st.number_input("Soil Backfill Depth (m)", value=1.0, min_value=0.0, step=0.1)
    soil_density = st.number_input("Soil Density (t/m³)", value=1.8, min_value=1.0, step=0.1)
    
    st.subheader("4. Column Section and Material Strengths")
    cx = st.number_input("Column Width X-axis (meters)", value=0.35, min_value=0.15, step=0.05)
    cy = st.number_input("Column Width Y-axis (meters)", value=0.35, min_value=0.15, step=0.05)
    col_position = st.selectbox("Column Position:", ["Interior", "Edge", "Corner"])
    fc_prime = st.number_input("Ultimate Compressive Strength fc' (ksc)", value=280, min_value=150, step=10)
    fy = st.selectbox("Main Rebar Yield Strength fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("Main Rebar Size (mm)", [12, 16, 20, 25, 28, 32], index=2)
    
    st.subheader("5. Thickness and Concrete Cover")
    thickness_mode = st.radio("Thickness Determination Method:", ["Auto-Optimize", "Manual Override"])
    manual_t = 0.65
    if thickness_mode == "Manual Override":
        manual_t_cm = st.number_input("Specify Footing Thickness t (cm)", min_value=30, max_value=300, value=65, step=5)
        manual_t = manual_t_cm / 100
        
    pile_embed_cm = st.number_input("Pile Embedment Depth (cm)", value=5.0, min_value=0.0, step=1.0)
    concrete_cover_cm = st.number_input("Net Concrete Cover (cm)", value=7.5, min_value=3.0, step=0.5)

phi_shear, phi_flexure = 0.75, 0.90
ab_area = (math.pi * (bar_dia / 10) ** 2) / 4

# =========================================================================
# AS-BUILT FIELD SURVEY DATA EDITOR
# =========================================================================
st.markdown("### 📍 1. As-Built Field Survey Analysis")
st.info("💡 **Data Linkage:** This table directly affects the engineering blueprint below.")

df_initial = pd.DataFrame({
    'Pile Name': [f"P{i+1}" for i in range(n_piles)],
    'Design X (m)': [round(p[0], 3) for p in piles_ideal],
    'Design Y (m)': [round(p[1], 3) for p in piles_ideal],
    'ΔX (m) - Field': [0.00] * n_piles,
    'ΔY (m) - Field': [0.00] * n_piles
})

edited_df = st.data_editor(df_initial, disabled=['Pile Name', 'Design X (m)', 'Design Y (m)'], hide_index=True, use_container_width=True)

piles_actual = []
for _, row in edited_df.iterrows():
    p_act_x = row['Design X (m)'] + row['ΔX (m) - Field']
    p_act_y = row['Design Y (m)'] + row['ΔY (m) - Field']
    piles_actual.append((p_act_x, p_act_y))

cg_actual_x = sum(p[0] for p in piles_actual) / n_piles
cg_actual_y = sum(p[1] for p in piles_actual) / n_piles
ecc_x, ecc_y = 0.0 - cg_actual_x, 0.0 - cg_actual_y

piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group = sum(p[0]**2 for p in piles_relative)
I_xx_group = sum(p[1]**2 for p in piles_relative)

P_service = DL + LL
P_ultimate = (1.2 * DL) + (1.6 * LL)
average_load_factor = P_ultimate / P_service if P_service > 0 else 1.45
Mu_cx = Mcx * average_load_factor
Mu_cy = Mcy * average_load_factor

# --- Calculate footing concrete corner coordinates based on true scale ---
if footing_shape_type == "Rectangular Footing":
    footing_area = B_ft * L_ft
    x_max_edge, x_min_edge = B_ft / 2, -B_ft / 2
    y_max_edge, y_min_edge = L_ft / 2, -L_ft / 2
    concrete_vertices = [(x_min_edge, y_min_edge), (x_max_edge, y_min_edge), (x_max_edge, y_max_edge), (x_min_edge, y_max_edge)]
else:
    # Calculate minimal truncated triangle shape (Base Geometry)
    y_p1, y_p23 = S_dist / math.sqrt(3), -S_dist / (2 * math.sqrt(3))
    v1_tri = (-E_dist / math.sqrt(3), y_p1 + E_dist)
    v2_tri = (E_dist / math.sqrt(3), y_p1 + E_dist)
    v3_tri = (S_dist / 2 + 2 * E_dist / math.sqrt(3), y_p23)
    v4_tri = (S_dist / 2 + E_dist / math.sqrt(3), y_p23 - E_dist)
    v5_tri = (-S_dist / 2 - E_dist / math.sqrt(3), y_p23 - E_dist)
    v6_tri = (-S_dist / 2 - 2 * E_dist / math.sqrt(3), y_p23)
    base_vertices = [v1_tri, v2_tri, v3_tri, v4_tri, v5_tri, v6_tri]
    
    # Find scale ratio from column center (0,0) in case user overrides dimensions
    B_base = max(v[0] for v in base_vertices) - min(v[0] for v in base_vertices)
    L_base = max(v[1] for v in base_vertices) - min(v[1] for v in base_vertices)
    
    scale_x = B_ft / B_base if B_base > 0 else 1.0
    scale_y = L_ft / L_base if L_base > 0 else 1.0
    
    # Map scaled concrete coordinates
    concrete_vertices = [(v[0] * scale_x, v[1] * scale_y) for v in base_vertices]
    
    # Calculate true scaled concrete area
    base_area = (math.sqrt(3)/4)*(S_dist**2) + (3*S_dist*E_dist) + (2*math.sqrt(3)*(E_dist**2))
    footing_area = base_area * scale_x * scale_y
    
    # Update true dimension boundaries
    B_ft = max(v[0] for v in concrete_vertices) - min(v[0] for v in concrete_vertices)
    L_ft = max(v[1] for v in concrete_vertices) - min(v[1] for v in concrete_vertices)

col_area = cx * cy
W_soil = max(0.0, footing_area - col_area) * soil_depth * soil_density

# As-Built Edge Distance Check
net_min_edge_dist = float('inf')
segments = [(concrete_vertices[i], concrete_vertices[(i+1)%len(concrete_vertices)]) for i in range(len(concrete_vertices))]
for px, py in piles_actual:
    p_radius = pile_size / 2
    current_min = min(point_to_segment_dist(px, py, seg[0][0], seg[0][1], seg[1][0], seg[1][1]) - p_radius for seg in segments)
    if current_min < net_min_edge_dist: net_min_edge_dist = current_min

if net_min_edge_dist < 0.10:
    st.error(f"🚨 **[As-Built Edge Distance Alert]** Piles have deviated, leaving only {net_min_edge_dist*100:.1f} cm edge distance. Risk of concrete spalling!")

def get_triangular_width_at_y(target_y):
    if footing_shape_type == "Rectangular Footing": return B_ft
    y_coords_v = [v[1] for v in concrete_vertices]
    y_top_bound, y_bot_bound = max(y_coords_v), min(y_coords_v)
    if target_y > y_top_bound or target_y < y_bot_bound: return 0.0
    # Estimate width on Y axis for scaled triangle
    x_max_at_y = max([v[0] for v in concrete_vertices if abs(v[1] - target_y) < 0.1], default=B_ft/2)
    return 2 * abs(x_max_at_y)

# =========================================================================
# ENGINEERING CALCULATIONS ROUTINES
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
        
    b1_box, b2_box = cx + eval_d, cy + eval_d
    b_0 = 2 * (b1_box + b2_box)
    A_punching_cm2 = b_0 * eval_d * 10000
    V_u_punching_kg = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_actual) if abs(px) > (cx/2 + eval_d/2) or abs(py) > (cy/2 + eval_d/2))
    v_u_punching_stress = V_u_punching_kg / A_punching_cm2 if A_punching_cm2 > 0 else 0.0
    beta_ratio = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "Interior" else (30 if col_position == "Edge" else 20)
    v_c_allow_punching = phi_shear * min(0.27*(2 + 4/beta_ratio)*math.sqrt(fc_prime), 0.27*(alpha_s*(eval_d*100)/(b_0*100) + 2)*math.sqrt(fc_prime), 1.06*math.sqrt(fc_prime))
    
    cut_y_pos = cy/2 + eval_d
    V_u_wb = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_actual) if py >= cut_y_pos)
    bw_y = get_triangular_width_at_y(cut_y_pos) * 100
    v_u_wb_max = V_u_wb / (bw_y * eval_d * 100) if bw_y > 0 else 0
    v_c_allow_wb = phi_shear * 0.53 * math.sqrt(fc_prime)
    
    return (v_u_punching_stress <= v_c_allow_punching) and (v_u_wb_max <= v_c_allow_wb), v_u_punching_stress, v_c_allow_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions

def compute_effective_depth(t_total):
    return t_total - (concrete_cover_cm / 100) - (pile_embed_cm / 100) - ((bar_dia / 1000) / 2)

if thickness_mode == "Auto-Optimize":
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

# FLEXURAL REBAR DESIGN
if footing_shape_type == "Rectangular Footing":
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
    if Rn > (rho_max * fy * (1 - 0.59 * rho_max * fy / fc_prime)): return 0, 0, True, 0.0
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * fc_prime)))
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 4)
    spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, 45.0), False, As_req

n_main_bars_x, sp_main_x, crash_fx, As_req_x = design_rebar_by_axis(Mu_x_face, w_flex_x, d_actual*100, t_actual*100)
n_main_bars_y, sp_main_y, crash_fy, As_req_y = design_rebar_by_axis(Mu_y_face, w_flex_y, (d_actual - bar_dia/1000)*100, t_actual*100)

is_structure_crashed = crash_fx or crash_fy or (not step_safe)

# =========================================================================
# DIAGNOSTICS & ADVISORY REPORT
# =========================================================================
st.markdown("### 🔍 2. Structural Health and Minimum Dimensions Report")
col_adv1, col_adv2 = st.columns(2)
with col_adv1:
    st.write(f"**📐 Minimum Geometric Footing Size Check:**")
    st.write(f"* Actual Dimensions Used: **{B_ft:.2f} x {L_ft:.2f} meters**")
    st.success(f"✅ Dimensions pass safety minimums ($B \\ge {B_min_geometry:.2f}$ m, $L \\ge {L_min_geometry:.2f}$ m)")

with col_adv2:
    if not step_safe:
        st.error("🚨 **Shear Status:** Failed! Section is too narrow or thin to resist punching shear.")
    else:
        st.success("✅ **Shear Status:** Passed all column shear stress checks.")

# =========================================================================
# 2D ENGINEERING BLUEPRINT WITH DIMENSION LINES
# =========================================================================
if not is_structure_crashed:
    st.markdown("### 📊 3. 2D Engineering Blueprint")
    fig, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Top View Plan
    footing_shape_patch = patches.Polygon(concrete_vertices, closed=True, linewidth=2.5, edgecolor='#2c3e50', facecolor='#eaeded', zorder=1)
    ax_plan.add_patch(footing_shape_patch)
    
    x_coords = [v[0] for v in concrete_vertices]
    y_coords = [v[1] for v in concrete_vertices]
    
    ax_plan.set_xlim(min(x_coords) - 0.6, max(x_coords) + 0.6)
    ax_plan.set_ylim(min(y_coords) - 0.6, max(y_coords) + 0.6)
    
    ax_plan.add_patch(patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.8, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4))
    ax_plan.scatter(0, 0, color='red', marker='+', s=200, linewidths=3, label='Column Center (0,0)', zorder=6)
    ax_plan.scatter(cg_actual_x, cg_actual_y, color='#f39c12', marker='X', s=130, label='True C.G. of Piles', zorder=5)
    
    for idx, (px, py) in enumerate(piles_actual):
        ix, iy = piles_ideal[idx]
        pile_ideal_draw = patches.Circle((ix, iy), pile_size/2, linewidth=1.2, edgecolor='#bdc3c7', facecolor='none', linestyle='--', alpha=0.7, zorder=2)
        ax_plan.add_patch(pile_ideal_draw)
        
        pile_draw = patches.Circle((px, py), pile_size/2, linewidth=1.5, edgecolor='#34495e', facecolor='#7f8c8d', alpha=0.8, zorder=3)
        ax_plan.add_patch(pile_draw)
        ax_plan.text(px, py, f"P{idx+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold', zorder=4)
        
        if ix != px or iy != py:
            ax_plan.plot([ix, px], [iy, py], color='#e74c3c', linestyle='-', linewidth=1.8, zorder=4)
            ax_plan.scatter(ix, iy, color='#e74c3c', marker='.', s=40, zorder=4)
            
    # --- 📐 Dynamic Dimension Lines System ---
    # X-Axis Dimensions (Total width at the bottom)
    dim_y = min(y_coords) - 0.25
    ax_plan.annotate('', xy=(min(x_coords), dim_y), xytext=(max(x_coords), dim_y),
                     arrowprops=dict(arrowstyle='<->', color='#2c3e50', lw=1.5))
    ax_plan.text(0, dim_y - 0.12, f"B (Total Width) = {B_ft:.2f} m", ha='center', va='center', color='#2c3e50', fontweight='bold', fontsize=10)
    
    # Y-Axis Dimensions (Total length on the left)
    dim_x = min(x_coords) - 0.25
    ax_plan.annotate('', xy=(dim_x, min(y_coords)), xytext=(dim_x, max(y_coords)),
                     arrowprops=dict(arrowstyle='<->', color='#2c3e50', lw=1.5))
    ax_plan.text(dim_x - 0.12, 0, f"L (Total Length) = {L_ft:.2f} m", ha='center', va='center', color='#2c3e50', fontweight='bold', fontsize=10, rotation=90)

    ax_plan.plot([], [], color='#bdc3c7', linestyle='--', linewidth=1.5, label='Design Position')
    ax_plan.plot([], [], color='#34495e', marker='o', markersize=8, markerfacecolor='#7f8c8d', linestyle='none', label='As-Built Position')
    ax_plan.plot([], [], color='#e74c3c', linestyle='-', linewidth=1.8, label='Deviation Vector')
        
    ax_plan.set_aspect('equal')
    ax_plan.grid(True, linestyle=':', alpha=0.6)
    ax_plan.legend(loc="upper right", fontsize=8)
    ax_plan.set_title(f"Plan showing actual concrete dimensions {B_ft:.2f} x {L_ft:.2f} m (Top View)", fontsize=11, fontweight='bold')
    
    # Section View
    sec_w = B_ft
    ax_sec.add_patch(patches.Rectangle((-sec_w/2, 0), sec_w, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#f2f4f4', zorder=2))
    
    embed_m = pile_embed_cm / 100
    for idx, (px, py) in enumerate(piles_actual):
        ix, iy = piles_ideal[idx]
        if abs(py) < L_ft/2:
            ax_sec.add_patch(patches.Rectangle((ix - pile_size/2, -0.4), pile_size, 0.4 + embed_m, linewidth=1.2, edgecolor='#bdc3c7', facecolor='none', linestyle='--', alpha=0.5, zorder=1))
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
    
    ax_sec.annotate('', xy=(sec_w/2 + 0.1, 0), xytext=(sec_w/2 + 0.1, t_actual), arrowprops=dict(arrowstyle='<->', color='#2c3e50'))
    ax_sec.text(sec_w/2 + 0.15, t_actual/2, f"t = {t_actual*100:.0f} cm", va='center', ha='left', fontweight='bold', fontsize=9)

    blueprint_text = f"Total Footing Dimensions: {B_ft:.2f} x {L_ft:.2f} m\n" \
                     f"Effective Depth d = {d_actual*100:.1f} cm\n\n" \
                     f"X-Axis Rebar: DB{bar_dia} @ {sp_main_x:.0f} cm ({n_main_bars_x} bars)\n" \
                     f"Y-Axis Rebar: DB{bar_dia} @ {sp_main_y:.0f} cm ({n_main_bars_y} bars)"
                     
    ax_sec.text(0, t_actual + 0.15, blueprint_text, ha='center', va='bottom', color='#2c3e50', fontsize=9, fontweight='bold', bbox=dict(boxstyle='round,pad=0.5', facecolor='#fcf3cf', alpha=0.5))
    
    ax_sec.set_xlim(-sec_w/2 - 0.5, sec_w/2 + 0.5)
    ax_sec.set_ylim(-0.5, t_actual + 0.6)
    ax_sec.set_aspect('equal')
    ax_sec.axis('off')
    ax_sec.set_title("Section View showing thickness and rebar arrangement", fontsize=11, fontweight='bold')
    st.pyplot(fig)

# =========================================================================
# INTERACTIVE MULTI-TAB MATRIX OUTPUTS
# =========================================================================
tab1, tab2, tab3 = st.tabs(["📝 Statics Safety Summary", "🌐 3D Solid Model Mesh", "📋 Calculations and Stress Values"])

with tab1:
    st.subheader("📋 Engineering Dimensions Summary")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1: st.metric("Maximum Total Width (B)", f"{B_ft:.2f} m")
    with col_m2: st.metric("Maximum Total Length (L)", f"{L_ft:.2f} m")
    with col_m3: st.metric("Total Footing Thickness (t)", f"{t_actual*100:.1f} cm")
    with col_m4: st.metric("Actual Footing Surface Area", f"{footing_area:.3f} sq.m")

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
    fig_3d.add_trace(create_3d_prism_trace(concrete_vertices, 0, t_actual, '#2ecc71', 0.6, 'Concrete Footing'))
    draw_3d_wireframe_lines(fig_3d, concrete_vertices, 0, t_actual, '#1e8449')

    column_vertices = [(-cx/2, -cy/2), (cx/2, -cy/2), (cx/2, cy/2), (-cx/2, cy/2)]
    fig_3d.add_trace(create_3d_prism_trace(column_vertices, t_actual, t_actual + 0.60, '#e74c3c', 0.85, 'Column'))
    draw_3d_wireframe_lines(fig_3d, column_vertices, t_actual, t_actual + 0.60, '#922b21')

    for idx, (px, py) in enumerate(piles_actual):
        segments_count = 8
        pile_nodes = [(px + (pile_size/2)*math.cos(s*2*math.pi/segments_count), py + (pile_size/2)*math.sin(s*2*math.pi/segments_count)) for s in range(segments_count)]
        fig_3d.add_trace(create_3d_prism_trace(pile_nodes, -1.5, embed_m, '#34495e', 0.8, 'As-Built Pile', show_legend=(idx == 0)))
        draw_3d_wireframe_lines(fig_3d, pile_nodes, -1.5, embed_m, '#2c3e50')

    fig_3d.update_layout(scene=dict(xaxis=dict(title='X (m)'), yaxis=dict(title='Y (m)'), zaxis=dict(title='Z (m)'), aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30))
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.subheader("📋 Ultimate Engineering Calculation Report")
    st.markdown("Design Standard Reference: **ACI 318-19 / DPT 1301/1302-61**")
    st.markdown("---")
    
    # =========================================================================
    # [CRITICAL FIX 1] Declare and calculate upstream critical geometric variables to prevent NameError
    # =========================================================================
    b1_box, b2_box = cx + d_actual, cy + d_actual
    b_0_len = 2 * (b1_box + b2_box)
    cut_y_pos = cy/2 + d_actual
    bw_y_width = get_triangular_width_at_y(cut_y_pos)
    
    # =========================================================================
    # [CRITICAL FIX 2] Separate total shear calculation (tons -> kg) outside f-string to prevent ValueError
    # =========================================================================
    # 1. Total Punching Shear (Considering only positive compressive forces)
    Vu_punch_kg = float(sum(max(0.0, float(p)) for p in p_ult_out)) * 1000.0
    
    # 2. Total Wide-Beam Shear (Considering only piles in the Y critical plane zone)
    Vu_wb_kg = 0.0
    for idx, p in enumerate(p_ult_out):
        if piles_actual[idx][1] >= cut_y_pos:
            Vu_wb_kg += max(0.0, float(p))
    Vu_wb_kg = Vu_wb_kg * 1000.0
    
    # Calculate Utilization Ratios (D/C Ratio) for status charts
    max_pile_s = max(pile_service_reactions)
    pile_ur = max_pile_s / pile_cap
    punching_ur = v_up / v_cp if v_cp > 0 else 1.0
    wide_beam_ur = v_uwb / v_cwb if v_cwb > 0 else 1.0
    
    # ---------------------------------------------------------------------
    # SECTION 1: EXECUTIVE SAFETY RATIO (D/C RATIO)
    # ---------------------------------------------------------------------
    st.markdown("#### 📊 1. Structural Performance and Capacity Utilization (Demand/Capacity Ratio)")
    
    col_ur1, col_ur2, col_ur3 = st.columns(3)
    with col_ur1:
        st.metric("Pile Load Capacity UR", f"{pile_ur*100:.1f}%", delta=f"{100 - pile_ur*100:.1f}% Margin", delta_color="inverse")
        st.progress(min(max(pile_ur, 0.0), 1.0))
    with col_ur2:
        st.metric("Punching Shear UR", f"{punching_ur*100:.1f}%", delta=f"{100 - punching_ur*100:.1f}% Margin", delta_color="inverse")
        st.progress(min(max(punching_ur, 0.0), 1.0))
    with col_ur3:
        st.metric("Wide-Beam Shear UR", f"{wide_beam_ur*100:.1f}%", delta=f"{100 - wide_beam_ur*100:.1f}% Margin", delta_color="inverse")
        st.progress(min(max(wide_beam_ur, 0.0), 1.0))

    st.markdown("---")

    # ---------------------------------------------------------------------
    # SECTION 2: PILE GROUP MECHANICS & DETAIL REACTION
    # ---------------------------------------------------------------------
    st.markdown("#### 🏗️ 2. Pile Group Mechanics and Stress Distribution")
    st.markdown(
        "Stress distribution analysis uses the **Rigid Foundation Method**, considering the actual eccentricity (As-Built Deviation), "
        "which shifts the relative center of gravity away from the column center."
    )
    
    st.markdown(
        r"$$\text{Governing Equation: } R_i = \frac{P_{total}}{n} \pm \frac{M_{y,total} \cdot x_i}{I_{yy}} \pm \frac{M_{x,total} \cdot y_i}{I_{xx}}$$"
    )
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown(f"""
        **Geometric Sectional Properties:**
        * Number of piles in group ($n$): `{n_piles}` piles
        * Group moment of inertia about X-axis ($I_{{xx}}$): `{I_xx_group:.4f}` m²
        * Group moment of inertia about Y-axis ($I_{{yy}}$): `{I_yy_group:.4f}` m²
        * Eccentricity of pile group CM from column center ($\\Delta X, \\Delta Y$): `({-ecc_x:.3f}, {-ecc_y:.3f})` m
        """)
    with col_v2:
        st.markdown(f"""
        **Combined External Forces and Bending Moments:**
        * Total axial service load ($P_{{service,total}}$): `{P_service_total:.2f}` tons
        * Total axial ultimate load ($P_{{ultimate,total}}$): `{(P_ultimate + 1.2*(w_s_footing + W_soil)):.2f}` tons
        * Total ultimate bending moment about X-axis ($M_{{u,x,total}}$): `{Mu_cx + (P_ultimate + 1.2*(w_s_footing + W_soil))*(-ecc_y):.2f}` ton-m
        * Total ultimate bending moment about Y-axis ($M_{{u,y,total}}$): `{Mu_cy + (P_ultimate + 1.2*(w_s_footing + W_soil))*(-ecc_x):.2f}` ton-m
        """)

    # Detailed pile results table
    pile_results_detailed = []
    for i in range(n_piles):
        p_status = "✅ Pass" if pile_service_reactions[i] <= pile_cap and pile_service_reactions[i] >= -pile_tension_cap else "❌ Overstressed"
        pile_results_detailed.append({
            "Pile Name": f"P{i+1}",
            "Actual X-Coord (m)": round(piles_relative[i][0], 3),
            "Actual Y-Coord (m)": round(piles_relative[i][1], 3),
            "Service Load (tons)": round(pile_service_reactions[i], 2),
            "Allowable Cap. (tons)": round(pile_cap, 2),
            "Ultimate Load (tons)": round(p_ult_out[i], 2),
            "Status": p_status
        })
    st.dataframe(pd.DataFrame(pile_results_detailed), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---------------------------------------------------------------------
    # SECTION 3: DETAILED SHEAR VERIFICATION (WITH SUBSTITUTION)
    # ---------------------------------------------------------------------
    st.markdown("#### 📐 3. Critical Shear Stress Analysis and Substitution")
    
    # Punching Shear Detail
    st.markdown("##### 📌 3.1 Punching Shear Validation")
    st.markdown(
        f"The critical section is located at a distance of $d/2 = {d_actual*100/2:.1f}$ cm from the column face, "
        f"resulting in a critical perimeter $b_0 = {b_0_len*100:.1f}$ cm."
    )
    st.markdown(
        f"$$\\text{{Substitution: }} v_u = \\frac{{V_u}}{{b_0 \\cdot d}} = \\frac{{{Vu_punch_kg:.1f} \\text{{ kg}}}}{{{b_0_len*100:.1f} \\text{{ cm}} \\times {d_actual*100:.1f} \\text{{ cm}}}} = {v_up:.2f} \\text{{ ksc}} \\le \\phi v_c = {v_cp:.2f} \\text{{ ksc}}$$"
    )
    if v_up <= v_cp:
        st.success(f"✅ **Safe:** The actual punching shear stress is below the concrete allowable capacity referencing the ACI 318 standard.")
    else:
        st.error(f"❌ **Unsafe:** Punching shear stress exceeds the standard limit. It is recommended to increase the footing thickness (t) or use a higher concrete grade.")

    # Wide-Beam Shear Detail
    st.markdown("##### 📌 3.2 Wide-Beam Shear Validation")
    st.markdown(
        f"The critical section is evaluated at the plane located at a distance $d = {d_actual*100:.1f}$ cm from the column face. "
        f"The concrete width at this section is $b_w = {bw_y_width*100:.1f}$ cm."
    )
    st.markdown(
        f"$$\\text{{Substitution: }} v_u = \\frac{{V_u}}{{b_w \\cdot d}} = \\frac{{{Vu_wb_kg:.1f} \\text{{ kg}}}}{{{bw_y_width*100:.1f} \\text{{ cm}} \\times {d_actual*100:.1f} \\text{{ cm}}}} = {v_uwb:.2f} \\text{{ ksc}} \\le \\phi v_c = {v_cwb:.2f} \\text{{ ksc}}$$"
    )
    if v_uwb <= v_cwb:
        st.success(f"✅ **Safe:** The wide-beam shear stress complies with safety requirements.")
    else:
        st.error(f"❌ **Unsafe:** The section is at risk of wide-beam shear failure.")

    st.markdown("---")

    # ---------------------------------------------------------------------
    # SECTION 4: REBAR REINFORCEMENT MATHEMATICS
    # ---------------------------------------------------------------------
    st.markdown("#### 📐 4. Flexural Design Parameters and Main Reinforcement Layout")
    st.markdown(
        "Reinforcement is calculated based on Ultimate Strength Design (USD), "
        "governed by a minimum temperature and shrinkage reinforcement ratio of $\\rho_{{min}} = 0.0018$."
    )
    
    df_rebar_matrix = pd.DataFrame({
        "Axis": ["X-Axis (Main Reinforcement)", "Y-Axis (Transverse Reinforcement)"],
        "Design Moment Mu (t-m)": [round(Mu_x_face, 2), round(Mu_y_face, 2)],
        "Effective Width b (cm)": [round(w_flex_x, 1), round(w_flex_y, 1)],
        "Required Rebar Area As (cm²)": [round(As_req_x, 2), round(As_req_y, 2)],
        "Provided Reinforcement": [f"{n_main_bars_x} - DB{bar_dia} bars", f"{n_main_bars_y} - DB{bar_dia} bars"],
        "Spacing": [f"Every {sp_main_x:.0f} cm c/c", f"Every {sp_main_y:.0f} cm c/c"],
        "Provided Rebar Area As (cm²)": [round(n_main_bars_x * ab_area, 2), round(n_main_bars_y * ab_area, 2)]
    })
    st.dataframe(df_rebar_matrix, use_container_width=True, hide_index=True)

    # Check development length
    st.markdown("##### 🔍 4.1 Development Length Check")
    l_d_required = (fy / (1.1 * 1.0 * math.sqrt(fc_prime))) * (bar_dia / 10)
    available_length_x = ((B_ft - cx) / 2) * 100 - concrete_cover_cm
    
    st.markdown(
        f" * Required critical tension development length ($L_d$): **{l_d_required:.1f} cm** "
        f" | Available concrete embedment length: **{available_length_x:.1f} cm**"
    )
    if available_length_x >= l_d_required:
        st.success("✅ **Pass:** The available concrete embedment length is sufficient for tension development of the main reinforcement. Standard 90-degree hooks are not required.")
    else:
        st.warning("⚠️ **Engineering Intervention:** The ends of the main reinforcement must be provided with **Standard 90-Degree Hooks** because the straight embedment length to the footing edge is insufficient.")
