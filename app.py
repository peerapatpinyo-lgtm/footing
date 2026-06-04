import streamlit as st
import math
import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
from matplotlib.path import Path
import plotly.graph_objects as go

# =========================================================================
# SYSTEM STABILITY & FONT MANAGEMENT
# =========================================================================
st.set_page_config(page_title="Enterprise Footing Suite V9.1 - Academic Engine", page_icon="📐", layout="wide")

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
# ADVANCED ENGINEERING SOLVER: WINKLER FOUNDATION & WOOD-ARMER (ITERATIVE)
# =========================================================================
def compute_flexible_reactions(vertices, piles_act, columns_list, P_total, M_x, M_y, t_actual, fc_prime, pile_ks, pile_tension_cap):
    x_coords = [v[0] for v in vertices]
    y_coords = [v[1] for v in vertices]
    xmin, xmax = min(x_coords), max(x_coords)
    ymin, ymax = min(y_coords), max(y_coords)
    
    margin = 0.05
    xmin -= margin; xmax += margin
    ymin -= margin; ymax += margin
    
    nx, ny = 20, 20
    dx = (xmax - xmin) / (nx - 1)
    dy = (ymax - ymin) / (ny - 1)
    
    fc_mpa = fc_prime * 0.0980665
    E_c_mpa = 4700 * math.sqrt(fc_mpa)
    E_concrete = E_c_mpa * 101.9716  
    nu = 0.15 
    D = (E_concrete * (t_actual**3)) / (12 * (1 - nu**2)) 
    
    poly_path = Path(vertices)
    active_nodes = []
    grid_to_global = {}
    node_idx = 0
    
    for i in range(nx):
        for j in range(ny):
            x = xmin + i * dx
            y = ymin + j * dy
            if poly_path.contains_point((x, y)) or poly_path.contains_point((x, y), radius=0.01):
                grid_to_global[(i, j)] = node_idx
                active_nodes.append((i, j, x, y))
                node_idx += 1
                
    M = len(active_nodes)
    if M == 0: return [P_total / max(1, len(piles_act))] * len(piles_act), 0.0, 0.0, 0.0
        
    factor_x = (D * dy) / (dx**3)
    factor_y = (D * dx) / (dy**3)
    factor_nu = (D * nu) / (dx * dy)
    factor_twist = (D * (1.0 - nu)) / (dx * dy)
    
    # ---------------------------------------------------------
    # [OPTIMIZATION] สร้าง Base Stiffness Matrix (K_base) และ Load (F_base) นอกลูป
    # ---------------------------------------------------------
    K_base = np.zeros((M, M))
    F_base = np.zeros(M)
    
    for j in range(ny):
        for i in range(1, nx - 1):
            g0, g1, g2 = grid_to_global.get((i-1, j)), grid_to_global.get((i, j)), grid_to_global.get((i+1, j))
            if all(g is not None for g in [g0, g1, g2]):
                for r, c in [(r,c) for r in range(3) for c in range(3)]:
                    K_base[[g0,g1,g2][r], [g0,g1,g2][c]] += [1.0, -2.0, 1.0][r] * [1.0, -2.0, 1.0][c] * factor_x
                    
    for i in range(nx):
        for j in range(1, ny - 1):
            g0, g1, g2 = grid_to_global.get((i, j-1)), grid_to_global.get((i, j)), grid_to_global.get((i, j+1))
            if all(g is not None for g in [g0, g1, g2]):
                for r, c in [(r,c) for r in range(3) for c in range(3)]:
                    K_base[[g0,g1,g2][r], [g0,g1,g2][c]] += [1.0, -2.0, 1.0][r] * [1.0, -2.0, 1.0][c] * factor_y

    for i in range(1, nx - 1):
        for j in range(1, ny - 1):
            g_mid, g_e, g_w, g_n, g_s = grid_to_global.get((i, j)), grid_to_global.get((i+1, j)), grid_to_global.get((i-1, j)), grid_to_global.get((i, j+1)), grid_to_global.get((i, j-1))
            if all(g is not None for g in [g_mid, g_e, g_w, g_n, g_s]):
                idx_x, idx_y = [g_w, g_mid, g_e], [g_s, g_mid, g_n]
                for r, c in [(r,c) for r in range(3) for c in range(3)]:
                    K_base[idx_x[r], idx_y[c]] += [1.0, -2.0, 1.0][r] * [1.0, -2.0, 1.0][c] * factor_nu

    for i in range(nx - 1):
        for j in range(ny - 1):
            g00, g10, g01, g11 = grid_to_global.get((i, j)), grid_to_global.get((i+1, j)), grid_to_global.get((i, j+1)), grid_to_global.get((i+1, j+1))
            if all(g is not None for g in [g00, g10, g01, g11]):
                idx = [g00, g10, g01, g11]
                for r, c in [(r,c) for r in range(4) for c in range(4)]:
                    K_base[idx[r], idx[c]] += [1.0, -1.0, -1.0, 1.0][r] * [1.0, -1.0, -1.0, 1.0][c] * factor_twist
    
    K_base += np.eye(M) * 1e-3
    
    pile_node_indices = []
    for px, py in piles_act:
        best_g = min(active_nodes, key=lambda n: (n[2]-px)**2 + (n[3]-py)**2)[0]
        pile_node_indices.append(best_g)

    for col_x, col_y in columns_list:
        best_i, best_j, _, _ = min(active_nodes, key=lambda n: (n[2]-col_x)**2 + (n[3]-col_y)**2)
        best_g = grid_to_global[(best_i, best_j)]
        F_base[best_g] += P_total / len(columns_list)
        
        g_n, g_s = grid_to_global.get((best_i, min(ny-1, best_j+1))), grid_to_global.get((best_i, max(0, best_j-1)))
        if g_n and g_s:
            F_base[g_n] += (M_x / len(columns_list)) / (2 * dy)
            F_base[g_s] -= (M_x / len(columns_list)) / (2 * dy)
            
        g_e, g_w = grid_to_global.get((min(nx-1, best_i+1), best_j)), grid_to_global.get((max(0, best_i-1), best_j))
        if g_e and g_w:
            F_base[g_e] += (M_y / len(columns_list)) / (2 * dx)
            F_base[g_w] -= (M_y / len(columns_list)) / (2 * dx)

    # ---------------------------------------------------------
    # Iterative Solver
    # ---------------------------------------------------------
    max_iter = 15
    active_piles = [True] * len(piles_act)
    w_disp = np.zeros(M)
    
    for iteration in range(max_iter):
        K = K_base.copy()
        F = F_base.copy()
        
        for idx, g_idx in enumerate(pile_node_indices):
            if active_piles[idx]:
                K[g_idx, g_idx] += pile_ks
                
        try: w_disp = np.linalg.solve(K, F)
        except np.linalg.LinAlgError: break
            
        state_changed = False
        for idx, g_idx in enumerate(pile_node_indices):
            r = w_disp[g_idx] * pile_ks if active_piles[idx] else 0.0
            if r < -pile_tension_cap and active_piles[idx]:
                active_piles[idx] = False
                state_changed = True
        if not state_changed: break 

    max_Mx_star, max_My_star, max_V_fdm = 0.0, 0.0, 0.0
    for g_idx, (i, j, x, y) in enumerate(active_nodes):
        g_mid, g_e, g_w, g_n, g_s = grid_to_global.get((i, j)), grid_to_global.get((i+1, j)), grid_to_global.get((i-1, j)), grid_to_global.get((i, j+1)), grid_to_global.get((i, j-1))
        g_ne, g_nw, g_se, g_sw = grid_to_global.get((i+1, j+1)), grid_to_global.get((i-1, j+1)), grid_to_global.get((i+1, j-1)), grid_to_global.get((i-1, j-1))
        
        if all(g is not None for g in [g_mid, g_e, g_w, g_n, g_s]):
            d2w_dx2 = (w_disp[g_e] - 2*w_disp[g_mid] + w_disp[g_w]) / (dx**2)
            d2w_dy2 = (w_disp[g_n] - 2*w_disp[g_mid] + w_disp[g_s]) / (dy**2)
            Mx, My = -D * (d2w_dx2 + nu * d2w_dy2), -D * (d2w_dy2 + nu * d2w_dx2)
            
            Mxy = 0.0
            if all(g is not None for g in [g_ne, g_nw, g_se, g_sw]):
                d2w_dxdy = (w_disp[g_ne] - w_disp[g_nw] - w_disp[g_se] + w_disp[g_sw]) / (4 * dx * dy)
                Mxy = -D * (1 - nu) * d2w_dxdy
                
            Mx_star, My_star = abs(Mx) + abs(Mxy), abs(My) + abs(Mxy)
            max_Mx_star, max_My_star = max(max_Mx_star, Mx_star/1000.0), max(max_My_star, My_star/1000.0)
            
            g_ee, g_ww, g_nn, g_ss = grid_to_global.get((i+2, j)), grid_to_global.get((i-2, j)), grid_to_global.get((i, j+2)), grid_to_global.get((i, j-2))
            if all(g is not None for g in [g_ee, g_ww, g_nn, g_ss, g_ne, g_nw, g_se, g_sw]):
                lap_e = (w_disp[g_ee] - 2*w_disp[g_e] + w_disp[g_mid])/(dx**2) + (w_disp[g_ne] - 2*w_disp[g_e] + w_disp[g_se])/(dy**2)
                lap_w = (w_disp[g_mid] - 2*w_disp[g_w] + w_disp[g_ww])/(dx**2) + (w_disp[g_nw] - 2*w_disp[g_w] + w_disp[g_sw])/(dy**2)
                lap_n = (w_disp[g_nw] - 2*w_disp[g_n] + w_disp[g_ne])/(dx**2) + (w_disp[g_nn] - 2*w_disp[g_n] + w_disp[g_mid])/(dy**2)
                lap_s = (w_disp[g_sw] - 2*w_disp[g_s] + w_disp[g_se])/(dx**2) + (w_disp[g_mid] - 2*w_disp[g_s] + w_disp[g_ss])/(dy**2)
                Vx, Vy = -D * (lap_e - lap_w)/(2*dx), -D * (lap_n - lap_s)/(2*dy)
                max_V_fdm = max(max_V_fdm, math.hypot(Vx, Vy))

    # [FIXED] ตัดการปรับสมดุล (Scale Factor) แบบ Manual ทิ้งไป เพื่อรักษาความถูกต้องตามสมการ Stiffness
    reactions = [w_disp[g_idx] * pile_ks if active_piles[idx] else 0.0 for idx, g_idx in enumerate(pile_node_indices)]
    
    return reactions, max_Mx_star, max_My_star, max_V_fdm

