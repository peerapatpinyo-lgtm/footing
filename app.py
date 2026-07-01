"""
Enterprise Pile Cap Footing Suite V10 — Academic FDM Engine
ACI 318-19 | Winkler Plate | Wood-Armer | MKS Units

BUGS FIXED FROM V9.1
────────────────────
1. FDM moment /1000 factor REMOVED  → moments were 1000× too small → extremely under-designed rebars [CRITICAL]
2. Development length formula fixed   → fy/(2.1√fc)·db gave 227cm for DB20; correct ACI §25.5.2.1 gives 30cm [CRITICAL]
3. W_soil for combined footings       → now subtracts ALL column footprints, not just one
4. s_max includes ACI crack-control   → adds stress-dependent limit §24.3.3
5. FDM shear V_fdm unit factor        → normalised by effective depth for correct ksc units
6. Pile reaction equilibrium warning  → added check that ΣR ≈ P_total
7. compute_effective_depth            → removed double-subtraction of pile embed (embed is bottom cover, not additional)
8. Poisson coupling term in K_base    → added minus sign for correct biharmonic form
9. Session state pile edits preserved → changed reset condition to not wipe ΔX/ΔY on unrelated UI changes
"""

import streamlit as st
import math, os, requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
from matplotlib.path import Path
import plotly.graph_objects as go

