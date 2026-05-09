import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from fractions import Fraction

# ============================================================================
# CONFIGURACIÓN Y CÁLCULOS
# ============================================================================
st.set_page_config(page_title="Generador de Pórticos - UNLP", layout="wide")

st.title("🏗️ Generador Automático de Pórticos - UNLP")

# ============================================================================
# MOTOR DE DATOS: BASE DE PERFILES AISC
# ============================================================================
@st.cache_data
def cargar_base_perfiles():
    """Lee el Excel, renombra la columna clave y elimina el sistema imperial"""
    df = pd.read_excel("Perfiles AISC.xlsx", header=1)
    
    # [CORRECCIÓN]: Renombramos la columna C (índice 2) forzadamente a nuestro nombre estándar
    # Así evitamos el error de los saltos de línea o espacios de la tabla original
    df.rename(columns={df.columns[2]: 'AISC_Manual_Label'}, inplace=True)
    
    # Eliminar columnas imperiales: de la E (índice 4) a la BC (índice 54)
    cols_to_drop = df.columns[4:55]
    df_metrico = df.drop(columns=cols_to_drop)
    
    # Limpiamos filas que no tengan nombre de perfil (ahora sí la va a encontrar)
    df_metrico = df_metrico.dropna(subset=['AISC_Manual_Label'])
    
    return df_metrico

# Cargamos la base a la memoria (se hace una sola vez de forma súper rápida)
df_perfiles = cargar_base_perfiles()
lista_perfiles_totales = df_perfiles['AISC_Manual_Label'].tolist()

def obtener_propiedades_perfil(nombre_perfil):
    """Busca un perfil en la tabla y devuelve sus dimensiones en metros"""
    try:
        # Filtramos la tabla para encontrar la fila del perfil elegido
        datos = df_perfiles[df_perfiles['AISC_Manual_Label'] == nombre_perfil].iloc[0]
        
        # Extraemos las medidas reales (están en mm, las pasamos a metros)
        props = {
            'd': float(datos['d']) / 1000.0,   # Peralte total
            'bf': float(datos['bf']) / 1000.0, # Ancho del ala
            'tw': float(datos['tw']) / 1000.0, # Espesor del alma
            'tf': float(datos['tf']) / 1000.0, # Espesor del ala
            'A': float(datos['A']) / 10000.0,  # Área en m2
            'Ix': float(datos['Ix']),          # Inercia X
            'Iy': float(datos['Iy'])           # Inercia Y
        }
        return props
    except:
        # Medidas de salvavidas por si algo falla
        return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015}

# ============================================================================
# FUNCIONES DE DIBUJO
# ============================================================================

def dibujar_apoyo_articulado(ax, x, y, escala=0.35):
    vertices = [[x, y], [x-escala, y-escala], [x+escala, y-escala]]
    triangle = patches.Polygon(vertices, closed=True, edgecolor='black', facecolor='white', linewidth=1.8, zorder=5)
    ax.add_patch(triangle)
    base_width = escala * 2.5
    ax.plot([x-base_width, x+base_width], [y-escala, y-escala], 'k', linewidth=1.5, zorder=4)
    for i in range(6):
        x_raya = x - base_width + (i * base_width * 2 / 5)
        ax.plot([x_raya, x_raya - 0.15], [y-escala, y-escala-0.2], 'k', linewidth=1)

def dibujar_apoyo_empotrado(ax, x, y, escala=0.35):
    ancho_base = escala * 2.5
    ax.plot([x - ancho_base, x + ancho_base], [y, y], 'k', linewidth=2.5, zorder=5)
    for i in range(8):
        x_raya = x - ancho_base + (i * ancho_base * 2 / 7)
        ax.plot([x_raya, x_raya - 0.15], [y, y - 0.25], 'k', linewidth=1)