# =========================================================================
# HELPER FUNCTIONS 
# =========================================================================
def polygon_area(vertices):
    n = len(vertices)
    return abs(sum(vertices[i][0]*vertices[(i+1)%n][1] - vertices[(i+1)%n][0]*vertices[i][1] for i in range(n))) / 2.0

def compute_polygon_advanced_properties(vertices):
    n, area, cx_g, cy_g, Ixx, Iyy, Ixy = len(vertices), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    for i in range(n):
        j = (i + 1) % n
        factor = (vertices[i][0] * vertices[j][1]) - (vertices[j][0] * vertices[i][1])
        area += factor
        cx_g += (vertices[i][0] + vertices[j][0]) * factor
        cy_g += (vertices[i][1] + vertices[j][1]) * factor
        Ixx += (vertices[i][1]**2 + vertices[i][1]*vertices[j][1] + vertices[j][1]**2) * factor
        Iyy += (vertices[i][0]**2 + vertices[i][0]*vertices[j][0] + vertices[j][0]**2) * factor
        Ixy += (vertices[i][0]*vertices[j][1] + 2*vertices[i][0]*vertices[i][1] + 2*vertices[j][0]*vertices[j][1] + vertices[j][0]*vertices[i][1]) * factor
    area = abs(area / 2.0)
    if area < 1e-6: return 1.0, 0.0, 0.0, 1.0, 1.0, 0.0
    cx_g /= (6.0 * area); cy_g /= (6.0 * area)
    Ixx = abs(Ixx / 12.0) - area * cy_g**2
    Iyy = abs(Iyy / 12.0) - area * cx_g**2
    Ixy = abs(Ixy / 24.0) - area * cx_g * cy_g
    return area, cx_g, cy_g, max(0.001, Ixx), max(0.001, Iyy), Ixy

def get_polygon_section_width_at_y(target_y, vertices):
    intersections = []
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if (y1 <= target_y and y2 > target_y) or (y2 <= target_y and y1 > target_y):
            intersections.append(x1 + (target_y - y1) * (x2 - x1) / (y2 - y1))
    if len(intersections) >= 2:
        intersections.sort()
        return max(sum(intersections[i+1] - intersections[i] for i in range(0, len(intersections)-1, 2)), 0.01)
    return 0.01

def get_polygon_section_height_at_x(target_x, vertices):
    intersections = []
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if (x1 <= target_x and x2 > target_x) or (x2 <= target_x and x1 > target_x):
            intersections.append(y1 + (target_x - x1) * (y2 - y1) / (x2 - x1))
    if len(intersections) >= 2:
        intersections.sort()
        return max(sum(intersections[i+1] - intersections[i] for i in range(0, len(intersections)-1, 2)), 0.01)
    return 0.01

def compute_effective_depth(t_total, cover_cm, embed_cm, bar_dia_mm):
    return t_total - max(cover_cm / 100, embed_cm / 100) - ((bar_dia_mm / 1000) / 2)

def point_to_segment_dist(px, py, x1, y1, x2, y2):
    l2 = (x1 - x2)**2 + (y1 - y2)**2
    if l2 == 0: return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / l2))
    return math.hypot(px - (x1 + t*(x2 - x1)), py - (y1 + t*(y2 - y1)))

def calculate_b0_reduced_for_pile(px, py, pile_w, eval_d, vertices):
    n = len(vertices)
    min_dist = min([point_to_segment_dist(px, py, vertices[i][0], vertices[i][1], vertices[(i+1)%n][0], vertices[(i+1)%n][1]) for i in range(n)])
    crit_dist = (pile_w / 2) + (eval_d / 2)
    b0_standard = 4 * (pile_w + eval_d)
    if min_dist < crit_dist: return 3 * (pile_w + eval_d) if min_dist > pile_w / 2 else 2 * (pile_w + eval_d)
    return b0_standard

def get_dynamic_s_max(t_actual_m, env_condition):
    return min(3 * t_actual_m * 100, 45.0 if "กันน้ำ" not in env_condition and "กัดกร่อนสูง" not in env_condition else 30.0)

def evaluate_development_length(fy_ksc, fc_ksc, bar_dia_mm, available_length_m, cover_cm):
    ld_cm = max((fy_ksc / (2.1 * math.sqrt(fc_ksc))) * (bar_dia_mm / 10.0), 30.0)
    actual_available_cm = (available_length_m * 100) - cover_cm
    return actual_available_cm >= ld_cm, ld_cm, actual_available_cm

def evaluate_gergely_lutz_crack(Ms_ton_m, As_cm2, d_cm, cover_cm, bar_mm, spacing_cm):
    if Ms_ton_m <= 0 or As_cm2 <= 0: return 0.0
    fs_mpa = min((Ms_ton_m * 1000 * 100) / (As_cm2 * 0.85 * d_cm) * 0.0980665, 0.6 * 400.0)
    dc_mm = (cover_cm * 10.0) + (bar_mm / 2.0)
    s_mm = (spacing_cm * 10.0) if spacing_cm > 0 else 150.0
    return 11.0e-6 * 1.20 * fs_mpa * ((dc_mm * 2.0 * dc_mm * s_mm)**(1/3))

# =========================================================================
# ADVANCED SHEAR & REBAR DESIGN
# =========================================================================