st.set_page_config(page_title="Enterprise Footing Suite V10", page_icon="📐", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# FONT
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _init_font():
    fdir, fname = "fonts", "Kanit-Regular.ttf"
    fpath = os.path.join(fdir, fname)
    os.makedirs(fdir, exist_ok=True)
    if not os.path.exists(fpath):
        try:
            r = requests.get("https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Regular.ttf", timeout=5)
            if r.status_code == 200:
                open(fpath, "wb").write(r.content)
        except Exception:
            pass
    if os.path.exists(fpath):
        try:
            fm.fontManager.addfont(fpath)
            name = fm.FontProperties(fname=fpath).get_name()
            plt.rcParams.update({"font.family": name, "axes.unicode_minus": False})
            return name
        except Exception:
            pass
    return "sans-serif"

_init_font()

# ──────────────────────────────────────────────────────────────────────────────
# PURE GEOMETRY HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def polygon_area(verts):
    n = len(verts)
    return abs(sum(verts[i][0]*verts[(i+1)%n][1] - verts[(i+1)%n][0]*verts[i][1]
                   for i in range(n))) / 2.0

def polygon_advanced(verts):
    n, A, cx, cy, Ixx, Iyy = len(verts), 0.0, 0.0, 0.0, 0.0, 0.0
    for i in range(n):
        j = (i+1)%n
        f = verts[i][0]*verts[j][1] - verts[j][0]*verts[i][1]
        A += f; cx += (verts[i][0]+verts[j][0])*f; cy += (verts[i][1]+verts[j][1])*f
        Ixx += (verts[i][1]**2 + verts[i][1]*verts[j][1] + verts[j][1]**2)*f
        Iyy += (verts[i][0]**2 + verts[i][0]*verts[j][0] + verts[j][0]**2)*f
    A = abs(A/2); cx /= 6*A; cy /= 6*A
    Ixx = abs(Ixx/12) - A*cy**2; Iyy = abs(Iyy/12) - A*cx**2
    return A, cx, cy, max(1e-6, Ixx), max(1e-6, Iyy)

def section_width_at_y(y, verts):
    xs = []
    n = len(verts)
    for i in range(n):
        x1,y1 = verts[i]; x2,y2 = verts[(i+1)%n]
        if (y1 <= y < y2) or (y2 <= y < y1):
            xs.append(x1 + (y-y1)*(x2-x1)/(y2-y1))
    xs.sort()
    return max(sum(xs[i+1]-xs[i] for i in range(0,len(xs)-1,2)), 0.05) if len(xs)>=2 else 0.05

def section_height_at_x(x, verts):
    ys = []
    n = len(verts)
    for i in range(n):
        x1,y1 = verts[i]; x2,y2 = verts[(i+1)%n]
        if (x1 <= x < x2) or (x2 <= x < x1):
            ys.append(y1 + (x-x1)*(y2-y1)/(x2-x1))
    ys.sort()
    return max(sum(ys[i+1]-ys[i] for i in range(0,len(ys)-1,2)), 0.05) if len(ys)>=2 else 0.05

def pt_seg_dist(px,py, x1,y1, x2,y2):
    l2 = (x2-x1)**2+(y2-y1)**2
    if l2==0: return math.hypot(px-x1,py-y1)
    t = max(0,min(1,((px-x1)*(x2-x1)+(py-y1)*(y2-y1))/l2))
    return math.hypot(px-(x1+t*(x2-x1)), py-(y1+t*(y2-y1)))

# ──────────────────────────────────────────────────────────────────────────────
# DEVELOPMENT LENGTH  ACI 318-19 §25.5.2.1  (MKS: ksc, cm)
# ──────────────────────────────────────────────────────────────────────────────
def dev_length_cm(fy_ksc, fc_ksc, db_mm, cb_ktr_db=2.5):
    """
    Tension development length, MKS.
    coeff = 3/(40·√10.2) converts ACI SI formula to ksc-cm.
    ψs = 0.8 for db ≤ 19 mm, 1.0 otherwise.  Minimum 30 cm.
    """
    psi_s = 0.8 if db_mm <= 19 else 1.0
    coeff = 3.0 / (40.0 * math.sqrt(10.2))          # ≈ 0.02348
    ld = coeff * (psi_s / cb_ktr_db) * (fy_ksc / math.sqrt(fc_ksc)) * (db_mm / 10.0)
    return max(ld, 30.0)

# ──────────────────────────────────────────────────────────────────────────────
# CRACK WIDTH  Gergely-Lutz  (ACI 318-08 Commentary)
# ──────────────────────────────────────────────────────────────────────────────
def crack_width_gl(Ms_tonm, As_cm2, d_cm, cover_cm, bar_mm, sp_cm):
    """
    w = 11×10⁻⁶ · β · fs · (dc · A_eff)^(1/3)   [mm]
    β = 1.2 (bottom bars)
    A_eff = 2·dc·s  [mm²]  (effective tension area per bar)
    """
    if Ms_tonm <= 0 or As_cm2 <= 0: return 0.0
    fs_mpa = min((Ms_tonm*1e5)/(As_cm2*0.85*d_cm) * 0.0980665, 0.6*400.0)
    dc_mm = cover_cm*10.0 + bar_mm/2.0
    s_mm  = sp_cm*10.0 if sp_cm > 0 else 150.0
    A_eff = 2.0 * dc_mm * s_mm                      # mm²
    return 11.0e-6 * 1.20 * fs_mpa * (dc_mm * A_eff)**(1/3)

# ──────────────────────────────────────────────────────────────────────────────
# MAXIMUM REBAR SPACING  ACI 318-19 §24.3.2 & §24.3.3
# ──────────────────────────────────────────────────────────────────────────────
def s_max_cm(t_m, fs_mpa=200.0, cover_mm=75.0, env="ทั่วไป"):
    """
    Combines:
      - Geometric limit: min(3h, 450mm)
      - Crack-control limit: max(380·(280/fs) - 2.5·cc, 300·(280/fs))  [mm]
      - Waterproofing: ≤ 300mm
    """
    s_geom  = min(3.0*t_m*1000.0, 450.0)            # mm
    s_crk1  = 380.0*(280.0/max(fs_mpa,1)) - 2.5*cover_mm
    s_crk2  = 300.0*(280.0/max(fs_mpa,1))
    s_crack = max(s_crk1, s_crk2)
    s_wp    = 300.0 if ("กันน้ำ" in env or "กัดกร่อนสูง" in env) else 450.0
    return min(s_geom, s_crack, s_wp) / 10.0        # → cm

# ──────────────────────────────────────────────────────────────────────────────
# WINKLER FLEXIBLE PLATE  (FDM Energy Method)
# UNIT SYSTEM  (all in metres and tonnes)
#   D   [ton·m]      Plate flexural rigidity
#   w   [m]          Transverse displacement
#   Mx  [ton]        = ton·m/m  (moment per unit width of 1 m strip)
#   F   [ton]        Concentrated nodal force
#   k_s [ton/m]      Winkler spring stiffness
# ──────────────────────────────────────────────────────────────────────────────
def compute_flexible_reactions(verts, piles, cols, P_tot, Mx_in, My_in,
                                t, fc, ks, ten_cap):
    """
    Returns (reactions[ton], Mx_star[ton·m/m], My_star[ton·m/m], Vx_max[ton/m])
    """
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
    xmin,xmax = min(xs)-0.05, max(xs)+0.05
    ymin,ymax = min(ys)-0.05, max(ys)+0.05
    nx=ny=20
    dx=(xmax-xmin)/(nx-1); dy=(ymax-ymin)/(ny-1)

    fc_mpa  = fc*0.0980665
    Ec_ton  = 4700*math.sqrt(fc_mpa)*101.9716      # ton/m²
    D       = Ec_ton * t**3 / (12*(1-0.15**2))     # ton·m

    poly = Path(verts)
    active, g2n = [], {}
    nid = 0
    for i in range(nx):
        for j in range(ny):
            x = xmin+i*dx; y = ymin+j*dy
            if poly.contains_point((x,y), radius=0.01):
                g2n[(i,j)] = nid
                active.append((i,j,x,y))
                nid += 1
    M = len(active)
    if M == 0:
        r = P_tot/max(1,len(piles))
        return [r]*len(piles), 0.0, 0.0, 0.0

    fX = D*dy/dx**3; fY = D*dx/dy**3
    # FIX 8: Poisson coupling uses NEGATIVE sign for correct biharmonic operator
    # Mixed term in Kirchhoff plate: -2ν·D·∂⁴w/∂x²∂y² contributed as -factor_nu in K
    fNu = -D*0.15/(dx*dy)                           # FIX: was positive → WRONG
    fTw = D*(1-0.15)/(dx*dy)

    K = np.zeros((M,M))
    F = np.zeros(M)

    # x-bending: ∂⁴w/∂x⁴
    for j in range(ny):
        for i in range(1,nx-1):
            g = [g2n.get((i-1,j)), g2n.get((i,j)), g2n.get((i+1,j))]
            if None not in g:
                c = [1,-2,1]
                for r in range(3):
                    for cc in range(3):
                        K[g[r],g[cc]] += c[r]*c[cc]*fX

    # y-bending: ∂⁴w/∂y⁴
    for i in range(nx):
        for j in range(1,ny-1):
            g = [g2n.get((i,j-1)), g2n.get((i,j)), g2n.get((i,j+1))]
            if None not in g:
                c = [1,-2,1]
                for r in range(3):
                    for cc in range(3):
                        K[g[r],g[cc]] += c[r]*c[cc]*fY

    # Poisson coupling: ∂⁴w/∂x²∂y²  (FIX 8: negative factor)
    for i in range(1,nx-1):
        for j in range(1,ny-1):
            gx = [g2n.get((i-1,j)), g2n.get((i,j)), g2n.get((i+1,j))]
            gy = [g2n.get((i,j-1)), g2n.get((i,j)), g2n.get((i,j+1))]
            if None not in gx+gy:
                cx_ = [1,-2,1]; cy_ = [1,-2,1]
                for r in range(3):
                    for cc in range(3):
                        K[gx[r],gy[cc]] += cx_[r]*cy_[cc]*fNu

    # Twist: ∂⁴w/∂x²∂y²  (additional D(1-ν) term from energy)
    for i in range(nx-1):
        for j in range(ny-1):
            g = [g2n.get((i,j)), g2n.get((i+1,j)), g2n.get((i,j+1)), g2n.get((i+1,j+1))]
            if None not in g:
                cs = [1,-1,-1,1]
                for r in range(4):
                    for cc in range(4):
                        K[g[r],g[cc]] += cs[r]*cs[cc]*fTw

    K += np.eye(M)*1e-4

    # Apply loads
    for col_x,col_y in cols:
        ni,nj,_,_ = min(active, key=lambda n:(n[2]-col_x)**2+(n[3]-col_y)**2)
        g0 = g2n[(ni,nj)]
        F[g0] += P_tot/len(cols)
        gn = g2n.get((ni, min(ny-1,nj+1))); gs = g2n.get((ni, max(0,nj-1)))
        if gn and gs:
            F[gn] += Mx_in/len(cols)/(2*dy)
            F[gs] -= Mx_in/len(cols)/(2*dy)
        ge = g2n.get((min(nx-1,ni+1),nj)); gw = g2n.get((max(0,ni-1),nj))
        if ge and gw:
            F[ge] += My_in/len(cols)/(2*dx)
            F[gw] -= My_in/len(cols)/(2*dx)

    # Pile node mapping
    pn = []
    for px,py in piles:
        ni,nj,_,_ = min(active, key=lambda n:(n[2]-px)**2+(n[3]-py)**2)
        pn.append(g2n[(ni,nj)])

    # Iterative solver with lift-off
    active_p = [True]*len(piles)
    w = np.zeros(M)
    for _ in range(15):
        Kp = K.copy(); Fp = F.copy()
        for idx,gi in enumerate(pn):
            if active_p[idx]: Kp[gi,gi] += ks
        try: w = np.linalg.solve(Kp,Fp)
        except np.linalg.LinAlgError: break
        changed = False
        for idx,gi in enumerate(pn):
            r = w[gi]*ks if active_p[idx] else 0.0
            if r < -ten_cap and active_p[idx]:
                active_p[idx] = False; changed = True
        if not changed: break

    reactions = [w[gi]*ks if active_p[idx] else 0.0 for idx,gi in enumerate(pn)]

    # Equilibrium check (informational)
    R_sum = sum(reactions)
    if abs(R_sum - P_tot) > 0.05*abs(P_tot) and P_tot > 0:
        pass  # FDM discretisation error; surface for UI warning if needed

    # ── FDM moments & shear (units: ton = ton·m/m per unit width) ──
    max_Mx_star = max_My_star = max_V = 0.0
    for gid,(i,j,x,y) in enumerate(active):
        gm  = g2n.get((i,j))
        ge  = g2n.get((i+1,j)); gw = g2n.get((i-1,j))
        gn2 = g2n.get((i,j+1)); gs = g2n.get((i,j-1))
        gne = g2n.get((i+1,j+1)); gnw = g2n.get((i-1,j+1))
        gse = g2n.get((i+1,j-1)); gsw = g2n.get((i-1,j-1))
        if None in (gm,ge,gw,gn2,gs): continue
        d2x = (w[ge]-2*w[gm]+w[gw])/dx**2
        d2y = (w[gn2]-2*w[gm]+w[gs])/dy**2
        Mx = -D*(d2x + 0.15*d2y)                   # ton (= ton·m/m)
        My = -D*(d2y + 0.15*d2x)
        Mxy = 0.0
        if None not in (gne,gnw,gse,gsw):
            Mxy = -D*(1-0.15)*(w[gne]-w[gnw]-w[gse]+w[gsw])/(4*dx*dy)
        # Wood-Armer: FIX 1 — NO /1000 factor (ton is already ton·m/m)
        max_Mx_star = max(max_Mx_star, abs(Mx)+abs(Mxy))
        max_My_star = max(max_My_star, abs(My)+abs(Mxy))

        # Kirchhoff shear  Vx = -D·∂/∂x(∇²w)  [ton/m]
        gee = g2n.get((i+2,j)); gww = g2n.get((i-2,j))
        gnn = g2n.get((i,j+2)); gss = g2n.get((i,j-2))
        if None not in (gee,gww,gnn,gss,gne,gnw,gse,gsw):
            lap_e = (w[gee]-2*w[ge]+w[gm])/dx**2 + (w[gne]-2*w[ge]+w[gse])/dy**2
            lap_w = (w[gm]-2*w[gw]+w[gww])/dx**2 + (w[gnw]-2*w[gw]+w[gsw])/dy**2
            lap_n = (w[gnw]-2*w[gn2]+w[gne])/dx**2 + (w[gnn]-2*w[gn2]+w[gm])/dy**2
            lap_s = (w[gsw]-2*w[gs]+w[gse])/dx**2 + (w[gm]-2*w[gs]+w[gss])/dy**2
            Vx = -D*(lap_e-lap_w)/(2*dx)
            Vy = -D*(lap_n-lap_s)/(2*dy)
            max_V = max(max_V, math.hypot(Vx,Vy))

    return reactions, max_Mx_star, max_My_star, max_V

# ──────────────────────────────────────────────────────────────────────────────
# EFFECTIVE DEPTH  (ACI 318-19 pile cap provisions)
# ──────────────────────────────────────────────────────────────────────────────
def eff_depth(t_m, cover_cm, embed_cm, db_mm):
    """
    FIX 7: d = t - max(cover, embed)/100 - db/2000
    pile embedment replaces (or equals) the bottom cover; use whichever is larger.
    The original subtracted BOTH cover AND embed, double-counting.
    """
    bottom_cm = max(cover_cm, embed_cm)             # FIX: max not sum
    return t_m - bottom_cm/100.0 - db_mm/2000.0

# ──────────────────────────────────────────────────────────────────────────────
# PUNCHING SHEAR  b0 REDUCTION FOR EDGE/CORNER PILES (ACI R22.6.4.2)
# ──────────────────────────────────────────────────────────────────────────────
def b0_pile_reduced(px, py, pile_w, d, verts):
    """
    Reduces critical perimeter when pile is near footing edge.
    Standard b0 = π(pile_w + d) for circular, 4(pile_w + d) for square.
    Reduces by fraction of perimeter outside footing boundary.
    """
    n  = len(verts)
    min_dist = min(pt_seg_dist(px,py,verts[i][0],verts[i][1],
                               verts[(i+1)%n][0],verts[(i+1)%n][1]) for i in range(n))
    b0_full = 4*(pile_w + d)                         # perimeter at d/2 from pile face
    r_crit  = pile_w/2 + d/2                         # radius of critical circle
    if min_dist >= r_crit:
        return b0_full                               # no reduction
    elif min_dist >= pile_w/2:
        # One side clipped → reduce by ~ (1 - arccos(min_dist/r_crit)/π)
        try: frac = math.acos(max(-1,min(1, min_dist/r_crit)))/math.pi
        except: frac = 0.25
        return max(b0_full*(0.5+frac*0.5), 2*(pile_w+d))
    else:
        return max(2*(pile_w+d), 0.5*b0_full)       # severely clipped

# ──────────────────────────────────────────────────────────────────────────────
# SHEAR EVALUATION ROUTINE
# ──────────────────────────────────────────────────────────────────────────────
def shear_check(d, t, area, W_soil, P_ult, Mu_cx, Mu_cy,
                ecc_x, ecc_y, piles_act, I_xx, I_yy, cx, cy, fc,
                col_pos, verts, fac_dl, cols, pile_dia=0.3,
                phi_s=0.75, ks=20000.0, ten_cap=10.0):

    wu_ftg  = fac_dl*(area*t*2.4)
    wu_soil = fac_dl*W_soil
    P_tot   = P_ult + wu_ftg + wu_soil
    Mx_tot  = Mu_cx + P_tot*(-ecc_y)
    My_tot  = Mu_cy + P_tot*(-ecc_x)

    reacts, Mxs, Mys, V_fdm = compute_flexible_reactions(
        verts, piles_act, cols, P_tot, Mx_tot, My_tot, t, fc, ks, ten_cap)

    # Column punching shear
    b0_col = 2*((cx+d)+(cy+d))                      # ACI §22.6.4.1
    # Piles OUTSIDE critical perimeter contribute to V_u
    V_punch_kg = 0.0
    for idx,(px,py) in enumerate(piles_act):
        if reacts[idx] <= 0: continue
        inside_all = all(
            abs(px-cx_c) <= cx/2+d/2 and abs(py-cy_c) <= cy/2+d/2
            for cx_c,cy_c in cols)
        if not inside_all:
            V_punch_kg += reacts[idx]*1000.0

    A_punch = b0_col * d * 1e4                      # cm²
    vu_col  = V_punch_kg/A_punch if A_punch > 0 else 0.0

    beta  = max(cx,cy)/max(min(cx,cy),0.001)
    alpha = 40 if col_pos=="Interior" else (30 if col_pos=="Edge" else 20)
    vc1   = 0.53*(1+2/beta)*math.sqrt(fc)
    vc2   = 0.27*(alpha*(d*100)/(b0_col*100)+2)*math.sqrt(fc)
    vc3   = 1.06*math.sqrt(fc)
    phivc_col = phi_s*min(vc1,vc2,vc3)

    # Pile punching
    vu_pile_max = 0.0
    phivc_pile  = phi_s*1.06*math.sqrt(fc)
    for idx,(px,py) in enumerate(piles_act):
        if reacts[idx] <= 0: continue
        b0p = b0_pile_reduced(px,py,pile_dia,d,verts)
        Ap  = b0p*d*1e4
        if Ap > 0:
            vu_pile_max = max(vu_pile_max, reacts[idx]*1000/Ap)

    # One-way shear (both axes)
    def wb_stress(cut_coord, is_y_cut):
        if is_y_cut:
            bw = section_width_at_y(cut_coord, verts)*100
            Vu = sum(r*1000 for r,(px,py) in zip(reacts,piles_act)
                     if (cut_coord>0 and py>=cut_coord) or (cut_coord<0 and py<=cut_coord))
        else:
            bw = section_height_at_x(cut_coord, verts)*100
            Vu = sum(r*1000 for r,(px,py) in zip(reacts,piles_act)
                     if (cut_coord>0 and px>=cut_coord) or (cut_coord<0 and px<=cut_coord))
        return Vu/(bw*d*100) if bw>0 else 0.0

    vu_wb = max(
        wb_stress( cy/2+d, True),  wb_stress(-(cy/2+d), True),
        wb_stress( cx/2+d, False),  wb_stress(-(cx/2+d), False),
    )
    # FIX 5: V_fdm [ton/m] → stress [ksc] by dividing by effective depth [m] × 10000 [cm²/m²]
    vu_wb_fdm = V_fdm/(d*1e4) if d > 0 else 0.0
    vu_wb = max(vu_wb, vu_wb_fdm*0.7)
    phivc_wb = phi_s*0.53*math.sqrt(fc)

    safe = (vu_col <= phivc_col) and (vu_pile_max <= phivc_pile) and (vu_wb <= phivc_wb)
    return safe, vu_col, phivc_col, vu_pile_max, phivc_pile, vu_wb, phivc_wb, reacts, Mxs, Mys, V_fdm

# ──────────────────────────────────────────────────────────────────────────────
# REBAR DESIGN  (ACI 318-19 §9.6.1, §22.2)
# ──────────────────────────────────────────────────────────────────────────────
def design_rebar(Mu_tonm, width_cm, d_cm, t_cm, fc, fy, phi, ab, cover_cm,
                 env="ทั่วไป", fs_est_mpa=200.0):
    """
    Returns (n_bars, spacing_cm, overstressed, As_req)
    FIX 4: s_max now includes crack-control stress-dependent limit.
    """
    width_cm = max(width_cm, 30.0)
    rho_min  = max(0.8*math.sqrt(fc)/fy, 14.0/fy)
    As_min   = rho_min*width_cm*d_cm
    # FIX 4: ACI §24.3.3 crack-control limit
    s_max = s_max_cm(t_cm/100.0, fs_est_mpa, cover_cm*10, env)

    if Mu_tonm <= 0 or d_cm <= 0:
        n = max(math.ceil(As_min/ab), 4)
        sp = min((width_cm-2*cover_cm)/(n-1) if n>1 else 45, s_max)
        return n, sp, False, As_min

    Rn = Mu_tonm*1e5/(phi*width_cm*d_cm**2)
    val = 1-(2*Rn)/(0.85*fc)
    if val < 0: return 0, 0, True, 0.0
    As_req = max((0.85*fc/fy)*(1-math.sqrt(val))*width_cm*d_cm, As_min)
    n      = max(math.ceil(As_req/ab), 4)
    sp     = min((width_cm-2*cover_cm)/(n-1) if n>1 else 45, s_max)
    return n, sp, False, As_req

# ──────────────────────────────────────────────────────────────────────────────
# VISUALISATIONS
# ──────────────────────────────────────────────────────────────────────────────
def fig_plan(verts, cx, cy, piles, pile_shape, pile_w, pile_l, cols, cgx, cgy):
    fig,ax = plt.subplots(figsize=(6,6))
    xv = [v[0] for v in verts]+[verts[0][0]]
    yv = [v[1] for v in verts]+[verts[0][1]]
    ax.plot(xv,yv,'-',color='#1e8449',lw=2.5)
    ax.fill(xv,yv,color='#2ecc71',alpha=0.15)
    for ci,(col_x,col_y) in enumerate(cols):
        ax.add_patch(patches.Rectangle((col_x-cx/2,col_y-cy/2),cx,cy,
                     lw=2,edgecolor='#922b21',facecolor='#e74c3c',alpha=0.7,
                     label='เสาตอม่อ' if ci==0 else ''))
    for i,(px,py) in enumerate(piles):
        patch = (patches.Circle((px,py),pile_w/2,lw=1.5,edgecolor='#2c3e50',facecolor='#34495e',alpha=0.6)
                 if pile_shape=="Circular Pile" else
                 patches.Rectangle((px-pile_w/2,py-pile_l/2),pile_w,pile_l,
                                    lw=1.5,edgecolor='#2c3e50',facecolor='#34495e',alpha=0.6))
        ax.add_patch(patch)
        ax.text(px,py,f"P{i+1}",ha='center',va='center',color='white',fontsize=9,fontweight='bold')
    ax.plot(cgx,cgy,'X',color='#e67e22',ms=10,label=f'C.G.({cgx:.2f},{cgy:.2f})')
    ax.axhline(0,color='k',lw=0.5,ls='--'); ax.axvline(0,color='k',lw=0.5,ls='--')
    ax.set(xlabel='X (m)',ylabel='Y (m)',title='As-Built Plan — Eccentricity Map')
    ax.axis('equal'); ax.grid(True,ls=':',alpha=0.6); ax.legend(fontsize=8)
    return fig

def fig_section(t, bmax, cover, embed, db, nbx, spx, cx, cy, top_steel):
    fig,ax = plt.subplots(figsize=(8,5)); ax.set_aspect('equal')
    c,e,d = cover/100, embed/100, db/1000
    ax.add_patch(patches.Rectangle((-bmax/2,0),bmax,t,lw=2,edgecolor='#2c3e50',facecolor='#eaeded'))
    ax.add_patch(patches.Rectangle((-cx/2,t),cx,0.4,lw=2,edgecolor='#7e1e1e',facecolor='#f2d7d5'))
    for xp in [-bmax/3-0.15, bmax/3-0.15]:
        ax.add_patch(patches.Rectangle((xp,-0.2),0.3,0.2+e,fc='#bdc3c7',ec='#34495e',lw=1.5))
    bz = e+c+d/2; lx,rx = -bmax/2+c, bmax/2-c
    ax.plot([lx,rx],[bz,bz],color='#c0392b',lw=2.5,label=f'เหล็กล่าง DB{db}')
    ax.plot([lx,lx],[bz,bz+min(0.3,t-2*c-e)],color='#c0392b',lw=2.5)
    ax.plot([rx,rx],[bz,bz+min(0.3,t-2*c-e)],color='#c0392b',lw=2.5)
    for rx2 in np.linspace(lx+c,rx-c,min(nbx,15)):
        ax.plot(rx2,bz+d,'o',color='#2c3e50',ms=4)
    if top_steel:
        tz = t-c-d/2
        ax.plot([lx,rx],[tz,tz],color='#2980b9',lw=2,label='เหล็กบน')
        ax.plot([lx,lx],[tz,tz-min(0.3,t-2*c-e)],color='#2980b9',lw=2)
        ax.plot([rx,rx],[tz,tz-min(0.3,t-2*c-e)],color='#2980b9',lw=2)
    ax.text(0,-0.3,f'B_max={bmax:.2f}m',ha='center',fontsize=10,fontweight='bold')
    ax.text(rx+0.1,t/2,f't={t:.2f}m',fontsize=9,fontweight='bold',va='center')
    ax.set_title(f'Section: {nbx}-DB{db} @ {spx:.0f}cm',fontsize=11,fontweight='bold')
    ax.axis('off'); ax.legend(fontsize=8,framealpha=0.8)
    return fig

@st.cache_data(show_spinner=False)
def fig_3d(verts_t, t, cx, cy, piles_t, pile_shape, pile_w, pile_l, embed, cols_t):
    verts = list(verts_t); piles = list(piles_t); cols = list(cols_t)
    def prism(vs, z0, z1, color, op, name, sl=True):
        n = len(vs)
        x = [v[0] for v in vs]*2; y = [v[1] for v in vs]*2
        z = [z0]*n+[z1]*n
        ii,jj,kk = [],[],[]
        for k in range(1,n-1):
            ii.extend([0,n]); jj.extend([k,n+k+1]); kk.extend([k+1,n+k])
        for k in range(n):
            nk=(k+1)%n
            ii.extend([k,k]); jj.extend([nk,n+nk]); kk.extend([n+nk,n+k])
        return go.Mesh3d(x=x,y=y,z=z,i=ii,j=jj,k=kk,color=color,opacity=op,
                         name=name,showlegend=sl,
                         lighting=dict(ambient=0.6,diffuse=0.8,roughness=0.4))
    fig = go.Figure()
    zb = -t
    fig.add_trace(prism(verts,zb,0,'#2ecc71',0.45,'คอนกรีตฐานราก'))
    for cx_c,cy_c in cols:
        fig.add_trace(prism([(cx_c-cx/2,cy_c-cy/2),(cx_c+cx/2,cy_c-cy/2),
                              (cx_c+cx/2,cy_c+cy/2),(cx_c-cx/2,cy_c+cy/2)],
                            0,0.4,'#e74c3c',0.75,'เสาตอม่อ',sl=False))
    for i,(px,py) in enumerate(piles):
        pvs = ([(px+pile_w/2*math.cos(a),py+pile_w/2*math.sin(a))
                for a in np.linspace(0,2*np.pi,8,endpoint=False)]
               if pile_shape=="Circular Pile" else
               [(px-pile_w/2,py-pile_l/2),(px+pile_w/2,py-pile_l/2),
                (px+pile_w/2,py+pile_l/2),(px-pile_w/2,py+pile_l/2)])
        fig.add_trace(prism(pvs,zb-0.8,zb+embed,'#7f8c8d',0.8,f'P{i+1}',sl=False))
        fig.add_trace(go.Scatter3d(x=[px],y=[py],z=[zb+embed+0.05],mode='text',
                      text=[f"P{i+1}"],textfont=dict(size=10),showlegend=False))
    fig.update_layout(scene=dict(xaxis_title='X(m)',yaxis_title='Y(m)',zaxis_title='Z(m)',aspectmode='data'),
                      margin=dict(l=0,r=0,b=0,t=30))
    return fig

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR INPUTS
# ──────────────────────────────────────────────────────────────────────────────
sb = st.sidebar
sb.header("🏗️ Pile Cap Footing — V10")
shape_type = sb.selectbox("รูปทรงฐานราก:", [
    "Truncated Triangular Footing","Rectangular Footing",
    "Combined Footing (>= 2 Columns)","Strap Footing (ชิดเขต)",
    "Arbitrary Freeform Polygon"], index=0)
col_pos = sb.selectbox("ตำแหน่งเสาตอม่อ:", ["Interior","Edge","Corner"])

sb.subheader("🧱 วัสดุ & หน้าตัด")
fc   = sb.number_input("fc' (ksc)", 150, 700, 280, 10)
fy   = sb.number_input("fy  (ksc)", 2400, 6000, 4000, 100)
cx   = sb.number_input("cx ตอม่อแกน X (m)", 0.10, value=0.35, step=0.05)
cy   = sb.number_input("cy ตอม่อแกน Y (m)", 0.10, value=0.35, step=0.05)

sb.subheader("⚖️ Load Factors")
fac_dl = sb.number_input("γ_DL", value=1.2, step=0.1)
fac_ll = sb.number_input("γ_LL", value=1.6, step=0.1)

sb.subheader("🌪️ Horizontal & Torsion")
V_x = sb.number_input("V_x (ton)", value=0.0)
V_y = sb.number_input("V_y (ton)", value=0.0)
T_z = sb.number_input("T_z (ton-m)", value=0.0)

sb.subheader("💧 รอยร้าว")
env_cond  = sb.selectbox("สภาวะ:", ["ทั่วไป (Max 0.30mm)","โครงสร้างกันน้ำ (Max 0.15mm)"])
w_allow   = 0.15 if "กันน้ำ" in env_cond else 0.30

sb.subheader("🔩 เสาเข็ม")
pile_shape = sb.selectbox("รูปทรงเข็ม:", ["Circular Pile","Square/Rectangular Pile"])
pile_dia   = sb.number_input("ขนาดเข็ม (m)", 0.15, value=0.30, step=0.05)
pile_cap   = sb.number_input("กำลังรับแรงอัด (ton/ต้น)", value=30.0)
ten_cap    = sb.number_input("กำลังรับแรงถอน (ton/ต้น)", value=10.0)
pile_ks    = sb.number_input("ks (ton/m)", value=20000.0, step=1000.0)

S = 3.0*pile_dia; E = 0.40                          # default spacing & edge distance
cols_list = [(0.0,0.0)]

# ── Shape-dependent geometry setup ──
if shape_type == "Truncated Triangular Footing":
    n_piles = 3
    piles_ideal = [(0,S/math.sqrt(3)),(-S/2,-S/(2*math.sqrt(3))),(S/2,-S/(2*math.sqrt(3)))]
    R,Y,X,tr = S/math.sqrt(3)+E, -(S/(2*math.sqrt(3)))-E, S/2+E, 0.20
    verts_base = [(-tr,R),(tr,R),(X,Y+tr),(X-tr,Y),(-X+tr,Y),(-X,Y+tr)]
    B_vis = X*2

elif shape_type == "Rectangular Footing":
    n_piles = sb.selectbox("จำนวนเข็ม:", [2,4,5,6,8,9], index=1)
    if   n_piles==2: piles_ideal = [(-S/2,0),(S/2,0)]
    elif n_piles==4: piles_ideal = [(-S/2,-S/2),(S/2,-S/2),(-S/2,S/2),(S/2,S/2)]
    elif n_piles==5: piles_ideal = [(-S/2,-S/2),(S/2,-S/2),(0,0),(-S/2,S/2),(S/2,S/2)]
    elif n_piles==6: piles_ideal = [(-S,-S/2),(0,-S/2),(S,-S/2),(-S,S/2),(0,S/2),(S,S/2)]
    elif n_piles==8: piles_ideal = [(-S,-S),(-S,0),(-S,S),(0,-S),(0,S),(S,-S),(S,0),(S,S)]
    else:            piles_ideal = [(-S,-S),(0,-S),(S,-S),(-S,0),(0,0),(S,0),(-S,S),(0,S),(S,S)]
    Bf,Lf = S+2*E, S+2*E
    verts_base = [(-Bf/2,-Lf/2),(Bf/2,-Lf/2),(Bf/2,Lf/2),(-Bf/2,Lf/2)]
    B_vis = Bf

elif shape_type == "Combined Footing (>= 2 Columns)":
    n_piles = 6
    piles_ideal = [(-1.2,-0.6),(0.0,-0.6),(1.2,-0.6),(-1.2,0.6),(0.0,0.6),(1.2,0.6)]
    cols_list = [(-1.0,0.0),(1.0,0.0)]
    verts_base = [(-2.0,-1.2),(2.0,-1.2),(2.0,1.2),(-2.0,1.2)]
    B_vis = 4.0

elif shape_type == "Strap Footing (ชิดเขต)":
    n_piles = 4
    piles_ideal = [(-1.5,-0.5),(-1.5,0.5),(1.5,-0.5),(1.5,0.5)]
    cols_list = [(-1.8,0.0),(1.5,0.0)]
    verts_base = [(-2.3,-1.0),(2.3,-1.0),(2.3,1.0),(-2.3,1.0)]
    B_vis = 4.6

else:  # Freeform
    n_piles = sb.number_input("จำนวนเข็ม:", 1, 20, 4, 1)
    piles_ideal = []
    nc,nr = math.ceil(math.sqrt(n_piles)), math.ceil(n_piles/math.ceil(math.sqrt(n_piles)))
    idx = 0
    for r in range(nr):
        for c in range(nc):
            if idx < n_piles:
                piles_ideal.append(((c-(nc-1)/2)*0.9,(r-(nr-1)/2)*0.9)); idx+=1
    sb.write("จุดยอดฐานราก (ทวนเข็มนาฬิกา):")
    if "poly_verts" not in st.session_state:
        st.session_state.poly_verts = pd.DataFrame({'X(m)':[-1.5,0.5,0.5,1.5,1.5,-1.5],'Y(m)':[1.5,1.5,-0.5,-0.5,-1.5,-1.5]})
    ev = sb.data_editor(st.session_state.poly_verts, num_rows="dynamic", key="poly_ed")
    st.session_state.poly_verts = ev
    verts_base = list(zip(ev['X(m)'],ev['Y(m)']))
    if len(verts_base) < 3: st.error("ต้องมี ≥ 3 จุด"); st.stop()
    B_vis = max(v[0] for v in verts_base)-min(v[0] for v in verts_base) if verts_base else 3.0

sb.subheader("3. น้ำหนักบรรทุก")
DL      = sb.number_input("Dead Load (ton)", value=55.0)
LL      = sb.number_input("Live Load (ton)", value=30.0)
Mcx_dl  = sb.number_input("M_DL_x (ton-m)", value=6.0)
Mcy_dl  = sb.number_input("M_DL_y (ton-m)", value=5.0)
Mcx_ll  = sb.number_input("M_LL_x (ton-m)", value=4.0)
Mcy_ll  = sb.number_input("M_LL_y (ton-m)", value=3.0)
soil_d  = sb.number_input("ความลึกดิน (m)", value=1.0)
soil_γ  = sb.number_input("หน่วยน้ำหนักดิน (ton/m³)", value=1.8)
bar_dia = sb.selectbox("DB เหล็กเสริม (mm)", [12,16,20,25,28,32], index=2)

t_mode  = sb.radio("โหมดความหนา t:", ["Auto-Optimize","Manual Override"])
t_man   = sb.number_input("t ฐานราก (m)", value=0.65, min_value=0.30) if t_mode=="Manual Override" else 0.65
embed_cm, cover_cm = 5.0, 7.5

phi_s, phi_f = 0.75, 0.90
ab = math.pi*(bar_dia/10)**2/4

# ──────────────────────────────────────────────────────────────────────────────
# MAIN PROCESSING
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 📍 As-Built Pile Survey")

# FIX 9: Only reset pile data if footing TYPE or PILE COUNT changes
key_id = f"{shape_type}|{n_piles}"
if st.session_state.get("_pile_key") != key_id:
    st.session_state["_pile_key"] = key_id
    st.session_state.pile_df = pd.DataFrame({
        'ชื่อเข็ม': [f"P{i+1}" for i in range(n_piles)],
        'Ideal X':  [round(p[0],3) for p in piles_ideal],
        'Ideal Y':  [round(p[1],3) for p in piles_ideal],
        'ΔX (m)':   [0.0]*n_piles,
        'ΔY (m)':   [0.0]*n_piles,
    })

ed = st.data_editor(st.session_state.pile_df, disabled=['ชื่อเข็ม','Ideal X','Ideal Y'],
                    hide_index=True, use_container_width=True, key="pile_editor")
st.session_state.pile_df = ed

piles_act = [(r['Ideal X']+r['ΔX (m)'], r['Ideal Y']+r['ΔY (m)']) for _,r in ed.iterrows()]
cgx = sum(p[0] for p in piles_act)/n_piles
cgy = sum(p[1] for p in piles_act)/n_piles
ecc_x, ecc_y = cgx, cgy
piles_rel = [(p[0]-cgx, p[1]-cgy) for p in piles_act]
Iyy_grp = max(1e-6, sum(p[0]**2 for p in piles_rel))
Ixx_grp = max(1e-6, sum(p[1]**2 for p in piles_rel))

# Factored loads
P_ult  = fac_dl*DL + fac_ll*LL
Mu_cx  = fac_dl*Mcx_dl + fac_ll*Mcx_ll
Mu_cy  = fac_dl*Mcy_dl + fac_ll*Mcy_ll
Ms_cx  = Mcx_dl + Mcx_ll
Ms_cy  = Mcy_dl + Mcy_ll

# Shift vertices so group C.G. is at origin
verts = [(v[0]-ecc_x, v[1]-ecc_y) for v in verts_base]

# Validate all piles inside footing
poly_chk = Path(verts)
bad_piles = [f"P{i+1}" for i,p in enumerate(piles_act)
             if not poly_chk.contains_point(p, radius=0.01)]
if bad_piles:
    st.error(f"🚨 เสาเข็ม {', '.join(bad_piles)} อยู่นอกขอบฐานราก!")

area = polygon_area(verts)
# FIX 3: subtract ALL column footprints
W_soil = max(0.0, area - len(cols_list)*cx*cy) * soil_d * soil_γ

# Thickness optimisation
if t_mode == "Auto-Optimize":
    d_try = 0.30; t_safe = False; loops = 0
    while not t_safe and loops < 200:
        t_try = d_try + max(cover_cm, embed_cm)/100 + bar_dia/2000
        t_safe, *_ = shear_check(
            d_try, t_try, area, W_soil, P_ult, Mu_cx, Mu_cy,
            ecc_x, ecc_y, piles_act, Ixx_grp, Iyy_grp, cx, cy, fc,
            col_pos, verts, fac_dl, cols_list, pile_dia, pile_ks, ten_cap)
        if not t_safe: d_try += 0.02
        loops += 1
    if not t_safe: st.error("🚨 ไม่สามารถหาความหนาที่ปลอดภัยได้ — เพิ่มขนาดเสาเข็มหรือจำนวนเข็ม"); st.stop()
    t_actual = math.ceil((d_try + max(cover_cm,embed_cm)/100 + bar_dia/2000)*20)/20
    d_actual = eff_depth(t_actual, cover_cm, embed_cm, bar_dia)
else:
    t_actual = t_man
    d_actual = eff_depth(t_actual, cover_cm, embed_cm, bar_dia)

(safe, vu_col, phivc_col, vu_pile, phivc_pile,
 vu_wb, phivc_wb, p_ult_out, Mxs, Mys, V_fdm) = shear_check(
    d_actual, t_actual, area, W_soil, P_ult, Mu_cx, Mu_cy,
    ecc_x, ecc_y, piles_act, Ixx_grp, Iyy_grp, cx, cy, fc,
    col_pos, verts, fac_dl, cols_list, pile_dia, pile_ks, ten_cap)

# Service reactions
P_svc = DL + LL + area*t_actual*2.4 + W_soil
p_svc_out, Ms_xfdm, Ms_yfdm, _ = compute_flexible_reactions(
    verts, piles_act, cols_list, P_svc, Ms_cx, Ms_cy, t_actual, fc, pile_ks, ten_cap)

wu_ftg  = fac_dl*(area*t_actual*2.4)
wu_soil = fac_dl*W_soil
P_u_tot = P_ult + wu_ftg + wu_soil

# Horizontal shear distribution
polar_R = max(sum(rx**2+ry**2 for rx,ry in piles_rel), 1e-6)
h_shear = [math.hypot((V_x/n_piles)-T_z*ry/polar_R,
                       (V_y/n_piles)+T_z*rx/polar_R) for rx,ry in piles_rel]

# Equilibrium warning
R_sum = sum(p_ult_out)
if P_u_tot > 0 and abs(R_sum - P_u_tot)/P_u_tot > 0.10:
    st.warning(f"⚠️ FDM equilibrium gap: ΣR={R_sum:.1f} t vs P_total={P_u_tot:.1f} t "
               f"({abs(R_sum-P_u_tot)/P_u_tot*100:.1f}%). "
               "พิจารณาเพิ่มความหนา t หรือ ks.")

# Rebar design
# Use service moment to estimate fs for crack-control spacing
fs_est = min((Ms_xfdm*1e5)/(max(1.0,(10*ab))*0.85*d_actual*100)*0.0981, 240.0) if Ms_xfdm > 0 else 200.0
wx = section_width_at_y(0, verts)*100
nbx,spx,_,Asrx = design_rebar(Mxs, wx, d_actual*100, t_actual*100, fc, fy,
                                phi_f, ab, cover_cm, env_cond, fs_est)
wy = min(section_height_at_x(-cx/2,verts), section_height_at_x(cx/2,verts))*100
nby,spy,_,Asry = design_rebar(Mys, wy, d_actual*100, t_actual*100, fc, fy,
                                phi_f, ab, cover_cm, env_cond, fs_est)

w_crack = crack_width_gl(Ms_xfdm, nbx*ab, d_actual*100, cover_cm, bar_dia, spx)
has_tens = any(r < 0 for r in p_ult_out)
top_steel = has_tens or t_actual >= 0.60

# ── Development length check ──
ld_req = dev_length_cm(fy, fc, bar_dia)
# Cantilever from column face to footing edge
cant_x = max(abs(v[0]) for v in verts) - cx/2
cant_y = max(abs(v[1]) for v in verts) - cy/2
avail_x = cant_x*100 - cover_cm
avail_y = cant_y*100 - cover_cm

# ──────────────────────────────────────────────────────────────────────────────
# RESULTS  UI
# ──────────────────────────────────────────────────────────────────────────────
tab_rep, tab_calc, tab_vis = st.tabs([
    "📊 รายงานผลสรุป",
    "📄 รายการคำนวณ (Step-by-Step)",
    "🗺️ Engineering Visuals"])

with tab_rep:
    st.markdown("## 📊 สรุปผลการออกแบบฐานราก (Design Summary)")
    
    # แจ้งเตือนเสาเข็มรับแรงถอน
    tension_warn = [f"P{i+1} ({abs(r):.2f}t)" for i,r in enumerate(p_svc_out) if r < -ten_cap]
    if tension_warn: 
        st.error(f"🚨 เสาเข็มรับแรงถอนเกิน {ten_cap}t: {', '.join(tension_warn)}")

    # 1. แถบแสดงข้อมูลหลัก (Top Level Metrics)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("พื้นที่ฐานราก (Area)", f"{area:.2f} m²")
    m2.metric("ความหนา (t)", f"{t_actual:.2f} m")
    m3.metric("ความลึกประสิทธิผล (d)", f"{d_actual:.3f} m")
    m4.metric("น้ำหนักบรรทุกรวม (ΣPu)", f"{P_u_tot:.1f} ton")

    st.divider()

    c1, c2 = st.columns([1.2, 1.0])
    
    with c1:
        st.subheader("🛡️ ผลการตรวจสอบกำลังรับน้ำหนัก (Design Checks)")
        
        # แรงเฉือน (Shear)
        st.markdown("#### 1. การรับแรงเฉือน (Shear Capacity)")
        shear_data = [
            ("Punching Shear (รอบตอม่อ)", vu_col, phivc_col),
            ("Punching Shear (รอบเสาเข็ม)", vu_pile, phivc_pile),
            ("Wide-Beam Shear (เฉือนทางเดียว)", vu_wb, phivc_wb)
        ]
        for lbl, vu, phivc in shear_data:
            ok = vu <= phivc
            status = "✅ **PASS**" if ok else "❌ **FAIL**"
            st.markdown(f"- **{lbl}:** $v_u = {vu:.3f}$ ksc $\\le \\phi v_c = {phivc:.3f}$ ksc {status}")

        # เหล็กเสริม (Flexure)
        st.markdown("#### 2. เหล็กเสริมรับโมเมนต์ดัด (Flexural Reinforcement)")
        st.markdown(f"- **แกน X:** $M_{{ux}}^* = {Mxs:.3f}$ t·m/m $\\rightarrow$ **ใช้ {nbx}-DB{bar_dia} @ {spx:.0f} cm**")
        st.markdown(f"- **แกน Y:** $M_{{uy}}^* = {Mys:.3f}$ t·m/m $\\rightarrow$ **ใช้ {nby}-DB{bar_dia} @ {spy:.0f} cm**")

        # ข้อกำหนดพิเศษ (Serviceability & Detailing)
        st.markdown("#### 3. ข้อกำหนดพิเศษ (Serviceability & Detailing)")
        ok_cr = w_crack <= w_allow
        cr_stat = "✅ **PASS**" if ok_cr else "❌ **EXCEEDED**"
        st.markdown(f"- **รอยร้าว (Crack Width):** $w = {w_crack:.3f}$ mm $\\le {w_allow}$ mm {cr_stat}")
        
        st.markdown(f"- **ระยะฝังยึดเหนี่ยว (Development Length):** ต้องการ $L_d = {ld_req:.1f}$ cm")
        for dr, av in [("X", avail_x), ("Y", avail_y)]:
            ok_ld = av >= ld_req
            ld_stat = "✅ **OK**" if ok_ld else "⚠️ **ต้องงอขอ (Hook Required)**"
            st.markdown(f"  - ทิศทาง {dr}: มีระยะให้ฝังได้ $= {av:.1f}$ cm $\\rightarrow$ {ld_stat}")

    with c2:
        st.subheader("🎯 แรงปฏิกิริยาเสาเข็ม (Pile Reactions)")
        
        # เช็คสมดุลแรง
        gap_pct = abs(R_sum - P_u_tot) / max(P_u_tot, 0.001) * 100
        st.info(f"**Equilibrium Check:** ΣR (FDM) = {R_sum:.2f} ton vs $P_{{total}}$ = {P_u_tot:.2f} ton (Gap: {gap_pct:.1f}%)")
        
        # ตารางผลลัพธ์เสาเข็ม
        df_r = pd.DataFrame({
            'เสาเข็ม': ed['ชื่อเข็ม'],
            'Ru (ton)': [f"{r:.2f}" for r in p_ult_out],
            'Rs (ton)': [f"{r:.2f}" for r in p_svc_out],
            'Ru/Cap':   [f"{r/pile_cap:.2f}" if pile_cap>0 else "-" for r in p_ult_out],
            'V_horiz (ton)': [f"{v:.3f}" for v in h_shear],
        })
        st.dataframe(df_r, hide_index=True, use_container_width=True)
        
        # สรุปน้ำหนักลงเข็ม
        max_ru = max(p_ult_out) if p_ult_out else 0
        min_ru = min(p_ult_out) if p_ult_out else 0
        st.markdown(f"**> Ru สูงสุด:** {max_ru:.2f} ton")
        st.markdown(f"**> Ru ต่ำสุด:** {min_ru:.2f} ton")
        
        if max_ru > pile_cap:
            st.error(f"🚨 เสาเข็มรับน้ำหนักเกินกำลัง (Overloaded)! ({max_ru:.2f} > {pile_cap} ton)")
        else:
            st.success("✅ เสาเข็มทุกต้นรับน้ำหนักได้ปลอดภัย")

with tab_calc:
    st.markdown("## 📄 รายการคำนวณแบบละเอียด — ACI 318-19 (MKS Units)")
    st.markdown("**ระเบียบวิธีวิเคราะห์:** Winkler Flexible Plate (FDM) เปรียบเทียบกับ Rigid Pile Cap Method")
    st.divider()

    # =========================================================
    # 1. Properties
    # =========================================================
    st.markdown("### 1. ข้อมูลคุณสมบัติวัสดุและความลึกประสิทธิผล (Material Properties & Effective Depth)")
    
    st.markdown("**กำลังของวัสดุที่ใช้ในการออกแบบ:**")
    st.latex(rf"f'_c = {fc}\text{{ ksc}},\quad f_y = {fy}\text{{ ksc}}")
    
    st.markdown("**มิติและระยะหุ้มคอนกรีต (Geometry & Coverings):**")
    st.latex(rf"t = {t_actual:.3f}\text{{ m}},\quad \text{{Cover}} = {cover_cm:.1f}\text{{ cm}},\quad \text{{Embed}} = {embed_cm:.1f}\text{{ cm}},\quad d_b = {bar_dia}\text{{ mm}}")
    
    st.markdown("**คำนวณหาความลึกประสิทธิผลของฐานราก ($d$):**")
    st.latex(r"d = t - \frac{\max(\text{Cover}, \text{Embed})}{100} - \frac{d_b}{2000}")
    st.latex(rf"d = {t_actual:.3f} - \frac{{\max({cover_cm:.1f}, {embed_cm:.1f})}}{{100}} - \frac{{{bar_dia}}}{{2000}} = \mathbf{{{d_actual:.3f}\text{{ m}}}}")
    st.divider()

    # =========================================================
    # 2. Pile Group C.G. & Factored Loads
    # =========================================================
    st.markdown("### 2. ศูนย์ถ่วงกลุ่มเสาเข็ม และ น้ำหนักบรรทุกประลัย (Pile C.G. & Factored Loads)")
    
    # 2.1 หาจุดศูนย์ถ่วงกลุ่มเสาเข็ม (Pile Group C.G.)
    st.markdown("#### 2.1 การหาจุดศูนย์ถ่วงกลุ่มเสาเข็มด้วยเวกเตอร์ตำแหน่ง (Position Vectors)")
    st.markdown("นิยามเวกเตอร์ตำแหน่งของเสาเข็มต้นที่ $i$ ใดๆ เทียบกับจุดหมุนอ้างอิง และหาค่าเฉลี่ยเซนทรอยด์:")
    st.latex(r"\vec{r}_i = \begin{bmatrix} x_i \\ y_i \end{bmatrix} \quad \text{และ} \quad \vec{{R}}_{{c.g.}} = \frac{1}{n} \sum_{i=1}^{n} \vec{r}_i")
    
    # ดึงพิกัดเพื่อแสดงผลเวกเตอร์
    sum_x = sum(p[0] for p in piles_act)
    sum_y = sum(p[1] for p in piles_act)
    
    if len(piles_act) <= 6:
        vec_str = " + ".join([f"\\begin{{bmatrix}} {p[0]:.3f} \\\\ {p[1]:.3f} \\end{{bmatrix}}" for p in piles_act])
    else:
        vec_str = f"\\begin{{bmatrix}} {piles_act[0][0]:.3f} \\\\ {piles_act[0][1]:.3f} \\end{{bmatrix}} + \\begin{{bmatrix}} {piles_act[1][0]:.3f} \\\\ {piles_act[1][1]:.3f} \\end{{bmatrix}} + \\dots + \\begin{{bmatrix}} {piles_act[-1][0]:.3f} \\\\ {piles_act[-1][1]:.3f} \\end{{bmatrix}}"
        
    st.latex(rf"\vec{{R}}_{{c.g.}} = \frac{{1}}{{{n_piles}}} \left( {vec_str} \right)")
    st.latex(rf"\vec{{R}}_{{c.g.}} = \frac{{1}}{{{n_piles}}} \begin{{bmatrix}} {sum_x:.3f} \\\\ {sum_y:.3f} \end{{bmatrix}} = \begin{{bmatrix}} \mathbf{{{cgx:.3f}}} \\\\ \mathbf{{{cgy:.3f}}} \end{{bmatrix}}\text{{ m}}")

    # 2.2 น้ำหนักบรรทุกประลัย (Factored Loads)
    st.markdown("#### 2.2 น้ำหนักบรรทุกประลัยรวม และระยะเยื้องศูนย์ (Total Factored Loads & Eccentricity)")
    st.markdown("คำนวณน้ำหนักบรรทุกประลัยจากเสาตอหม้อ น้ำหนักฐานราก และน้ำหนักดินกลบ:")
    st.latex(rf"P_{{ult}} = {fac_dl}(DL) + {fac_ll}(LL) = {fac_dl}({DL}) + {fac_ll}({LL}) = {P_ult:.2f}\text{{ ton}}")
    st.latex(rf"W_{{ftg}} = 1.2 \times (A \times t \times \gamma_c) = 1.2 \times ({area:.2f} \times {t_actual:.3f} \times 2.4) = {wu_ftg:.2f}\text{{ ton}}")
    st.latex(rf"W_{{soil}} = 1.2 \times (A_{{soil}} \times D_{{soil}} \times \gamma_s) = 1.2 \times {W_soil:.2f} = {wu_soil:.2f}\text{{ ton}}")
    st.latex(rf"\Sigma P_u = P_{{ult}} + W_{{ftg}} + W_{{soil}} = \mathbf{{{P_u_tot:.2f}\text{{ ton}}}}")
    
    st.markdown("ระยะเยื้องศูนย์ลัพธ์ของน้ำหนักบรรทุกเทียบกับจุดศูนย์ถ่วงกลุ่มเสาเข็ม:")
    st.latex(rf"e_x = {ecc_x:.3f}\text{{ m}},\quad e_y = {ecc_y:.3f}\text{{ m}}")
    st.divider()

    # =========================================================
    # 3. Vector-Matrix Derivation (Rigid Cap)
    # =========================================================
    st.markdown("### 3. การพิสูจน์สมการแรงปฏิกิริยาเสาเข็มด้วยเวกเตอร์ (Rigid Cap Formulation)")
    st.markdown("**สมมติฐาน:** ฐานรากแข็งเกร็งสมบูรณ์ (Rigid Body) และเสาเข็มทุกต้นมีค่าความขดแข็งสปริงในแนวดิ่ง ($k$) เท่ากัน")

    st.markdown("**ขั้นตอนที่ 1: ความสัมพันธ์ทางคณิตศาสตร์ของการกระจัด (Kinematics)**")
    st.markdown("ย้ายจุดกำเนิดระบบพิกัดมาที่จุด C.G. ของกลุ่มเสาเข็ม ระยะทรุดตัวของเสาเข็มต้นที่ $i$ ($\delta_i$) จะสัมพันธ์กับการเคลื่อนตัวแนวดิ่ง ($\Delta_z$) และการหมุนรอบแกน ($\vec{\theta}$):")
    st.latex(r"\text{เวกเตอร์ตำแหน่งเทียบ C.G.: } \vec{r}_i = \begin{bmatrix} x_i \\ y_i \end{bmatrix}, \quad \text{เวกเตอร์การหมุน: } \vec{\theta} = \begin{bmatrix} \theta_y \\ \theta_x \end{bmatrix}")
    st.latex(r"\text{ระยะทรุดตัวเสาเข็ม: } \delta_i = \Delta_z + \vec{\theta} \cdot \vec{r}_i = \Delta_z + \theta_y x_i + \theta_x y_i")

    st.markdown("**ขั้นตอนที่ 2: ความสัมพันธ์ระหว่างแรงและการกระจัด (Constitutive Law)**")
    st.latex(r"R_i = k \cdot \delta_i = k (\Delta_z + \theta_y x_i + \theta_x y_i)")

    st.markdown("**ขั้นตอนที่ 3: สมการสมดุลแรงในแนวดิ่ง (Vertical Equilibrium)**")
    st.latex(r"\sum_{i=1}^{n} R_i = \Sigma P_u \Rightarrow \sum_{i=1}^{n} k(\Delta_z + \theta_y x_i + \theta_x y_i) = \Sigma P_u")
    st.markdown("เนื่องจากแกนอ้างอิงอยู่ที่จุด C.G. ส่งผลให้ผลรวมพิกัด $\sum x_i = 0$ และ $\sum y_i = 0$ (พจน์คูณโมเมนต์ของการหมุนจึงตัดกันเป็นศูนย์):")
    st.latex(r"n \cdot k \cdot \Delta_z = \Sigma P_u \Rightarrow \Delta_z = \frac{\Sigma P_u}{n \cdot k}")

    st.markdown("**ขั้นตอนที่ 4: สมการสมดุลโมเมนต์ในรูปเมทริกซ์ (Moment Equilibrium Matrix)**")
    st.latex(r"\vec{M}_{cg} = \begin{bmatrix} M_y \\ M_x \end{bmatrix} = \sum_{i=1}^{n} R_i \vec{r}_i = k \sum_{i=1}^{n} (\Delta_z + \theta_y x_i + \theta_x y_i) \begin{bmatrix} x_i \\ y_i \end{bmatrix}")
    st.markdown("จัดรูปสมการให้อยู่ในรูปเมทริกซ์ความเฉื่อยของกลุ่มเสาเข็ม (Pile Group Inertia Matrix, $\mathbf{J}$):")
    st.latex(r"\begin{bmatrix} M_y \\ M_x \end{bmatrix} = k \begin{bmatrix} \sum x_i^2 & \sum x_i y_i \\ \sum x_i y_i & \sum y_i^2 \end{bmatrix} \begin{bmatrix} \theta_y \\ \theta_x \end{bmatrix} = k \mathbf{J} \vec{\theta}")
    
    st.markdown("สำหรับกลุ่มเสาเข็มที่วางตัวสมมาตร ค่าผลคูณร่วมพิกัดเยื้องเชิงเส้น $\sum x_i y_i = 0$ จะได้เวกเตอร์มุมหมุนคือ:")
    st.latex(r"\theta_y = \frac{M_y}{k \sum x_i^2}, \quad \theta_x = \frac{M_x}{k \sum y_i^2}")

    st.markdown("**ขั้นตอนที่ 5: สมการคำนวณแรงปฏิกิริยาสรุป (Final Rigid Cap Equation)**")
    st.markdown("แทนค่าการเคลื่อนตัว $\Delta_z, \theta_y, \theta_x$ กลับลงไปในสมการแรงกดของเข็ม (ค่าความแข็งสปริง $k$ จะตัดกันหมดไปเอง):")
    st.latex(r"R_i = \frac{\Sigma P_u}{n} + \frac{M_y}{\sum x_i^2}x_i + \frac{M_x}{\sum y_i^2}y_i")
    st.latex(r"\text{หรือเขียนในรูปแบบเวกเตอร์-เมทริกซ์สากล: } R_i = \frac{\Sigma P_u}{n} + \vec{M}_{cg}^T \mathbf{J}^{-1} \vec{r}_i")
    st.divider()

    # =========================================================
    # 3.1 การพิสูจน์สูตรจากสมดุลโมเมนต์ (PiRi = MR Formulation)
    # =========================================================
    st.markdown("---")
    st.markdown("### 3.1 การพิสูจน์สูตรแรงปฏิกิริยาจากสมดุลโมเมนต์ ($\sum P_i r_i = M_R$)")
    st.markdown("พิจารณาพฤติกรรมของฐานรากแข็งเกร็งรับโมเมนต์ดัดดั้งเดิม โดยกำหนดให้พิกัดอ้างอิงเริ่มต้นที่จุดศูนย์ถ่วง (C.G.) ของกลุ่มเสาเข็ม")
    
    st.markdown("**ขั้นที่ 1: สมมติฐานพฤติกรรมเชิงเส้น (Kinematic Assumption)**")
    st.markdown("เนื่องจากฐานรากมีความแข็งเกร็งสมบูรณ์ (Rigid Cap) ระยะทรุดตัวหรือแรงต้านในเสาเข็มต้นที่ $i$ ($P_i$) จะแปรผันเป็นเส้นตรงตามระยะห่างจากจุดศูนย์ถ่วง ($r_i$)")
    st.latex(r"P_i \propto r_i \quad \implies \quad P_i = k \cdot r_i")
    st.markdown("เมื่อ $k$ คือค่าคงที่สัดส่วนความลาดชันของแรง (Proportionality Constant)")

    st.markdown("**ขั้นที่ 2: สมการสมดุลโมเมนต์ลัพธ์ (Moment Equilibrium)**")
    st.markdown("โมเมนต์ต้านทานภายในที่เกิดจากแรงในเสาเข็มทุกต้นรวมกัน จะต้องมีค่าเท่ากับโมเมนต์ลัพธ์ภายนอก ($M_R$) ที่มากระทำพอดี:")
    st.latex(r"\sum_{i=1}^{n} (P_i \cdot r_i) = M_R")
    st.markdown("นี่คือสมการสมดุลหลักในรูปแบบ $\sum P_i r_i = M_R$")

    st.markdown("**ขั้นที่ 3: แทนค่าเพื่อหาค่าคงที่ $k$ (Substitution & Solving for $k$)**")
    st.markdown("แทนค่า $P_i = k \cdot r_i$ ลงในสมการสมดุลโมเมนต์ด้านบน:")
    st.latex(r"\sum_{i=1}^{n} (k \cdot r_i \cdot r_i) = M_R")
    st.latex(r"k \sum_{i=1}^{n} r_i^2 = M_R \quad \implies \quad k = \frac{M_R}{\sum_{i=1}^{n} r_i^2}")

    st.markdown("**ขั้นที่ 4: สมการสำเร็จรูปสำหรับแรงในเสาเข็ม (Final Formula for Pile Force)**")
    st.markdown("นำค่าคงที่ $k$ ที่คำนวณได้ ย้อนกลับไปแทนในสมมติฐานเริ่มต้น ($P_i = k \cdot r_i$) จะได้สูตรการกระจายแรงเนื่องจากโมเมนต์ดัด:")
    st.latex(r"P_i = \left( \frac{M_R}{\sum r_i^2} \right) \cdot r_i = \frac{M_R \cdot r_i}{\sum r_i^2}")

    st.markdown("**ขั้นที่ 5: การขยายผลเข้าสู่ระบบพิกัดฉาก 2 แกน (Extension to 2D Cartesian Coordinates)**")
    st.markdown("เมื่อแยกพิจารณาในระบบพิกัดฉาก $x$ และ $y$ ระยะห่างกำลังสองจะกลายเป็น $r_i^2 = x_i^2 + y_i^2$ ทำให้ได้สมการที่ใช้ในงานวิศวกรรมจริง:")
    st.latex(r"P_{i, \text{due to } M_x} = \frac{M_x \cdot y_i}{\sum y_i^2}, \quad P_{i, \text{due to } M_y} = \frac{M_y \cdot x_i}{\sum x_i^2}")
    
    st.markdown("เมื่อนำไปรวมกับแรงกดในแนวดิ่งสม่ำเสมอจากน้ำหนักบรรทุกรวม ($\Sigma P_u / n$) จะได้สมการรวมอันเป็นที่สุด:")
    st.latex(r"R_i = \frac{\Sigma P_u}{n} \pm \frac{M_x \cdot y_i}{\sum y_i^2} \pm \frac{M_y \cdot x_i}{\sum x_i^2}")
    # =========================================================
    # 4. Pile Reactions Calculation
    # =========================================================
    st.markdown("### 4. การคำนวณแรงปฏิกิริยาเสาเข็มรายต้น (Pile Reactions Validation)")
    
    # ย้ายพจน์โมเมนต์ลัพธ์รอบ C.G. มาคำนวณตรงนี้เพื่อความต่อเนื่อง
    Mx_tot = Mu_cx + P_u_tot * (-ecc_y)
    My_tot = Mu_cy + P_u_tot * (-ecc_x)
    
    st.markdown("**โมเมนต์ลัพธ์และโมเมนต์เฉื่อยรอบจุดศูนย์ถ่วงกลุ่มเสาเข็ม (C.G.):**")
    st.latex(rf"M_{{x,cg}} = M_{{ux}} + \Sigma P_u(-e_y) = {Mu_cx:.2f} + ({P_u_tot:.2f})({-ecc_y:.3f}) = {Mx_tot:.2f}\text{{ ton-m}}")
    st.latex(rf"M_{{y,cg}} = M_{{uy}} + \Sigma P_u(-e_x) = {Mu_cy:.2f} + ({P_u_tot:.2f})({-ecc_x:.3f}) = {My_tot:.2f}\text{{ ton-m}}")
    st.latex(rf"\sum x^2 = I_{{yy}} = {Iyy_grp:.3f}\text{{ m}}^2, \quad \sum y^2 = I_{{xx}} = {Ixx_grp:.3f}\text{{ m}}^2")
    
    st.markdown("**แทนค่าคำนวณเปรียบเทียบเสาเข็มรายต้น ($R_i$):**")
    st.markdown("รูปแบบสมการใช้งาน: $R_i = \\frac{\\Sigma P_u}{n} + \\frac{M_{x,cg} \\cdot y_i}{I_{xx}} + \\frac{M_{y,cg} \\cdot x_i}{I_{yy}}$")

    # ลูปแสดงผลลัพธ์และการแทนค่าของเสาเข็มทุกต้น
    for i, (px, py) in enumerate(piles_act):
        rx = px - cgx  # ระยะ x เทียบกับ CG
        ry = py - cgy  # ระยะ y เทียบกับ CG
        
        # คำนวณแต่ละพจน์ย่อย
        term_P = P_u_tot / n_piles
        term_Mx = (Mx_tot * ry) / Ixx_grp
        term_My = (My_tot * rx) / Iyy_grp
        R_rigid = term_P + term_Mx + term_My
        R_fdm = p_ult_out[i] # ค่ากำลังปฏิกิริยาจริงจาก Finite Difference Engine
        
        # ตรวจสอบเครื่องหมายเพื่อนำไปแสดงผลในสมการให้สวยงาม
        sign_Mx = "+" if term_Mx >= 0 else "-"
        sign_My = "+" if term_My >= 0 else "-"
        
        # แสดงขั้นตอนการแทนค่าตัวเลข
        st.latex(rf"R_{{{i+1}}} = \frac{{{P_u_tot:.2f}}}{{{n_piles}}} + \frac{{({Mx_tot:.2f})({ry:.3f})}}{{{Ixx_grp:.3f}}} + \frac{{({My_tot:.2f})({rx:.3f})}}{{{Iyy_grp:.3f}}}")
        # แสดงผลลัพธ์สุดท้ายเปรียบเทียบกับวิธี FDM
        st.latex(rf"R_{{{i+1}}} = {term_P:.2f} {sign_Mx} {abs(term_Mx):.2f} {sign_My} {abs(term_My):.2f} = \mathbf{{{R_rigid:.2f}\text{{ ton}}}} \quad \color{{gray}}{{\text{{(FDM Engine = {R_fdm:.2f} ton)}}}}")
    
    st.info("💡 **ข้อแนะนำเชิงวิศวกรรม:** ค่าแรงปฏิกิริยาในวงเล็บสีเทา (FDM Engine) พิจารณาความยืดหยุ่นของฐานราก (Flexibility) และสปริงของชั้นดิน/เสาเข็ม ซึ่งจะมีความแม่นยำสูงกว่าวิธี Rigid Cap และถูกนำไปใช้ในขั้นตอนการคำนวณเหล็กเสริมถัดไป")
    
    # 3. Plate rigidity
    st.markdown("### 3. แผ่นพื้นยืดหยุ่น (Flexural Rigidity) และโมเมนต์ดัด")
    fc_mpa  = fc * 0.0980665
    Ec_rep  = 4700 * math.sqrt(fc_mpa) * 101.9716
    D_rep   = Ec_rep * (t_actual**3) / (12 * (1 - 0.15**2))
    st.latex(rf"E_c = 4700\sqrt{{f'_c\text{{(MPa)}}}} = 4700\sqrt{{{fc_mpa:.2f}}} = {Ec_rep:,.0f}\text{{ ton/m}}^2")
    st.latex(rf"D = \frac{{E_c t^3}}{{12(1-\nu^2)}} = \frac{{{Ec_rep:,.0f} \times {t_actual:.3f}^3}}{{12(1-0.15^2)}} = {D_rep:,.2f}\text{{ ton·m}}")
    st.markdown("**Wood-Armer Moments (คำนวณรวมผลจาก Mxy เพื่อหาโมเมนต์ออกแบบ):**")
    st.latex(rf"M_{{ux}}^* = |M_x| + |M_{{xy}}| = {Mxs:.4f}\text{{ ton·m/m}}")
    st.latex(rf"M_{{uy}}^* = |M_y| + |M_{{xy}}| = {Mys:.4f}\text{{ ton·m/m}}")

    # 4. Shear
    st.markdown("### 4. การตรวจสอบแรงเฉือน (Shear Checks)")
    b0c = 2 * ((cx + d_actual) + (cy + d_actual))
    beta = max(cx, cy) / max(min(cx, cy), 0.001)
    alpha_s = 40 if col_pos == "Interior" else (30 if col_pos == "Edge" else 20)
    vc1 = 0.53 * (1 + 2/beta) * math.sqrt(fc)
    vc2 = 0.27 * (alpha_s * (d_actual * 100) / (b0c * 100) + 2) * math.sqrt(fc)
    vc3 = 1.06 * math.sqrt(fc)

    st.markdown("#### 4.1 Punching Shear รอบเสาตอม่อ (Two-way Shear)")
    st.latex(rf"b_0 = 2((c_x + d) + (c_y + d)) = 2(({cx:.3f} + {d_actual:.3f}) + ({cy:.3f} + {d_actual:.3f})) = {b0c:.3f}\text{{ m}}")
    st.latex(rf"v_{{c1}} = 0.53\left(1 + \frac{{2}}{{\beta}}\right)\sqrt{{f'_c}} = 0.53\left(1 + \frac{{2}}{{{beta:.2f}}}\right)\sqrt{{{fc}}} = {vc1:.3f}\text{{ ksc}}")
    st.latex(rf"v_{{c2}} = 0.27\left(\frac{{\alpha_s d}}{{b_0}} + 2\right)\sqrt{{f'_c}} = 0.27\left(\frac{{{alpha_s} \times {d_actual:.3f}}}{{{b0c:.3f}}} + 2\right)\sqrt{{{fc}}} = {vc2:.3f}\text{{ ksc}}")
    st.latex(rf"v_{{c3}} = 1.06\sqrt{{f'_c}} = 1.06\sqrt{{{fc}}} = {vc3:.3f}\text{{ ksc}}")
    st.latex(rf"\phi v_c = \phi \cdot \min(v_{{c1}}, v_{{c2}}, v_{{c3}}) = 0.75 \times \min({vc1:.2f}, {vc2:.2f}, {vc3:.2f}) = {phivc_col:.3f}\text{{ ksc}}")
    st.latex(rf"v_{{u}} = {vu_col:.4f}\text{{ ksc}} \le \phi v_c ({phivc_col:.3f}\text{{ ksc}}) \rightarrow \textbf{{{'SAFE' if vu_col<=phivc_col else 'FAIL'}}}")

    st.markdown("#### 4.2 Punching Shear รอบหัวเสาเข็ม")
    st.latex(rf"\phi v_{{c,pile}} = 0.75 \times 1.06\sqrt{{f'_c}} = 0.75 \times 1.06\sqrt{{{fc}}} = {phivc_pile:.3f}\text{{ ksc}}")
    st.latex(rf"v_{{u,pile(max)}} = {vu_pile:.4f}\text{{ ksc}} \le {phivc_pile:.3f}\text{{ ksc}} \rightarrow \textbf{{{'SAFE' if vu_pile<=phivc_pile else 'FAIL'}}}")

    st.markdown("#### 4.3 Wide-Beam Shear (One-way Shear)")
    st.latex(rf"\phi v_{{c,wb}} = 0.75 \times 0.53\sqrt{{f'_c}} = 0.75 \times 0.53\sqrt{{{fc}}} = {phivc_wb:.3f}\text{{ ksc}}")
    st.latex(rf"v_{{u,wb}} = {vu_wb:.4f}\text{{ ksc}} \le {phivc_wb:.3f}\text{{ ksc}} \rightarrow \textbf{{{'SAFE' if vu_wb<=phivc_wb else 'FAIL'}}}")

    # 5. Rebar
    st.markdown("### 5. การออกแบบปริมาณเหล็กเสริม (Flexural Reinforcement)")
    rho_min = max(0.8 * math.sqrt(fc) / fy, 14.0 / fy)
    st.latex(rf"\rho_{{min}} = \max\left(\frac{{0.8\sqrt{{{fc}}}}}{{{fy}}}, \frac{{14}}{{{fy}}}\right) = {rho_min:.5f}")
    
    Rn_x = (Mxs * 1e5) / (phi_f * 100 * (d_actual * 100)**2) if d_actual > 0 else 0
    Rn_y = (Mys * 1e5) / (phi_f * 100 * (d_actual * 100)**2) if d_actual > 0 else 0
    
    st.latex(rf"R_{{nx}} = \frac{{M_{{ux}}^*}}{{\phi b d^2}} = \frac{{{Mxs:.4f} \times 10^5}}{{{phi_f} \times 100 \times {d_actual*100:.1f}^2}} = {Rn_x:.4f}\text{{ ksc}}")
    st.latex(rf"A_{{s,req(X)}} = {Asrx:.2f}\text{{ cm}}^2\text{{/m}} \rightarrow \text{{ใช้ }} \textbf{{{nbx}\text{{-DB}}{bar_dia}\;@\;{spx:.0f}\text{{ cm}}}} \quad (A_{{s,prov}} = {nbx*ab:.2f}\text{{ cm}}^2\text{{/m}})")
    
    st.latex(rf"R_{{ny}} = \frac{{M_{{uy}}^*}}{{\phi b d^2}} = \frac{{{Mys:.4f} \times 10^5}}{{{phi_f} \times 100 \times {d_actual*100:.1f}^2}} = {Rn_y:.4f}\text{{ ksc}}")
    st.latex(rf"A_{{s,req(Y)}} = {Asry:.2f}\text{{ cm}}^2\text{{/m}} \rightarrow \text{{ใช้ }} \textbf{{{nby}\text{{-DB}}{bar_dia}\;@\;{spy:.0f}\text{{ cm}}}} \quad (A_{{s,prov}} = {nby*ab:.2f}\text{{ cm}}^2\text{{/m}})")

    # 6. Development length
    st.markdown("### 6. ระยะฝังยึดเหนี่ยวเหล็กเสริม (Development Length, ACI 318-19 §25.5.2.1)")
    psi_s = 0.8 if bar_dia <= 19 else 1.0
    st.latex(rf"L_d = \left( \frac{{3}}{{40\sqrt{{10.2}}}} \right) \left( \frac{{\psi_s}}{{\frac{{c_b+K_{{tr}}}}{{d_b}}}} \right) \left( \frac{{f_y}}{{\sqrt{{f'_c}}}} \right) d_b \ge 30\text{{ cm}}")
    st.latex(rf"L_d = \left( 0.0235 \right) \left( \frac{{{psi_s}}}{{2.5}} \right) \left( \frac{{{fy}}}{{\sqrt{{{fc}}}}} \right) \left( \frac{{{bar_dia}}}{{10}} \right) = {ld_req:.1f}\text{{ cm}}")
    for dr, av in [("X", avail_x), ("Y", avail_y)]:
        ok = av >= ld_req
        st.latex(rf"L_{{avail({dr})}} = {av:.1f}\text{{ cm}} \quad {'\ge' if ok else '<'} \quad {ld_req:.1f}\text{{ cm}} \rightarrow \textbf{{{'OK' if ok else 'Hook Required'}}}")

    # 7. Crack width
    st.markdown("### 7. การตรวจสอบรอยร้าว (Crack Control, Gergely-Lutz)")
    As_x = nbx * ab
    fs_gl = min((Ms_xfdm * 1e5) / (max(As_x, 0.01) * 0.85 * (d_actual * 100)) * 0.0981, 240.0)
    dc_mm = cover_cm * 10 + bar_dia / 2
    s_mm = spx * 10
    A_eff = 2 * dc_mm * s_mm
    
    st.latex(rf"f_s = \frac{{M_s}}{{0.85 \cdot A_s \cdot d}} = {fs_gl:.2f}\text{{ MPa}} \quad (\le 240\text{{ MPa}})")
    st.latex(rf"d_c = \text{{Cover}} + \frac{{d_b}}{{2}} = {cover_cm*10:.0f} + \frac{{{bar_dia}}}{{2}} = {dc_mm:.1f}\text{{ mm}}")
    st.latex(rf"A_{{eff}} = 2 \cdot d_c \cdot s = 2 \cdot {dc_mm:.1f} \cdot {s_mm:.0f} = {A_eff:.0f}\text{{ mm}}^2")
    st.latex(rf"w = 11 \times 10^{{-6}} \cdot \beta \cdot f_s \cdot \sqrt[3]{{d_c \cdot A_{{eff}}}}")
    st.latex(rf"w = 11 \times 10^{{-6}} \cdot 1.2 \cdot {fs_gl:.2f} \cdot \sqrt[3]{{{dc_mm:.1f} \cdot {A_eff:.0f}}} = {w_crack:.4f}\text{{ mm}}")
    st.latex(rf"w \le w_{{allow}} ({w_allow}\text{{ mm}}) \rightarrow \textbf{{{'PASSED' if w_crack<=w_allow else 'EXCEEDED'}}}")
    
with tab_vis:
    v1,v2 = st.columns(2)
    with v1:
        st.markdown("#### As-Built Plan")
        f2d = fig_plan(verts,cx,cy,piles_act,pile_shape,pile_dia,pile_dia,cols_list,cgx,cgy)
        st.pyplot(f2d); plt.close(f2d)
    with v2:
        st.markdown("#### Section Detail")
        if top_steel: st.info("💡 Top steel activated")
        fsec = fig_section(t_actual,B_vis,cover_cm,embed_cm,bar_dia,nbx,spx,cx,cy,top_steel)
        st.pyplot(fsec); plt.close(fsec)
    st.markdown("#### 3D Model")
    f3 = fig_3d(tuple(verts),t_actual,cx,cy,tuple(piles_act),pile_shape,pile_dia,pile_dia,embed_cm/100,tuple(cols_list))
    st.plotly_chart(f3,use_container_width=True)