def dibujar_arriostramiento_y(ax, x, y):
    dx, dy = -0.45, -0.36
    xf, yf = x + dx, y + dy
    ax.plot([x, xf], [y, yf], color='#0066CC', linestyle='-', linewidth=1.2, zorder=1)
    ax.plot([x], [y], 'o', color='white', markeredgecolor='#0066CC', markeredgewidth=1.8, markersize=6, zorder=5)
    L_hip = np.hypot(dx, dy)
    ux, uy = dx/L_hip, dy/L_hip
    px, py = -uy, ux
    h_tri, w_tri = 0.3, 0.4
    mx, my = xf + ux * h_tri, yf + uy * h_tri
    p2x, p2y = mx + px * (w_tri / 2), my + py * (w_tri / 2)
    p3x, p3y = mx - px * (w_tri / 2), my - py * (w_tri / 2)
    tri = patches.Polygon([[xf, yf], [p2x, p2y], [p3x, p3y]], closed=True, edgecolor='#0066CC', facecolor='white', linewidth=1.5, zorder=3)
    ax.add_patch(tri)
    ax.plot([p2x, p3x], [p2y, p3y], color='#0066CC', linewidth=1.5, zorder=3)

def dibujar_seccion_ipe(ax, x, y, orientacion='FUERTE', escala=0.45):
    """Sección en planta de la columna"""
    w, h = (1.0 * escala) * 1.5, (0.65 * escala) * 2.0
    ta, tm = 0.16 * escala * 1.5, 0.08 * escala * 1.5
    
    if orientacion == 'FUERTE':
        ax.add_patch(patches.Rectangle((x - w/2, y - tm/2), w, tm, facecolor='lightgray', edgecolor='black', alpha=0.4))
        ax.add_patch(patches.Rectangle((x - w/2, y - h/2), ta, h, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x + w/2 - ta, y - h/2), ta, h, facecolor='gray', edgecolor='black', alpha=0.7))
    else:
        ax.add_patch(patches.Rectangle((x - tm/2, y - h/2), tm, h, facecolor='lightgray', edgecolor='black', alpha=0.4))
        ax.add_patch(patches.Rectangle((x - w/2, y + h/2 - ta), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y - h/2), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
    
    # Ejes Locales en la Planta (X=Rojo, Y=Verde)
    color_x, color_y = '#CC0000', '#008000'
    ax.annotate('', xy=(x + (w/2 + 0.3), y), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_x, lw=1.2))
    ax.text(x + (w/2 + 0.4), y - 0.1, 'x', fontsize=9, color=color_x, fontweight='bold')
    ax.annotate('', xy=(x, y + (h/2 + 0.3)), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_y, lw=1.2))
    ax.text(x - 0.15, y + (h/2 + 0.4), 'y', fontsize=9, color=color_y, fontweight='bold')

def dibujar_seccion_viga(ax, x, y, orientacion='FUERTE', escala=0.45):
    """Sección lateral de la viga (Vista en el plano Y-Z)"""
    w, h = (1.0 * escala) * 1.5, (0.65 * escala) * 2.0
    ta, tm = 0.16 * escala * 1.5, 0.08 * escala * 1.5
    
    if orientacion == 'FUERTE':
        # Alma vertical, alas horizontales
        ax.add_patch(patches.Rectangle((x - tm/2, y - h/2), tm, h, facecolor='lightgray', edgecolor='black', alpha=0.4))
        ax.add_patch(patches.Rectangle((x - w/2, y + h/2 - ta), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y - h/2), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
    else:
        # Alma horizontal, alas verticales
        ax.add_patch(patches.Rectangle((x - h/2, y - tm/2), h, tm, facecolor='lightgray', edgecolor='black', alpha=0.4))
        ax.add_patch(patches.Rectangle((x - h/2, y - w/2), ta, w, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x + h/2 - ta, y - w/2), ta, w, facecolor='gray', edgecolor='black', alpha=0.7))
        
    # Ejes Locales de la Viga (Y=Verde, Z=Azul)
    color_y, color_z = '#008000', '#0066CC'
    dim_y = w/2 if orientacion == 'FUERTE' else h/2
    dim_z = h/2 if orientacion == 'FUERTE' else w/2
    
    ax.annotate('', xy=(x + dim_y + 0.3, y), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_y, lw=1.2))
    ax.text(x + dim_y + 0.4, y - 0.1, 'y', fontsize=9, color=color_y, fontweight='bold')
    ax.annotate('', xy=(x, y + dim_z + 0.3), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_z, lw=1.2))
    ax.text(x - 0.15, y + dim_z + 0.4, 'z', fontsize=9, color=color_z, fontweight='bold')