def execute_shear_evaluation_routine(eval_d, eval_t, area, W_soil, P_ult, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles_act, piles_rel, piles_act, I_xx, I_yy, cx, cy, fc_prime, col_pos, vertices, factor_dl, columns_list, pile_dia=0.3, I_xy=0.0, phi_s=0.75, pile_ks=20000.0, pile_tension_cap=10.0):
    w_u_footing_weight = factor_dl * (area * eval_t * 2.4)
    w_u_soil_weight = factor_dl * W_soil
    P_total_factored = P_ult + w_u_footing_weight + w_u_soil_weight
    Mu_x_total, Mu_y_total = Mu_cx + (P_total_factored * (-ecc_y)), Mu_cy + (P_total_factored * (-ecc_x))
    
    p_ult_reactions, Mx_star, My_star, V_fdm = compute_flexible_reactions(vertices, piles_act, columns_list, P_total_factored, Mu_x_total, Mu_y_total, eval_t, fc_prime, pile_ks, pile_tension_cap)
        
    b_0_col = 2 * (cx + eval_d + cy + eval_d)
    A_punching_col_cm2 = b_0_col * eval_d * 10000
    V_u_punching_kg = sum(p_ult_reactions[idx] * 1000 for idx, (px, py) in enumerate(piles_act) if all(abs(px - col_x) > (cx/2 + eval_d/2) or abs(py - col_y) > (cy/2 + eval_d/2) for col_x, col_y in columns_list) and p_ult_reactions[idx] > 0)
    
    beta_ratio = max(cx, cy) / min(cx, cy) if min(cx, cy) > 0 else 1.0
    alpha_s = 40 if col_pos == "Interior" else (30 if col_pos == "Edge" else 20)
    v_u_col_punching_stress = V_u_punching_kg / A_punching_col_cm2 if A_punching_col_cm2 > 0 else 0.0
    v_c_allow_col_punching = phi_s * min(0.53 * (1 + 2 / beta_ratio) * math.sqrt(fc_prime), 0.27 * (alpha_s * (eval_d * 100) / (b_0_col * 100) + 2) * math.sqrt(fc_prime), 1.06 * math.sqrt(fc_prime))
    
    v_u_pile_punching_max = 0.0
    v_c_allow_pile_punching = phi_s * 1.06 * math.sqrt(fc_prime)
    for idx, (px, py) in enumerate(piles_act):
        if p_ult_reactions[idx] > 0:
            A_punch_pile_cm2 = calculate_b0_reduced_for_pile(px, py, pile_dia, eval_d, vertices) * eval_d * 10000
            if A_punch_pile_cm2 > 0: v_u_pile_punching_max = max(v_u_pile_punching_max, (p_ult_reactions[idx] * 1000) / A_punch_pile_cm2)

    # --- เช็ก One-Way Shear (Beam Shear) ในแนวแกน Y (รอยตัดแนวตั้ง) ---
    cut_y_top = cy/2 + eval_d
    bw_top = get_polygon_section_width_at_y(cut_y_top, vertices) * 100
    v_u_wb_top_stress = sum(r * 1000 for r, (px, py) in zip(p_ult_reactions, piles_act) if py >= cut_y_top and r > 0) / (bw_top * eval_d * 100) if bw_top > 0 else 0

    cut_y_bot = -(cy/2 + eval_d)
    bw_bot = get_polygon_section_width_at_y(cut_y_bot, vertices) * 100
    v_u_wb_bot_stress = sum(r * 1000 for r, (px, py) in zip(p_ult_reactions, piles_act) if py <= cut_y_bot and r > 0) / (bw_bot * eval_d * 100) if bw_bot > 0 else 0
    
    # --- [เพิ่มใหม่] เช็ก One-Way Shear (Beam Shear) ในแนวแกน X (รอยตัดแนวนอน) ---
    cut_x_right = cx/2 + eval_d
    bw_right = get_polygon_section_height_at_x(cut_x_right, vertices) * 100
    v_u_wb_right_stress = sum(r * 1000 for r, (px, py) in zip(p_ult_reactions, piles_act) if px >= cut_x_right and r > 0) / (bw_right * eval_d * 100) if bw_right > 0 else 0

    cut_x_left = -(cx/2 + eval_d)
    bw_left = get_polygon_section_height_at_x(cut_x_left, vertices) * 100
    v_u_wb_left_stress = sum(r * 1000 for r, (px, py) in zip(p_ult_reactions, piles_act) if px <= cut_x_left and r > 0) / (bw_left * eval_d * 100) if bw_left > 0 else 0
    
    # นำผลรวมแกน X และ Y มาประเมินหาค่าวิกฤตที่สูงสุด
    v_u_wb_fdm_stress = V_fdm / (max(cx, cy) * 100 * eval_d * 100) if max(cx, cy) > 0 else 0
    v_u_wb_max = max(v_u_wb_top_stress, v_u_wb_bot_stress, v_u_wb_right_stress, v_u_wb_left_stress, v_u_wb_fdm_stress * 0.7) 
    v_c_allow_wb = phi_s * 0.53 * math.sqrt(fc_prime)
    
    is_safe = (v_u_col_punching_stress <= v_c_allow_col_punching) and (v_u_pile_punching_max <= v_c_allow_pile_punching) and (v_u_wb_max <= v_c_allow_wb)
    return is_safe, v_u_col_punching_stress, v_c_allow_col_punching, v_u_pile_punching_max, v_c_allow_pile_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions, Mx_star, My_star, V_fdm
    
def design_rebar_by_axis(Mu_ton_m, width_cm, d_cm, t_cm, fc_prime, fy, phi_flex, ab_area, cover_cm, env_cond="ทั่วไป"):
    width_cm = max(width_cm, 30.0)
    rho_min = max(0.8 * math.sqrt(fc_prime) / fy, 14.0 / fy)
    As_min = rho_min * width_cm * d_cm
    cover_deduction = cover_cm * 2 
    s_max = get_dynamic_s_max(t_cm / 100, env_cond)

    if Mu_ton_m <= 0 or d_cm <= 0:
        n_bars = max(math.ceil(As_min / ab_area), 4)
        return n_bars, min(math.floor((width_cm - cover_deduction) / (n_bars - 1)) if n_bars > 1 else 15, s_max), False, As_min
        
    Rn = (Mu_ton_m * 1000 * 100) / (phi_flex * width_cm * d_cm**2)
    val_sqrt = 1 - (2 * Rn) / (0.85 * fc_prime)
    if val_sqrt < 0: return 0, 0, True, 0.0
    
    As_req = max((0.85 * fc_prime / fy) * (1 - math.sqrt(val_sqrt)) * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 4)
    return n_bars, min(math.floor((width_cm - cover_deduction) / (n_bars - 1)) if n_bars > 1 else 15, s_max), False, As_req

