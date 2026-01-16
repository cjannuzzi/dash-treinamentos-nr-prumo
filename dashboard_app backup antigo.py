import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard QSSMA | Prumo",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IDENTIDADE VISUAL PRUMO (BASEADA NO FERRAMENTAS DIGITAIS) ---
COR_PRUMO_BROWN = "#501E0A"   # Marrom Prumo (Principal - Custos)
COR_PRUMO_ORANGE = "#Fa7828"  # Laranja Prumo (Destaque - Internos/Saving)
COR_SAVING_GREEN = "#2A9D8F"  # Verde Petróleo (APENAS PARA O TEXTO/BULLET DE ECONOMIA)
COR_BG_BODY = "#F8F9FA"       # Fundo Off-White

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Montserrat', sans-serif;
        }}
        
        .main {{ background-color: {COR_BG_BODY}; }}
        
        /* Sidebar Marrom */
        [data-testid="stSidebar"] {{ background-color: {COR_PRUMO_BROWN}; }}
        [data-testid="stSidebar"] * {{ color: #ffffff !important; }}
        [data-testid="stSidebar"] input {{ color: {COR_PRUMO_BROWN} !important; }}
        div[data-baseweb="select"] span {{ color: {COR_PRUMO_BROWN} !important; }}
        
        /* Títulos */
        h1, h2, h3 {{ color: {COR_PRUMO_BROWN}; font-weight: 700; }}
        
        /* CARDS KPI */
        div[data-testid="stMetric"] {{
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border-left: 6px solid {COR_PRUMO_ORANGE};
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            min-height: 120px;
        }}
        
        div[data-testid="stMetricLabel"] {{
            font-size: 0.85rem !important;
            color: #666666 !important;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        div[data-testid="stMetricValue"] {{
            font-size: 1.6rem !important;
            color: {COR_PRUMO_BROWN} !important;
            font-weight: 800;
        }}
        
        div[data-testid="stMetricDelta"] {{
            font-size: 0.8rem !important;
            color: {COR_PRUMO_ORANGE} !important;
            font-weight: 500;
        }}
        div[data-testid="stMetricDelta"] svg {{ display: none; }}

        .stDataFrame {{ border: 1px solid #eeeeee; border-radius: 8px; }}
        
        button[data-baseweb="tab"] {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 600;
        }}
    </style>
""", unsafe_allow_html=True)

# --- FORMATAÇÃO BRL ---
def formatar_brl(valor):
    if pd.isna(valor) or valor == 0: return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

@st.cache_data
def carregar_dados_final():
    arquivo_excel = 'TREINAMENTOS VALORES ATUAIS.xlsx'
    arquivo_csv = 'TREINAMENTOS_NORMATIVOS.csv'
    
    df = None
    try:
        df = pd.read_excel(arquivo_excel, header=0, engine='openpyxl')
    except:
        try:
            df = pd.read_csv(arquivo_csv, header=0)
        except:
            st.error("❌ Arquivo não encontrado.")
            return None

    cols_proibidas = [c for c in df.columns if 'TOTAL' in str(c).upper() or 'SOMA' in str(c).upper()]
    if cols_proibidas:
        df = df.drop(columns=cols_proibidas)

    colunas_id = ['CONTRATANTE', 'OBRAS', 'COORDENADOR', 'GERENCIA EXECUTIVA']
    for col in colunas_id:
        if col not in df.columns:
            st.error(f"Coluna '{col}' não encontrada.")
            return None

    df_melted = df.melt(id_vars=colunas_id, var_name='Treinamento', value_name='Valor_Bruto')

    def classificar_seguro(valor):
        if pd.isna(valor) or str(valor).strip() in ['', '-', 'nan', 'None']:
            return None, None
            
        val_str = str(valor).strip().upper()
        if val_str in ['N/A', 'NA', 'N.A', 'SEM REALIZAÇÃO']:
            return None, None 

        if 'INTERNO' in val_str or 'PRUMO' in val_str:
            return 0.0, 'Interno (SESMT)'

        if isinstance(valor, (int, float)):
            if valor > 0: return float(valor), 'Externo (Custo)'
            return None, None

        try:
            limpo = val_str.replace('R$', '').replace(' ', '')
            if ',' in limpo:
                limpo = limpo.replace('.', '').replace(',', '.')
            custo = float(limpo)
            if custo > 0: return custo, 'Externo (Custo)'
        except:
            return None, None
        return None, None

    resultado = df_melted['Valor_Bruto'].apply(classificar_seguro).tolist()
    
    df_melted['Custo_Final'] = [x[0] for x in resultado]
    df_melted['Status'] = [x[1] for x in resultado]
    
    df_limpo = df_melted.dropna(subset=['Status'])
    df_limpo['Treinamento'] = df_limpo['Treinamento'].str.replace('NR - ', 'NR ').str.strip()

    df_limpo['BUSCA_GERAL'] = (
        df_limpo['Treinamento'].astype(str) + " " + 
        df_limpo['OBRAS'].astype(str) + " " + 
        df_limpo['COORDENADOR'].astype(str) + " " + 
        df_limpo['GERENCIA EXECUTIVA'].astype(str) + " " +
        df_limpo['CONTRATANTE'].astype(str)
    ).str.upper()

    return df_limpo

df = carregar_dados_final()

if df is not None:
    # --- SIDEBAR ---
    st.sidebar.title("Filtros")
    termo_busca = st.sidebar.text_input("Busca Global", placeholder="Ex: NR 10, Coordenador...", label_visibility="collapsed")
    
    df_global = df.copy()
    if termo_busca:
        df_global = df_global[df_global['BUSCA_GERAL'].str.contains(termo_busca.upper(), na=False)]
    
    st.sidebar.divider()
    
    opt_contratante = sorted(df_global['CONTRATANTE'].astype(str).unique())
    sel_contratante = st.sidebar.multiselect("Contratante", opt_contratante, default=opt_contratante)
    df_f1 = df_global[df_global['CONTRATANTE'].isin(sel_contratante)]
    
    opt_gerencia = sorted(df_f1['GERENCIA EXECUTIVA'].astype(str).unique())
    sel_gerencia = st.sidebar.multiselect("Gerência Executiva", opt_gerencia, default=opt_gerencia)
    df_f2 = df_f1[df_f1['GERENCIA EXECUTIVA'].isin(sel_gerencia)]

    opt_coord = sorted(df_f2['COORDENADOR'].astype(str).unique())
    sel_coord = st.sidebar.multiselect("Coordenador", opt_coord, default=opt_coord)
    df_f3 = df_f2[df_f2['COORDENADOR'].isin(sel_coord)]

    opt_obras = sorted(df_f3['OBRAS'].astype(str).unique())
    sel_obras = st.sidebar.multiselect("Obras", opt_obras, default=opt_obras)
    df_f4 = df_f3[df_f3['OBRAS'].isin(sel_obras)]

    opt_treino = sorted(df_f4['Treinamento'].astype(str).unique())
    sel_treino = st.sidebar.multiselect("Treinamentos", opt_treino, default=[])
    
    df_filtered = df_f4.copy()
    if sel_treino:
        df_filtered = df_filtered[df_filtered['Treinamento'].isin(sel_treino)]

    # --- KPIs ---
    inv_total = df_filtered[df_filtered['Status'] == 'Externo (Custo)']['Custo_Final'].sum()
    qtd_interno = len(df_filtered[df_filtered['Status'] == 'Interno (SESMT)'])
    saving = qtd_interno * 200.00
    qtd_total = len(df_filtered)
    
    top_inv = df_filtered[df_filtered['Status']=='Externo (Custo)'].groupby('COORDENADOR')['Custo_Final'].sum().sort_values(ascending=False)
    nome_inv = top_inv.index[0] if not top_inv.empty else "N/A"
    val_inv = top_inv.iloc[0] if not top_inv.empty else 0

    st.title("COORDENAÇÃO DG | Dashboard QSSMA")
    st.markdown("**Gestão de Custos e Treinamentos Normativos**")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Investimento Total", formatar_brl(inv_total))
    c2.metric("Total Registros", qtd_total)
    
    # KPI SAVING: Hack CSS para o Bullet ser Verde, mas o gráfico embaixo continuará Laranja
    c3.metric("Realizados Internamente", qtd_interno, delta=f"Economia: {formatar_brl(saving)}")
    st.markdown(f"""<style>
        div[data-testid="stMetric"]:nth-child(3) div[data-testid="stMetricDelta"] {{
            color: {COR_SAVING_GREEN} !important;
        }}
    </style>""", unsafe_allow_html=True)
    
    c4.metric("Maior Investidor", formatar_brl(val_inv), delta=nome_inv, delta_color="inverse")

    st.divider()

    # --- SEÇÃO 1: GRÁFICOS ORIGINAIS ---
    col_orig1, col_orig2 = st.columns([2, 1])
    
    with col_orig1:
        st.subheader("💰 Top 10 Custos (Por Treinamento)")
        df_ext = df_filtered[df_filtered['Status'] == 'Externo (Custo)']
        if not df_ext.empty:
            df_chart = df_ext.groupby('Treinamento')['Custo_Final'].sum().reset_index().sort_values('Custo_Final', ascending=True).tail(10)
            df_chart['fmt'] = df_chart['Custo_Final'].apply(formatar_brl)
            
            fig = px.bar(df_chart, x='Custo_Final', y='Treinamento', orientation='h', text='fmt')
            # COR MARROM (IDENTIDADE)
            fig.update_traces(marker_color=COR_PRUMO_BROWN, textfont_color='white')
            fig.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem custos externos.")
    
    with col_orig2:
        st.subheader("📌 Status da Demanda")
        df_pie = df_filtered['Status'].value_counts().reset_index()
        df_pie.columns = ['Status', 'Qtd']
        
        # CORES IDENTIDADE VISUAL
        cores = {
            'Externo (Custo)': COR_PRUMO_BROWN,   # Marrom
            'Interno (SESMT)': COR_PRUMO_ORANGE,  # Laranja
            'Não Aplicável (N/A)': '#D1D5DB'
        }
        fig2 = px.pie(df_pie, values='Qtd', names='Status', hole=0.6, color='Status', color_discrete_map=cores)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- SEÇÃO 2: NOVOS GRÁFICOS ---
    st.markdown("### 📈 Rankings Comparativos")
    
    col_sel, _ = st.columns([1, 4])
    with col_sel:
        agrupar = st.selectbox("Comparar por:", ["COORDENADOR", "OBRAS", "GERENCIA EXECUTIVA"], index=0)

    g_new1, g_new2, g_new3 = st.columns(3)

    with g_new1:
        st.markdown("**💸 Quem mais investe? (Externo)**")
        df_rank_ext = df_filtered[df_filtered['Status']=='Externo (Custo)'].groupby(agrupar)['Custo_Final'].sum().reset_index()
        df_rank_ext = df_rank_ext.sort_values('Custo_Final', ascending=True).tail(10)
        
        if not df_rank_ext.empty:
            df_rank_ext['fmt'] = df_rank_ext['Custo_Final'].apply(formatar_brl)
            fig_r1 = px.bar(df_rank_ext, x='Custo_Final', y=agrupar, orientation='h', text='fmt')
            # COR MARROM (CUSTO)
            fig_r1.update_traces(marker_color=COR_PRUMO_BROWN, textfont_color='white') 
            fig_r1.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_r1, use_container_width=True)
        else:
            st.info("Sem dados.")

    with g_new2:
        st.markdown("**🛡️ Quem mais gera Saving? (Interno)**")
        df_rank_int = df_filtered[df_filtered['Status']=='Interno (SESMT)'].groupby(agrupar).size().reset_index(name='Qtd')
        df_rank_int['Valor_Saving'] = df_rank_int['Qtd'] * 200.00
        df_rank_int = df_rank_int.sort_values('Valor_Saving', ascending=True).tail(10)
        
        if not df_rank_int.empty:
            df_rank_int['fmt'] = df_rank_int['Valor_Saving'].apply(formatar_brl)
            fig_r2 = px.bar(df_rank_int, x='Valor_Saving', y=agrupar, orientation='h', text='fmt')
            # COR LARANJA (SAVING/INTERNO) - IDENTIDADE VISUAL
            fig_r2.update_traces(marker_color=COR_PRUMO_ORANGE, textfont_color='white') 
            fig_r2.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_r2, use_container_width=True)
        else:
            st.info("Sem dados.")

    with g_new3:
        st.markdown("**📊 Eficiência (Interno vs Externo)**")
        df_prop = df_filtered.groupby([agrupar, 'Status']).size().reset_index(name='Qtd')
        top_vol = df_prop.groupby(agrupar)['Qtd'].sum().sort_values(ascending=False).head(10).index
        df_prop = df_prop[df_prop[agrupar].isin(top_vol)]
        
        # Mapa de Cores Consistente (Marrom vs Laranja)
        cores_prop = {'Externo (Custo)': COR_PRUMO_BROWN, 'Interno (SESMT)': COR_PRUMO_ORANGE}
        fig_r3 = px.bar(df_prop, x='Qtd', y=agrupar, color='Status', orientation='h', 
                        color_discrete_map=cores_prop, text='Qtd')
        fig_r3.update_layout(xaxis_title="Qtd", yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', 
                             legend=dict(orientation="h", y=-0.2), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_r3, use_container_width=True)

    st.divider()

    # --- TABELAS ---
    tab_det, tab_audit = st.tabs(["📋 Detalhamento", "🕵️‍♂️ Auditoria"])
    
    with tab_det:
        df_show = df_filtered[['OBRAS', 'COORDENADOR', 'GERENCIA EXECUTIVA', 'Treinamento', 'Status', 'Custo_Final']].copy()
        df_show['Custo Visual'] = df_show['Custo_Final'].apply(formatar_brl)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    with tab_audit:
        st.info("Auditoria de Valores (Top 50 Maiores Custos)")
        audit = df_filtered[df_filtered['Status'] == 'Externo (Custo)'].sort_values('Custo_Final', ascending=False).head(50)
        audit['Valor'] = audit['Custo_Final'].apply(formatar_brl)
        st.dataframe(audit[['Treinamento', 'OBRAS', 'COORDENADOR', 'Valor']], use_container_width=True)