def dibujar_cotas(ax, x1, y1, x2, y2, texto, offset=0.8, orientacion='horizontal'):
    if orientacion == 'horizontal':
        ax.annotate('', xy=(x2, y1 + offset), xytext=(x1, y1 + offset), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text((x1 + x2) / 2, y1 + offset + 0.3, texto, ha='center', va='bottom', fontsize=10, fontweight='bold')
    else:
        ax.annotate('', xy=(x1 - offset, y2), xytext=(x1 - offset, y1), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text(x1 - offset - 0.3, (y1 + y2) / 2, texto, ha='right', va='center', fontsize=10, fontweight='bold', rotation=90)

# ============================================================================
# INTERFAZ SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Parámetros")
H = st.sidebar.number_input("Altura (H) [m]", value=5.5)
L = st.sidebar.number_input("Longitud (L) [m]", value=7.0)

series = ["IPE", "IPN", "HEB", "UPN", "W"]

st.sidebar.markdown("**Columna**")
# Menú desplegable con todos los perfiles de la AISC
perfil_col = st.sidebar.selectbox("Perfil Columna", lista_perfiles_totales, index=lista_perfiles_totales.index("W12X50") if "W12X50" in lista_perfiles_totales else 0, key="sc")
o_col = st.sidebar.radio("Eje en plano (Col)", ["FUERTE", "DEBIL"], key="oc")

st.sidebar.markdown("**Viga**")
perfil_viga = st.sidebar.selectbox("Perfil Viga", lista_perfiles_totales, index=lista_perfiles_totales.index("W16X26") if "W16X26" in lista_perfiles_totales else 0, key="sv")
o_viga = st.sidebar.radio("Eje en plano (Viga)", ["FUERTE", "DEBIL"], key="ov")

with st.sidebar.expander("Riostras"):
    NUDOS = st.sidebar.checkbox("Nudos", value=True)
    CANT = st.sidebar.number_input("Cant. Intermedias", min_value=0, value=2, step=1)
    FRAC = st.sidebar.slider("Fracción H", 0.1, 1.0, 0.33)

T_APOYO = st.sidebar.selectbox("Apoyo", ["Empotrado", "Articulado"])

# ============================================================================
# MOTOR DE DIBUJO
# ============================================================================

def generar_grafico():
    # Extraemos todas las propiedades del catálogo
    props_col = obtener_propiedades_perfil(perfil_col)
    props_viga = obtener_propiedades_perfil(perfil_viga)
    
    D_COL_R = props_col['d']
    D_VIGA_R = props_viga['d']
    
    # Escala visual del pórtico
    esc = 0.8 / 0.40
    D_C, D_V = D_COL_R * esc, D_VIGA_R * esc
    
    # Ahora usamos los espesores reales multiplicados por la escala visual para dibujar!
    E_ALA_C = max(props_col['tf'] * esc, 0.06) 
    E_ALA_V = max(props_viga['tf'] * esc, 0.06)
    
    lw_ext = 1.5
    lw_int = 1.0

    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_aspect('equal')
    ax.axis('off')
    # Aumentamos el límite X para que entre el cuadro de información desplazado
    ax.set_xlim(-5, L + 12); ax.set_ylim(-6, H + 3)

    # 1. EJES GLOBALES
    color_x, color_y, color_z = '#CC0000', '#008000', '#0066CC'
    xo, yo = -3.5, 0
    
    ax.annotate('', xy=(xo+1, yo), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=color_x))
    ax.text(xo+1.2, yo, 'X', color=color_x, fontweight='bold', va='center')
    ax.annotate('', xy=(xo, yo+1), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=color_z))
    ax.text(xo, yo+1.3, 'Z', color=color_z, fontweight='bold', ha='center')
    dx_y, dy_y = 0.5, 0.4
    ax.annotate('', xy=(xo+dx_y, yo+dy_y), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=color_y))
    ax.text(xo+dx_y+0.2, yo+dy_y+0.1, 'Y', color=color_y, fontweight='bold', ha='left')
    ax.plot([xo], [yo], 'o', color='black', markersize=4)

    # 2. COLUMNAS
    vs, vi = H + D_V/2, H - D_V/2
    for x in [0, L]:
        ax.plot([x-D_C/2, x-D_C/2], [0, vs], 'k', lw=lw_ext)
        ax.plot([x+D_C/2, x+D_C/2], [0, vs], 'k', lw=lw_ext)
        ax.plot([x-D_C/2, x+D_C/2], [0, 0], 'k', lw=lw_ext)
        ax.plot([x-D_C/2, x+D_C/2], [vs, vs], 'k', lw=lw_ext)
        
        if o_col == 'FUERTE':
            ax.plot([x-D_C/2+E_ALA_C, x-D_C/2+E_ALA_C], [0, vs], 'k', lw=lw_int)
            ax.plot([x+D_C/2-E_ALA_C, x+D_C/2-E_ALA_C], [0, vs], 'k', lw=lw_int)
        else:
            ax.plot([x, x], [0, vs], 'k--', lw=lw_int, alpha=0.6)
            
        if T_APOYO == "Empotrado": dibujar_apoyo_empotrado(ax, x, 0)
        else: dibujar_apoyo_articulado(ax, x, 0)
        
        # [CORRECCIÓN]: Secciones de columna subidas a la cota -1.5
        dibujar_seccion_ipe(ax, x, -1.5, orientacion=o_col)

    # 3. VIGA Y SECCIÓN LATERAL
    xfi, xfd = D_C/2, L - D_C/2
    ax.plot([xfi, xfd], [vi, vi], 'k', lw=lw_ext)
    ax.plot([xfi, xfd], [vs, vs], 'k', lw=lw_ext)
    if o_viga == 'FUERTE':
        ax.plot([xfi, xfd], [vi+E_ALA_V, vi+E_ALA_V], 'k', lw=lw_int)
        ax.plot([xfi, xfd], [vs-E_ALA_V, vs-E_ALA_V], 'k', lw=lw_int)
    else:
        ax.plot([xfi, xfd], [H, H], 'k--', lw=lw_int, alpha=0.6)

    # [CORRECCIÓN]: Dibujo del perfil de la viga a la derecha
    x_viga_sec = L + 1.8
    ax.plot([xfd, x_viga_sec], [H, H], 'k-.', lw=0.8, alpha=0.4) # Línea de proyección
    dibujar_seccion_viga(ax, x_viga_sec, H, orientacion=o_viga)

    # 4. RIOSTRAS Y COTAS
    pos = []
    if NUDOS: pos.append(H)
    dz = FRAC * H
    for i in range(1, int(CANT)+1):
        if i*dz < H-0.1: pos.append(i*dz)
    pos.sort()
    
    for yp in pos:
        dibujar_arriostramiento_y(ax, 0, yp)
        dibujar_arriostramiento_y(ax, L, yp)

    y_p = 0
    xc = D_C/2 + 1.0
    for yp in pos:
        dist = yp - y_p
        if dist > 0.1:
            f = Fraction(FRAC).limit_denominator(6)
            t = f"H/{f.denominator}={dist:.2f}m" if abs(dist-dz)<0.05 else f"{dist:.2f}m"
            ax.annotate('', xy=(xc, yp), xytext=(xc, y_p), arrowprops=dict(arrowstyle='<->', lw=0.8))
            ax.text(xc+0.1, (y_p+yp)/2, t, rotation=90, va='center', fontsize=8)
        y_p = yp

    dibujar_cotas(ax, 0, 0, 0, H, f'H={H:.2f}m', 1.2, 'vertical')
    dibujar_cotas(ax, 0, H, L, H, f'L={L:.2f}m', 1.0, 'horizontal')

    # INFO
    res = f"Riostras: {len(pos)} (a {FRAC}H)"
    info = f"TP Nº1 - ESTRUCTURAS METÁLICAS\nCol: {t_col} {m_col} ({o_col})\nViga: {t_viga} {m_viga} ({o_viga})\n{res}"
    ax.text(L+1.5, H, info, bbox=dict(boxstyle='round', fc='white', ec='black'), family='monospace', fontsize=9, va='top')

    st.pyplot(fig)

generar_grafico()