# =========================================================================
# VISUALIZATION FUNCTIONS 
# =========================================================================
def generate_2d_plan_view(vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l, columns_list, cg_x, cg_y):
    fig, ax = plt.subplots(figsize=(6, 6))
    x_v, y_v = [v[0] for v in vertices] + [vertices[0][0]], [v[1] for v in vertices] + [vertices[0][1]]
    ax.plot(x_v, y_v, '-', color='#1e8449', linewidth=2.5, label='ขอบเขตฐานราก')
    ax.fill(x_v, y_v, color='#2ecc71', alpha=0.15)
    
    for c_idx, (col_x, col_y) in enumerate(columns_list):
        ax.add_patch(patches.Rectangle((col_x - cx/2, col_y - cy/2), cx, cy, linewidth=2, edgecolor='#922b21', facecolor='#e74c3c', alpha=0.7, label='เสาตอม่อ' if c_idx==0 else ""))
    for i, (px, py) in enumerate(piles_actual):
        patch = patches.Circle((px, py), pile_w/2, linewidth=1.5, edgecolor='#2c3e50', facecolor='#34495e', alpha=0.6) if pile_shape == "Circular Pile" else patches.Rectangle((px - pile_w/2, py - pile_l/2), pile_w, pile_l, linewidth=1.5, edgecolor='#2c3e50', facecolor='#34495e', alpha=0.6)
        ax.add_patch(patch)
        ax.text(px, py, f"P{i+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
        
    ax.plot(cg_x, cg_y, 'X', color='#e67e22', markersize=10, label=f'C.G. เข็มเยื้องจริง ({cg_x:.2f}, {cg_y:.2f})')
    ax.plot([0, cg_x], [0, cg_y], ':', color='#d35400', linewidth=1.5)
    ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
    ax.axvline(0, color='black', linewidth=0.5, linestyle='--')
    ax.set(xlabel='พิกัด X (ม.)', ylabel='พิกัด Y (ม.)', title='แปลน As-Built Mapping & Eccentricity')
    ax.axis('equal'); ax.grid(True, linestyle=':', alpha=0.6); ax.legend(loc='upper right', fontsize=8)
    return fig

def generate_rebar_detailing_view(t_actual, b_max, cover_cm, embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_aspect('equal') 
    c_m, e_m, d_m = cover_cm / 100, embed_cm / 100, bar_dia / 1000
    hook_len = min(0.30, max(0.15, t_actual - 2*c_m - e_m))
    
    ax.add_patch(patches.Rectangle((-b_max/2, 0), b_max, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded'))
    ax.add_patch(patches.Rectangle((-cx/2, t_actual), cx, 0.40, linewidth=2, edgecolor='#7e1e1e', facecolor='#f2d7d5'))
    ax.add_patch(patches.Rectangle((-b_max/3 - 0.15, -0.2), 0.3, 0.2 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5))
    ax.add_patch(patches.Rectangle((b_max/3 - 0.15, -0.2), 0.3, 0.2 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5))
    
    bot_z_x, bot_z_y, left_x, right_x = e_m + c_m + (d_m/2), e_m + c_m + (d_m/2) + d_m, -b_max/2 + c_m, b_max/2 - c_m
    ax.plot([left_x, right_x], [bot_z_x, bot_z_x], color='#c0392b', linewidth=2.5, label=f'เหล็กล่าง DB{bar_dia}')
    ax.plot([left_x, left_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=2.5)
    ax.plot([right_x, right_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=2.5)
    
    x_dots = np.linspace(left_x + c_m, right_x - c_m, min(n_bars_x, 15))
    for rx in x_dots: ax.plot(rx, bot_z_y, 'o', color='#2c3e50', markersize=4)
        
    if require_top_steel:
        top_z_x, top_z_y = t_actual - c_m - (d_m/2), t_actual - c_m - (d_m/2) - d_m
        ax.plot([left_x, right_x], [top_z_x, top_z_x], color='#2980b9', linewidth=2, label='เหล็กบน (กันร้าว/รับแรงถอน)')
        ax.plot([left_x, left_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2)
        ax.plot([right_x, right_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2)
        for rx in x_dots: ax.plot(rx, top_z_y, 'o', color='#34495e', markersize=3.5)

    dowel_left, dowel_right, dowel_bot_z = -cx/2 + 0.05, cx/2 - 0.05, bot_z_y + d_m
    ax.plot([dowel_left, dowel_left], [dowel_bot_z, t_actual + 0.5], color='#d35400', linewidth=2, label='เหล็กเดือยตอม่อ (Dowel Bars)')
    ax.plot([dowel_right, dowel_right], [dowel_bot_z, t_actual + 0.5], color='#d35400', linewidth=2)
    ax.plot([dowel_left, dowel_left + 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2)
    ax.plot([dowel_right, dowel_right - 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2)

    ax.text(-b_max/2 - 0.1, bot_z_x, f'Cov. {cover_cm}cm', ha='right', fontsize=8)
    ax.text(-b_max/3 + 0.15, e_m/2, f'Embed. {embed_cm}cm', va='center', fontsize=8)
    ax.text(0, -0.3, f'B_max = {b_max:.2f} m', ha='center', fontsize=10, fontweight='bold')
    ax.text(right_x + 0.1, t_actual/2, f't = {t_actual:.2f} m', fontsize=9, fontweight='bold', va='center')
    ax.set_xlim(-b_max/2 - 0.4, b_max/2 + 0.4); ax.set_ylim(-0.4, t_actual + 0.6)
    ax.set_title(f'รูปขยายการจัดเหล็กเสริม ({n_bars_x}-DB{bar_dia} @ {sp_x:.0f} cm)', fontsize=11, fontweight='bold')
    ax.axis('off'); ax.legend(loc='upper right', fontsize=8, framealpha=0.8)
    return fig

@st.cache_data(show_spinner=False)
def generate_3d_mesh(concrete_vertices_tuple, t_actual, cx, cy, piles_actual_tuple, pile_shape, pile_w, pile_l, embed_m, columns_list_tuple):
    concrete_vertices = list(concrete_vertices_tuple)
    piles_actual = list(piles_actual_tuple)
    columns_list = list(columns_list_tuple)
    
    def create_3d_prism_trace(vertices, z_start, z_end, face_color, opacity, name, show_legend=True):
        n = len(vertices)
        x_coords, y_coords, z_coords = [v[0] for v in vertices] * 2, [v[1] for v in vertices] * 2, [z_start] * n + [z_end] * n
        i_idx, j_idx, k_idx = [], [], []
        for idx in range(1, n - 1): 
            i_idx.append(0); j_idx.append(idx); k_idx.append(idx + 1)
            i_idx.append(n); j_idx.append(n + idx + 1); k_idx.append(n + idx)
        for idx in range(n):
            next_idx = (idx + 1) % n
            i_idx.extend([idx, idx]); j_idx.extend([next_idx, n + next_idx]); k_idx.extend([n + next_idx, n + idx])
        return go.Mesh3d(x=x_coords, y=y_coords, z=z_coords, i=i_idx, j=j_idx, k=k_idx, color=face_color, opacity=opacity, name=name, showlegend=show_legend, lighting=dict(ambient=0.6, diffuse=0.8, roughness=0.4, specular=0.3, fresnel=0.2))

    fig_3d = go.Figure()
    footing_bottom_z = -t_actual
    pile_top_z, pile_bottom_z = footing_bottom_z + embed_m, footing_bottom_z - 0.8 
    
    fig_3d.add_trace(create_3d_prism_trace(concrete_vertices, footing_bottom_z, 0, '#2ecc71', 0.45, 'คอนกรีตฐานราก'))
    for col_x, col_y in columns_list:
        fig_3d.add_trace(create_3d_prism_trace([(col_x-cx/2, col_y-cy/2), (col_x+cx/2, col_y-cy/2), (col_x+cx/2, col_y+cy/2), (col_x-cx/2, col_y+cy/2)], 0, 0.40, '#e74c3c', 0.75, 'เสาตอม่อ', show_legend=False))
    
    for index, p in enumerate(piles_actual):
        px, py = p[0], p[1]
        pile_verts = [(px + (pile_w/2)*math.cos(a), py + (pile_w/2)*math.sin(a)) for a in np.linspace(0, 2*np.pi, 8, endpoint=False)] if pile_shape == "Circular Pile" else [(px-pile_w/2, py-pile_l/2), (px+pile_w/2, py-pile_l/2), (px+pile_w/2, py+pile_l/2), (px-pile_w/2, py+pile_l/2)]
        fig_3d.add_trace(create_3d_prism_trace(pile_verts, pile_bottom_z, pile_top_z, '#7f8c8d', 0.8, f'เสาเข็ม P{index+1}', show_legend=False))
        fig_3d.add_trace(go.Scatter3d(x=[px], y=[py], z=[pile_top_z + 0.05], mode='text', text=[f"P{index+1}"], textposition="top center", textfont=dict(color='black', size=10, family="sans-serif"), showlegend=False))

    fig_3d.update_layout(scene=dict(xaxis_title='แกน X (ม.)', yaxis_title='แกน Y (ม.)', zaxis_title='แกน Z (ม.)', aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30))
    return fig_3d

# =========================================================================
# APPLICATION LAYOUT & UI 
# =========================================================================
with st.sidebar:
    st.header("🏗️ ข้อมูลการออกแบบฐานรากตอม่อ V9.1")
    footing_shape_type = st.selectbox("รูปทรงเรขาคณิตและชนิดฐานราก:", ["Truncated Triangular Footing", "Rectangular Footing", "Combined Footing (>= 2 Columns)", "Strap Footing (ชิดเขต)", "Arbitrary Freeform Polygon"], index=0)
    col_position = st.selectbox("ตำแหน่งเสาตอม่อ (Column Position):", ["Interior", "Edge", "Corner"], index=0)
    
    st.subheader("🧱 คุณสมบัติวัสดุ & หน้าตัดตอม่อ")
    fc_prime = st.number_input("กำลังอัดคอนกรีต fc' (ksc)", value=280, min_value=150, step=10)
    fy = st.number_input("กำลังรับแรงดึงเหล็กเสริม fy (ksc)", value=4000, min_value=2400, step=100)
    cx = st.number_input("ขนาดตอม่อแกน X - cx (ม.)", value=0.35, min_value=0.10, step=0.05)
    cy = st.number_input("ขนาดตอม่อแกน Y - cy (ม.)", value=0.35, min_value=0.10, step=0.05)

    st.subheader("🛠️ User-Defined Load Factors")
    factor_dl = st.number_input("γ_DL (Dead Load Factor)", value=1.2, step=0.1)
    factor_ll = st.number_input("γ_LL (Live Load Factor)", value=1.6, step=0.1)
    
    st.subheader("🌪️ แรงเฉือนแนวราบ & แผ่นดินไหว")
    V_x = st.number_input("แรงเฉือนระดับแนวราบ V_x (ตัน)", value=0.0)
    V_y = st.number_input("แรงเฉือนระดับแนวราบ V_y (ตัน)", value=0.0)
    T_z = st.number_input("แรงบิดหมุนที่หัวเสา T_z (ตัน-เมตร)", value=0.0)

    st.subheader("💧 การควบคุมความกว้างรอยร้าว")
    env_condition = st.selectbox("สภาวะการใช้งานควบคุมรอยร้าว:", ["ทั่วไป (สภาวะปกติ - Max 0.30mm)", "โครงสร้างกันน้ำ / กัดกร่อนสูง (Max 0.15mm)"])
    w_allowable = 0.15 if "โครงสร้างกันน้ำ" in env_condition else 0.30

    st.subheader("1. การตั้งค่าเสาเข็มและพิกัด As-Built")
    pile_shape = st.selectbox("รูปทรงเสาเข็ม:", ["Circular Pile", "Square/Rectangular Pile"], index=0)
    pile_dia = st.number_input("เส้นผ่านศูนย์กลาง/กว้างเสาเข็ม (ม.)", value=0.30, min_value=0.15)
    pile_w = pile_dia; pile_l = pile_dia 
    
    pile_cap = st.number_input("กำลังรับแรงอัดที่ปลอดภัย (ตัน/ต้น)", value=30.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนที่ปลอดภัย (ตัน/ต้น)", value=10.0)
    pile_ks = st.number_input("ความแข็งแรงสปริงเสาเข็ม k_s (ตัน/ม.)", value=20000.0, step=1000.0)
    
    S_dist, E_dist, columns_list, I_xy_geom = 3.0 * pile_w, 0.40, [(0.0, 0.0)], 0.0
    
    if footing_shape_type == "Truncated Triangular Footing":
        n_piles = 3
        piles_ideal = [(0, S_dist / math.sqrt(3)), (-S_dist / 2, -S_dist / (2 * math.sqrt(3))), (S_dist / 2, -S_dist / (2 * math.sqrt(3)))]
        R_top, Y_bot, X_side, trunc = (S_dist / math.sqrt(3)) + E_dist, -(S_dist / (2 * math.sqrt(3))) - E_dist, (S_dist / 2) + E_dist, 0.20
        concrete_vertices_base = [(-trunc, R_top), (trunc, R_top), (X_side, Y_bot + trunc), (X_side - trunc, Y_bot), (-X_side + trunc, Y_bot), (-X_side, Y_bot + trunc)]
        B_max_visual = X_side * 2
    elif footing_shape_type == "Rectangular Footing":
        n_piles = st.selectbox("จำนวนเสาเข็มในกลุ่ม:", [2, 4, 5, 6, 8, 9], index=1)
        if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
        elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
        else: piles_ideal = [(0,0)] * n_piles 
        B_ft, L_ft = S_dist + 2*E_dist, S_dist + 2*E_dist
        concrete_vertices_base = [(-B_ft/2, -L_ft/2), (B_ft/2, -L_ft/2), (B_ft/2, L_ft/2), (-B_ft/2, L_ft/2)]
        B_max_visual = B_ft
    elif footing_shape_type == "Combined Footing (>= 2 Columns)":
        n_piles = 6
        piles_ideal = [(-1.2, -0.6), (0.0, -0.6), (1.2, -0.6), (-1.2, 0.6), (0.0, 0.6), (1.2, 0.6)]
        columns_list = [(-1.0, 0.0), (1.0, 0.0)]
        concrete_vertices_base = [(-2.0, -1.2), (2.0, -1.2), (2.0, 1.2), (-2.0, 1.2)]
        B_max_visual = 4.0
    elif footing_shape_type == "Strap Footing (ชิดเขต)":
        n_piles, piles_ideal = 4, [(-1.5, -0.5), (-1.5, 0.5), (1.5, -0.5), (1.5, 0.5)]
        columns_list, concrete_vertices_base = [(-1.8, 0.0), (1.5, 0.0)], [(-2.3, -1.0), (2.3, -1.0), (2.3, 1.0), (-2.3, 1.0)]
        B_max_visual = 4.6
    else: 
        n_piles = st.number_input("จำนวนเสาเข็มสำหรับฐานรากอิสระ (ต้น)", value=4, min_value=1, max_value=20, step=1)
        piles_ideal = []
        cols_grid, rows_grid = math.ceil(math.sqrt(n_piles)), math.ceil(n_piles / math.ceil(math.sqrt(n_piles)))
        idx_p = 0
        for r in range(rows_grid):
            for c in range(cols_grid):
                if idx_p < n_piles:
                    piles_ideal.append(((c - (cols_grid - 1)/2) * 0.9, (r - (rows_grid - 1)/2) * 0.9))
                    idx_p += 1
        st.write("🔧 แก้ไขพิกัดจุดยอดของฐานราก (ทวนเข็มนาฬิกา):")
        if "poly_vertices" not in st.session_state:
            st.session_state.poly_vertices = pd.DataFrame({'X (ม.)': [-1.5, 0.5, 0.5, 1.5, 1.5, -1.5], 'Y (ม.)': [1.5, 1.5, -0.5, -0.5, -1.5, -1.5]})
        edited_v_df = st.data_editor(st.session_state.poly_vertices, num_rows="dynamic", use_container_width=True, key="poly_v_editor_key")
        st.session_state.poly_vertices = edited_v_df
        concrete_vertices_base = list(zip(edited_v_df['X (ม.)'], edited_v_df['Y (ม.)']))
        if len(concrete_vertices_base) < 3: st.error("❌ รูปทรงต้องมีอย่างน้อย 3 จุด"); st.stop()
        _, _, _, _, _, I_xy_geom = compute_polygon_advanced_properties(concrete_vertices_base)
        B_max_visual = max([v[0] for v in concrete_vertices_base]) - min([v[0] for v in concrete_vertices_base]) if concrete_vertices_base else 3.0

    st.subheader("3. นน.บรรทุกตอม่อและวัสดุ")
    DL, LL = st.number_input("Dead Load (ตัน)", value=55.0), st.number_input("Live Load (ตัน)", value=30.0)
    Mcx_dl, Mcy_dl, Mcx_ll, Mcy_ll = 6.0, 5.0, 4.0, 3.0
    soil_depth, soil_density = 1.0, 1.8
    bar_dia = st.selectbox("ขนาดเหล็กแกน DB (มม.)", [12, 16, 20, 25, 28, 32], index=2)
    
    thickness_mode = st.radio("โหมดกำหนดความหนา t:", ["Auto-Optimize", "Manual Override"])
    manual_t = st.number_input("กำหนดความหนาฐานราก t (ม.)", value=0.65, min_value=0.30) if thickness_mode == "Manual Override" else 0.65
    pile_embed_cm, concrete_cover_cm = 5.0, 7.5

phi_shear, phi_flexure, ab_area = 0.75, 0.90, (math.pi * (bar_dia / 10) ** 2) / 4 

# =========================================================================
# MAIN DATA PROCESSING FLOW 
# =========================================================================
st.markdown("### 📍 1. การวิเคราะห์ As-Built Field Survey เข็มตอม่อ (Advanced Academic FDM)")
st.info("💡 **Academic Engine:** จำลองพฤติกรรม FDM Energy Plate พร้อมตรวจสอบ Wood-Armer, 3rd Derivative Shear และ Non-linear Lift-off")

if "prev_footing" not in st.session_state or st.session_state.prev_footing != footing_shape_type or st.session_state.prev_piles != n_piles:
    st.session_state.prev_footing, st.session_state.prev_piles = footing_shape_type, n_piles
    st.session_state.pile_data = pd.DataFrame({'ชื่อเข็ม': [f"P{i+1}" for i in range(n_piles)], 'Ideal X (ม.)': [round(p[0], 3) for p in piles_ideal], 'Ideal Y (ม.)': [round(p[1], 3) for p in piles_ideal], 'ΔX (ม.) - หน้างาน': [0.00] * n_piles, 'ΔY (ม.) - หน้างาน': [0.00] * n_piles})

edited_df = st.data_editor(st.session_state.pile_data, disabled=['ชื่อเข็ม', 'Ideal X (ม.)', 'Ideal Y (ม.)'], hide_index=True, use_container_width=True, key="static_piles_editor_key")
st.session_state.pile_data = edited_df

piles_actual = [(row['Ideal X (ม.)'] + row['ΔX (ม.) - หน้างาน'], row['Ideal Y (ม.)'] + row['ΔY (ม.) - หน้างาน']) for _, row in edited_df.iterrows()]
cg_actual_x, cg_actual_y = sum(p[0] for p in piles_actual)/n_piles, sum(p[1] for p in piles_actual)/n_piles
ecc_x, ecc_y = cg_actual_x, cg_actual_y
piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group, I_xx_group = max(0.001, sum(p[0]**2 for p in piles_relative)), max(0.001, sum(p[1]**2 for p in piles_relative))

P_ultimate = (factor_dl * DL) + (factor_ll * LL)
Mu_cx, Mu_cy = (factor_dl * Mcx_dl) + (factor_ll * Mcx_ll), (factor_dl * Mcy_dl) + (factor_ll * Mcy_ll)
Ms_cx, Ms_cy = Mcx_dl + Mcx_ll, Mcy_dl + Mcy_ll
concrete_vertices = [(v[0] - ecc_x, v[1] - ecc_y) for v in concrete_vertices_base]

poly_path_check = Path(concrete_vertices)
outside_piles = [f"P{idx+1}" for idx, p in enumerate(piles_actual) if not (poly_path_check.contains_point(p) or poly_path_check.contains_point(p, radius=0.01))]
if outside_piles: st.error(f"🚨 **Engineering Validation Failed:** เสาเข็ม `{', '.join(outside_piles)}` หลุดออกไปนอกแนวขอบของฐานราก!")

footing_area = polygon_area(concrete_vertices)
W_soil = max(0.0, footing_area - (cx*cy)) * soil_depth * soil_density

if thickness_mode == "Auto-Optimize":
    d_opt, safe, max_loops = 0.30, False, int((3.0 - 0.30) / 0.02) + 10 
    for _ in range(max_loops):
        t_opt = d_opt + max(concrete_cover_cm/100, pile_embed_cm/100) + ((bar_dia/1000)/2)
        safe, v_up_col, v_cp_col, v_up_pile, v_cp_pile, v_uwb, v_cwb, p_ult_out, Mu_x_max_fdm, Mu_y_max_fdm, V_fdm = execute_shear_evaluation_routine(
            d_opt, t_opt, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, columns_list, pile_dia=pile_w, I_xy=I_xy_geom, pile_ks=pile_ks, pile_tension_cap=pile_tension_cap)
        if safe: break
        d_opt += 0.02
    if not safe: st.error("🚨 วิกฤต: ไม่สามารถหาความหนาฐานรากที่ปลอดภัยได้"); st.stop() 
    t_actual = math.ceil(t_opt * 20) / 20; d_actual = d_opt
    safe, v_up_col, v_cp_col, v_up_pile, v_cp_pile, v_uwb, v_cwb, p_ult_out, Mu_x_max_fdm, Mu_y_max_fdm, V_fdm = execute_shear_evaluation_routine(
        d_actual, t_actual, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, columns_list, pile_dia=pile_w, I_xy=I_xy_geom, pile_ks=pile_ks, pile_tension_cap=pile_tension_cap)
else:
    t_actual = manual_t
    d_actual = compute_effective_depth(t_actual, concrete_cover_cm, pile_embed_cm, bar_dia)
    safe, v_up_col, v_cp_col, v_up_pile, v_cp_pile, v_uwb, v_cwb, p_ult_out, Mu_x_max_fdm, Mu_y_max_fdm, V_fdm = execute_shear_evaluation_routine(
        d_actual, t_actual, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, columns_list, pile_dia=pile_w, I_xy=I_xy_geom, pile_ks=pile_ks, pile_tension_cap=pile_tension_cap)

# Global Variables for Report
w_u_footing = factor_dl * (footing_area * t_actual * 2.4)
w_u_soil = factor_dl * W_soil
P_u_total = P_ultimate + w_u_footing + w_u_soil
polar_R_sum = max(sum(prx**2 + pry**2 for prx, pry in piles_relative), 1.0)
pile_horizontal_shear = [math.hypot((V_x / n_piles) - (T_z * pry / polar_R_sum), (V_y / n_piles) + (T_z * prx / polar_R_sum)) for prx, pry in piles_relative]

P_service_total = DL + LL + (footing_area * t_actual * 2.4) + W_soil
pile_service_reactions, Ms_x_max_fdm, Ms_y_max_fdm, _ = compute_flexible_reactions(concrete_vertices, piles_actual, columns_list, P_service_total, Ms_cx + P_service_total*ecc_y, Ms_cy + P_service_total*ecc_x, t_actual, fc_prime, pile_ks, pile_tension_cap)

has_tension = any(r < 0 for r in p_ult_out)
require_top_steel = has_tension or (t_actual >= 0.60) 

w_flex_x = get_polygon_section_width_at_y(0, concrete_vertices) * 100
n_bars_x, sp_x, _, as_req_x = design_rebar_by_axis(Mu_x_max_fdm, w_flex_x, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area, concrete_cover_cm, env_cond=env_condition)

w_flex_y = min(get_polygon_section_height_at_x(-cx/2.0, concrete_vertices), get_polygon_section_height_at_x(cx/2.0, concrete_vertices)) * 100
n_bars_y, sp_y, _, as_req_y = design_rebar_by_axis(Mu_y_max_fdm, w_flex_y, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area, concrete_cover_cm, env_cond=env_condition)

calculated_w = evaluate_gergely_lutz_crack(Ms_x_max_fdm, n_bars_x * ab_area, d_actual*100, concrete_cover_cm, bar_dia, sp_x)

st.markdown("---")

# =========================================================================
# DISPLAY & INTERFACE REPORT WITH NEW CALCULATION SHEET TAB
# =========================================================================
tab_report, tab_calc, tab_visuals = st.tabs([
    "📊 2. รายงานผลสรุป (Summary)", 
    "📄 3. รายการคำนวณละเอียด (Step-by-Step Calc)", 
    "🗺️ 4. Engineering Visual Twin (2D/3D)"
])

with tab_report:
    tension_warnings = [f"P{idx+1} (แรงถอน {abs(r_s):.2f} ตัน)" for idx, r_s in enumerate(pile_service_reactions) if r_s < 0 and abs(r_s) > pile_tension_cap]
    if tension_warnings: st.error(f"🚨 **อันตราย!** มีเสาเข็มรับแรงถอนเกินค่าพิกัด ({pile_tension_cap} ตัน/ต้น): {', '.join(tension_warnings)}")
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.write("**Factored Loads & Geometries**")
        st.write(f"* พื้นที่หน้าตัดฐานรากประมวลผลจริง: `{footing_area:.2f}` ตร.ม.")
        st.write(f"* P_u_total (รวมนน.ดิน+ฐานราก): `{P_u_total:.2f}` ตัน")
        st.write(f"**สมรรถนะการควบคุมรอยร้าว & พฤติกรรมโครงสร้าง**")
        st.write(f"* ความกว้างรอยร้าวผิวคอนกรีต: `{calculated_w:.3f}` มม. (ขีดจำกัด: `{w_allowable}` มม.)")
        if calculated_w <= w_allowable: st.success("✅ Crack Width Control: Passed")
        else: st.error("❌ Crack Width Control: Exceeded")
            
        st.write(f"**Flexural Design (ใช้ค่า Wood-Armer Moments $M_x^*, M_y^*$)**")
        st.write(f"* แกน X (Mu_x* = {Mu_x_max_fdm:.2f} t-m): ใช้ `{n_bars_x}-DB{bar_dia} @ {sp_x:.0f} cm`")
        st.write(f"* แกน Y (Mu_y* = {Mu_y_max_fdm:.2f} t-m): ใช้ `{n_bars_y}-DB{bar_dia} @ {sp_y:.0f} cm`")
        
        st.write(f"**Shear Check (d = {d_actual:.2f} m)**")
        st.write(f"* v_up (Punching เสาตอม่อ): `{v_up_col:.2f}` KSC (≤ {v_cp_col:.2f}) [{'✅ Safe' if v_up_col <= v_cp_col else '❌ Overstressed'}]")
        st.write(f"* v_up (Punching เสาเข็ม): `{v_up_pile:.2f}` KSC (≤ {v_cp_pile:.2f}) [{'✅ Safe' if v_up_pile <= v_cp_pile else '❌ Overstressed'}]")
        st.write(f"* v_uwb (Wide-beam): `{v_uwb:.2f}` KSC (≤ {v_cwb:.2f}) [{'✅ Safe' if v_uwb <= v_cwb else '❌ Overstressed'}]")

    with col_res2:
        st.write("**ตารางสรุปผลแรงปฏิกิริยาหัวเสาเข็มรอบทิศทาง**")
        df_react = pd.DataFrame({'ชื่อเข็ม': st.session_state.pile_data['ชื่อเข็ม'], 'R_u (ดิ่ง-ตัน)': p_ult_out, 'R_s (ดิ่งใช้งาน-ตัน)': pile_service_reactions, 'V_i (ราบแผ่นดินไหว-ตัน)': pile_horizontal_shear})
        st.dataframe(df_react.style.highlight_max(subset=['V_i (ราบแผ่นดินไหว-ตัน)'], color='#f5b041'), hide_index=True, use_container_width=True)

with tab_calc:
    st.markdown("## 📄 รายงานการคำนวณออกแบบฐานรากอย่างละเอียด (Detailed Calculation Report)")
    st.markdown("**วิธีการวิเคราะห์:** Advanced Flexible Plate (FDM Energy Formulation) + Wood-Armer Equations")
    st.markdown("**อ้างอิงมาตรฐาน:** ACI 318-19 / วสท. (รูปแบบ Strength Design Method)")
    st.divider()

    # คำนวณตัวแปรเสริมเพื่อใช้แสดงผลใน Report
    beta_ratio = max(cx, cy) / min(cx, cy) if min(cx, cy) > 0 else 1.0
    alpha_s = 40 if col_position == "Interior" else (30 if col_position == "Edge" else 20)
    b0_col = 2 * ((cx + d_actual) + (cy + d_actual))
    
    st.markdown("### 📌 ส่วนที่ 1: ข้อมูลพารามิเตอร์และการหาความลึกประสิทธิผล (Effective Depth)")
    st.markdown(f"""
    - **กำลังอัดคอนกรีต ($f'_c$):** {fc_prime} ksc, **กำลังครากเหล็กเสริม ($f_y$):** {fy} ksc
    - **ขนาดตอม่อ ($c_x \\times c_y$):** {cx} m $\\times$ {cy} m
    - **เหล็กเสริมหลัก:** DB{bar_dia} (พื้นที่ $A_b = {ab_area:.2f}$ $\\text{{cm}}^2$)
    - **ความแข็งสปริงเสาเข็ม ($k_s$):** {pile_ks:,.2f} Ton/m
    """)
    st.latex(rf"d = t - \text{{cover}} - \frac{{d_b}}{{2}} = {t_actual:.3f} - {concrete_cover_cm/100:.3f} - \frac{{{bar_dia/1000:.3f}}}{{2}} = {d_actual:.3f} \text{{ m}}")

    st.markdown("### 📌 ส่วนที่ 2: น้ำหนักบรรทุกประลัย (Factored Ultimate Loads)")
    st.latex(rf"P_{{ult}} = ({factor_dl} \times DL) + ({factor_ll} \times LL) = ({factor_dl} \times {DL}) + ({factor_ll} \times {LL}) = {P_ultimate:.2f} \text{{ Ton}}")
    st.latex(rf"W_{{footing\_u}} = \gamma_{{DL}} \times (Area \times t \times 2.4) = {factor_dl} \times ({footing_area:.2f} \times {t_actual:.2f} \times 2.4) = {w_u_footing:.2f} \text{{ Ton}}")
    st.latex(rf"W_{{soil\_u}} = \gamma_{{DL}} \times W_{{soil}} = {factor_dl} \times {W_soil:.2f} = {w_u_soil:.2f} \text{{ Ton}}")
    st.latex(rf"\Sigma P_{{total\_u}} = {P_ultimate:.2f} + {w_u_footing:.2f} + {w_u_soil:.2f} = {P_u_total:.2f} \text{{ Ton}}")
    st.markdown("**การถ่ายโมเมนต์จากการเยื้องศูนย์ของกลุ่มเสาเข็ม ($e_x, e_y$):**")
    st.latex(rf"e_x = {ecc_x:.3f} \text{{ m}}, \quad e_y = {ecc_y:.3f} \text{{ m}}")
    st.latex(rf"M_{{ux\_total}} = M_{{cx\_u}} + P_{{total\_u}}(-e_y) = {Mu_cx + (P_u_total * -ecc_y):.2f} \text{{ Ton-m}}")
    st.latex(rf"M_{{uy\_total}} = M_{{cy\_u}} + P_{{total\_u}}(-e_x) = {Mu_cy + (P_u_total * -ecc_x):.2f} \text{{ Ton-m}}")

    report_Ec_mpa = 4700 * math.sqrt(fc_prime * 0.0980665)
    report_Ec_ton = report_Ec_mpa * 101.9716
    report_D = (report_Ec_ton * (t_actual**3)) / (12 * (1 - 0.15**2))
    
    st.markdown("### 📌 ส่วนที่ 3: พฤติกรรมแผ่นพื้นยืดหยุ่น (Flexural Rigidity & FDM Moments)")
    st.latex(rf"E_c = 4700\sqrt{{f'_c \text{{ (MPa)}}}} = {report_Ec_ton:,.0f} \text{{ Ton/m}}^2 \quad (\nu = 0.15)")
    st.latex(rf"D = \frac{{E_c t^3}}{{12(1-\nu^2)}} = \frac{{{report_Ec_ton:,.0f} \times {t_actual:.2f}^3}}{{12(1 - 0.15^2)}} = {report_D:,.2f} \text{{ Ton-m}}")
    st.markdown("**แปลงโมเมนต์ดัดและแรงบิดจาก FDM Grid สู่ Design Moments (Wood-Armer Equations):**")
    st.latex(r"M_x^* = |M_x| + |M_{xy}|, \quad M_y^* = |M_y| + |M_{xy}|")
    st.latex(rf"M_{{ux\_max}}^* = {Mu_x_max_fdm:.2f} \text{{ Ton-m/m}}, \quad M_{{uy\_max}}^* = {Mu_y_max_fdm:.2f} \text{{ Ton-m/m}}")

    st.markdown("### 📌 ส่วนที่ 4: การตรวจสอบแรงเฉือน (Shear Validation)")
    st.markdown("**4.1 แรงเฉือนทะลุตอม่อ (Column Punching Shear)**")
    st.latex(rf"b_{{0\_col}} = 2((c_x + d) + (c_y + d)) = 2(({cx} + {d_actual:.3f}) + ({cy} + {d_actual:.3f})) = {b0_col:.3f} \text{{ m}}")
    
    vc1 = 0.53 * (1 + 2/beta_ratio) * math.sqrt(fc_prime)
    vc2 = 0.27 * (alpha_s * (d_actual*100) / (b0_col*100) + 2) * math.sqrt(fc_prime)
    vc3 = 1.06 * math.sqrt(fc_prime)
    
    st.latex(rf"v_c = \min \begin{{cases}} 0.53(1+\frac{{2}}{{\beta}})\sqrt{{f'_c}} = {vc1:.2f} \\ 0.27(\frac{{\alpha_s d}}{{b_0}}+2)\sqrt{{f'_c}} = {vc2:.2f} \\ 1.06\sqrt{{f'_c}} = {vc3:.2f} \end{{cases}} \times \phi (0.75) = {v_cp_col:.2f} \text{{ ksc}}")
    st.latex(rf"v_{{u\_col}} = {v_up_col:.2f} \text{{ ksc}} \le {v_cp_col:.2f} \text{{ ksc}} \rightarrow \textbf{{{'SAFE' if v_up_col <= v_cp_col else 'FAIL'}}}")

    st.markdown("**4.2 แรงเฉือนทะลุเสาเข็ม (Pile Punching Shear)**")
    st.latex(rf"v_{{c\_pile}} = \phi 1.06\sqrt{{f'_c}} = 0.75 \times 1.06\sqrt{{{fc_prime}}} = {v_cp_pile:.2f} \text{{ ksc}}")
    st.latex(rf"v_{{u\_pile}} = {v_up_pile:.2f} \text{{ ksc}} \le {v_cp_pile:.2f} \text{{ ksc}} \rightarrow \textbf{{{'SAFE' if v_up_pile <= v_cp_pile else 'FAIL'}}}")

    st.markdown("**4.3 แรงเฉือนคานกว้าง (Wide-Beam Shear ควบรวม FDM 3rd Derivative)**")
    st.latex(rf"v_{{c\_wb}} = \phi 0.53\sqrt{{f'_c}} = 0.75 \times 0.53\sqrt{{{fc_prime}}} = {v_cwb:.2f} \text{{ ksc}}")
    st.latex(rf"v_{{u\_wb}} = \max(v_{{static}}, 0.70v_{{FDM}}) = {v_uwb:.2f} \text{{ ksc}} \le {v_cwb:.2f} \text{{ ksc}} \rightarrow \textbf{{{'SAFE' if v_uwb <= v_cwb else 'FAIL'}}}")

    st.markdown("### 📌 ส่วนที่ 5: การออกแบบเหล็กเสริมรับแรงดัด (Flexural Reinforcement)")
    report_rho_min = max(0.8 * math.sqrt(fc_prime) / fy, 14.0 / fy)
    report_As_min = report_rho_min * 100 * (d_actual * 100)
    st.latex(rf"\rho_{{min}} = \max \left( \frac{{0.8\sqrt{{f'_c}}}}{{f_y}}, \frac{{14}}{{f_y}} \right) = \max \left( \frac{{0.8\sqrt{{{fc_prime}}}}}{{{fy}}}, \frac{{14}}{{{fy}}} \right) = {report_rho_min:.5f}")
    st.latex(rf"A_{{s,min}} = \rho_{{min}} b d = {report_rho_min:.5f} \times 100 \times {d_actual*100:.1f} = {report_As_min:.2f} \text{{ cm}}^2/\text{{m}}")
    
    # คำนวณจำลองสำหรับแสดงผลแกน X
    Mu_kg_cm_x = Mu_x_max_fdm * 1000 * 100
    Rn_x = Mu_kg_cm_x / (phi_flexure * 100 * (d_actual*100)**2) if d_actual > 0 else 0
    val_sqrt_x = max(1 - (2 * Rn_x) / (0.85 * fc_prime), 0)
    rho_req_x = (0.85 * fc_prime / fy) * (1 - math.sqrt(val_sqrt_x)) if val_sqrt_x > 0 else 0
    
    st.markdown("**คำนวณเหล็กแกน X (พิจารณาที่ความกว้าง $b=1.0$ m):**")
    st.latex(rf"R_{{nx}} = \frac{{M_{{ux}}^*}}{{\phi b d^2}} = \frac{{{Mu_x_max_fdm:.2f} \times 10^5}}{{0.90 \times 100 \times {d_actual*100:.1f}^2}} = {Rn_x:.2f} \text{{ ksc}}")
    st.latex(rf"\rho_{{req,x}} = \frac{{0.85 f'_c}}{{f_y}} \left( 1 - \sqrt{{1 - \frac{{2 R_{{nx}}}}{{0.85 f'_c}}}} \right) = \frac{{0.85({fc_prime})}}{{{fy}}} \left( 1 - \sqrt{{1 - \frac{{2({Rn_x:.2f})}}{{0.85({fc_prime})}}}} \right) = {rho_req_x:.5f}")
    st.latex(rf"A_{{s,req(X)}} = \max(\rho_{{req,x}} b d, A_{{s,min}}) = {as_req_x:.2f} \text{{ cm}}^2/\text{{m}} \rightarrow \textbf{{ใช้ {n_bars_x}-DB{bar_dia} @ {sp_x} cm}} \text{{ (}} A_s = {ab_area * (100/sp_x):.2f} \text{{ cm}}^2/\text{{m}} \text{{)}}")
    
    st.markdown("**คำนวณเหล็กแกน Y:**")
    st.latex(rf"A_{{s,req(Y)}} = {as_req_y:.2f} \text{{ cm}}^2/\text{{m}} \rightarrow \textbf{{ใช้ {n_bars_y}-DB{bar_dia} @ {sp_y} cm}} \text{{ (}} A_s = {ab_area * (100/sp_y):.2f} \text{{ cm}}^2/\text{{m}} \text{{)}}")

    st.markdown("### 📌 ส่วนที่ 6: การตรวจสอบสภาวะการใช้งาน (Serviceability - Crack Width Control)")
    st.markdown("**การคำนวณความกว้างรอยร้าวร้าวผิวคอนกรีตตามสมการ Gergely-Lutz:**")
    
    As_prov_x = n_bars_x * ab_area
    fs_mpa = min((Ms_x_max_fdm * 1000 * 100) / (As_prov_x * 0.85 * (d_actual*100)) * 0.0980665, 0.6 * 400.0) if As_prov_x > 0 else 0
    dc_mm = (concrete_cover_cm * 10.0) + (bar_dia / 2.0)
    s_mm = sp_x * 10.0
    A_eff = 2.0 * dc_mm * s_mm
    
    st.latex(rf"f_s = \frac{{M_s}}{{A_{{s,prov}} \times 0.85 \times d}} = \frac{{{Ms_x_max_fdm:.2f} \times 10^5}}{{{As_prov_x:.2f} \times 0.85 \times {d_actual*100:.1f}}} \times 0.098 = {fs_mpa:.2f} \text{{ MPa}} \quad (\le 0.6f_y)")
    st.latex(rf"d_c = \text{{cover}} + \frac{{d_b}}{{2}} = {concrete_cover_cm*10} + \frac{{{bar_dia}}}{{2}} = {dc_mm:.1f} \text{{ mm}}")
    st.latex(rf"A_{{eff}} = 2 d_c s = 2 \times {dc_mm:.1f} \times {s_mm:.1f} = {A_eff:,.1f} \text{{ mm}}^2")
    st.latex(rf"w_{{crack}} = 11 \times 10^{{-6}} \beta f_s \sqrt[3]{{d_c A_{{eff}}}} = 11 \times 10^{{-6}} (1.2) ({fs_mpa:.2f}) \sqrt[3]{{{dc_mm:.1f} \times {A_eff:,.1f}}} = {calculated_w:.3f} \text{{ mm}}")
    st.latex(rf"{calculated_w:.3f} \text{{ mm}} \le \text{{Allowable Limit (}}{w_allowable} \text{{ mm)}} \rightarrow \textbf{{{'PASSED' if calculated_w <= w_allowable else 'EXCEEDED'}}}")
with tab_visuals:
    col_plot1, col_plot2 = st.columns(2)
    with col_plot1:
        st.markdown("#### 📐 A) As-Built Plan View (Polygon Based)")
        fig_2d = generate_2d_plan_view(concrete_vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l, columns_list, cg_actual_x, cg_actual_y)
        st.pyplot(fig_2d); plt.close(fig_2d)
    with col_plot2:
        st.markdown("#### 🟥 B) Ultra Section Detailing View")
        if require_top_steel: st.info(f"💡 **Top Rebar Activated:** {'เนื่องจากมีเข็มรับแรงถอน' if has_tension else f'เนื่องจากฐานรากหนา t={t_actual:.2f}m ≥ 0.60m'}")
        fig_rebar = generate_rebar_detailing_view(t_actual, B_max_visual, concrete_cover_cm, pile_embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel)
        st.pyplot(fig_rebar); plt.close(fig_rebar)
    st.markdown("#### 🧊 C) 3D Interactive Mesh (Exact Geometry)")
    fig_3d = generate_3d_mesh(tuple(concrete_vertices), t_actual, cx, cy, tuple(piles_actual), pile_shape, pile_w, pile_l, pile_embed_cm / 100, tuple(columns_list))
    st.plotly_chart(fig_3d, use_container_width=True)
