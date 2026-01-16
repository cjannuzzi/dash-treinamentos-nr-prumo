"""
================================================================================
DASHBOARD GERENCIAL QSSMA - COORDENAÇÃO DG (PRUMO ENGENHARIA)
================================================================================
Autor: [Seu Nome / Gemini]
Versão: 3.0 (Identidade Visual Prumo + Lógica Estrita de Custos)
Data: Janeiro/2026

OBJETIVO:
Monitorar custos de treinamentos normativos (NRs), identificando oportunidades 
de economia (Saving) geradas pelo SESMT interno e controlando o budget externo.

ESTRUTURA DO CÓDIGO:
1.  CONFIGURAÇÕES GERAIS: Setup da página e importação de bibliotecas.
2.  IDENTIDADE VISUAL (CSS): Definição de cores, fontes e estilos dos componentes.
3.  FUNÇÕES AUXILIARES: Ferramentas de formatação (R$, datas, etc).
4.  ETL (DATA ENGINE): Carregamento, limpeza e transformação dos dados brutos.
5.  MOTOR DE FILTROS: Lógica de sidebar e filtros em cascata.
6.  CÁLCULO DE KPIS: Matemática financeira do dashboard.
7.  INTERFACE (UI): Construção visual dos gráficos, tabelas e métricas.
================================================================================
"""

# --- 1. IMPORTAÇÃO DE BIBLIOTECAS ---
import streamlit as st          # Framework principal da interface web
import pandas as pd             # Manipulação de dados (ETL)
import plotly.express as px     # Criação de gráficos interativos
import plotly.graph_objects as go # Personalização avançada de gráficos

# --- 1.1 CONFIGURAÇÃO DA PÁGINA ---
# Define título da aba, layout wide (tela cheia) e estado da barra lateral
st.set_page_config(
    page_title="Dashboard QSSMA | Prumo",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==============================================================================
# 2. IDENTIDADE VISUAL E ESTILOS (CSS)
# ==============================================================================
# Centralizamos as cores aqui. Se a marca mudar, altere apenas estas variáveis.

COR_PRUMO_BROWN = "#501E0A"   # Marrom Institucional (Usado em Títulos e Sidebar)
COR_PRUMO_ORANGE = "#Fa7828"  # Laranja Destaque (Usado em Bordas e Gráficos de Interno)
COR_SAVING_GREEN = "#2A9D8F"  # Verde (Exclusivo para indicar Economia/Saving positivo)
COR_BG_BODY = "#F8F9FA"       # Off-White (Fundo suave para descanso visual)
COR_TEXT_MUTED = "#666666"    # Cinza (Para rótulos e textos secundários)

# Injeção de CSS customizado para sobrescrever o padrão do Streamlit
st.markdown(f"""
    <style>
        /* Importa a fonte oficial 'Montserrat' do Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
        
        /* Aplica a fonte em todo o documento */
        html, body, [class*="css"] {{
            font-family: 'Montserrat', sans-serif;
        }}
        
        /* Cor de fundo da área principal */
        .main {{ background-color: {COR_BG_BODY}; }}
        
        /* --- ESTILO DA BARRA LATERAL (SIDEBAR) --- */
        [data-testid="stSidebar"] {{ 
            background-color: {COR_PRUMO_BROWN}; /* Fundo Marrom */
        }}
        /* Força todos os textos da sidebar a serem brancos */
        [data-testid="stSidebar"] * {{ color: #ffffff !important; }}
        
        /* Corrige a cor do texto dentro das caixas de input (para não ficar branco no branco) */
        [data-testid="stSidebar"] input {{ color: {COR_PRUMO_BROWN} !important; }}
        div[data-baseweb="select"] span {{ color: {COR_PRUMO_BROWN} !important; }}
        
        /* --- ESTILO DOS TÍTULOS --- */
        h1, h2, h3 {{ 
            color: {COR_PRUMO_BROWN}; 
            font-weight: 700; 
        }}
        
        /* --- ESTILO DOS CARTÕES DE MÉTRICA (KPIs) --- */
        div[data-testid="stMetric"] {{
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border-left: 6px solid {COR_PRUMO_ORANGE}; /* Borda Laranja à esquerda */
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);   /* Sombra suave */
            min-height: 120px;
        }}
        
        /* Rótulo (Ex: "Investimento Total") */
        div[data-testid="stMetricLabel"] {{
            font-size: 0.85rem !important;
            color: {COR_TEXT_MUTED} !important;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        /* Valor (Ex: "R$ 50.000") */
        div[data-testid="stMetricValue"] {{
            font-size: 1.6rem !important;
            color: {COR_PRUMO_BROWN} !important;
            font-weight: 800;
        }}
        
        /* Delta/Detalhe (Texto pequeno abaixo do valor) */
        div[data-testid="stMetricDelta"] {{
            font-size: 0.8rem !important;
            color: {COR_PRUMO_ORANGE} !important;
            font-weight: 500;
        }}
        /* Remove a seta padrão do delta */
        div[data-testid="stMetricDelta"] svg {{ display: none; }}

        /* --- HACK CSS: Cor Específica para o KPI de Saving --- */
        /* Seleciona o 3º Cartão (Saving) e força o texto de detalhe a ser VERDE */
        div[data-testid="column"]:nth-of-type(3) div[data-testid="stMetricDelta"] {{
            color: {COR_SAVING_GREEN} !important;
            -webkit-text-fill-color: {COR_SAVING_GREEN} !important;
        }}

        /* Estilo das Tabelas de Dados */
        .stDataFrame {{ border: 1px solid #eeeeee; border-radius: 8px; }}
        
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# 3. FUNÇÕES AUXILIARES
# ==============================================================================

def formatar_brl(valor):
    """
    Formata valores float para moeda brasileira (R$ 1.234,56).
    Trata erros caso venha valor nulo ou zero.
    """
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    # Lógica: Formata com vírgula padrão US (1,234.56) e depois inverte os caracteres
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ==============================================================================
# 4. ETL - EXTRAÇÃO E TRATAMENTO DE DADOS
# ==============================================================================

@st.cache_data
def carregar_dados_final():
    """
    Lê o arquivo Excel, remove colunas indesejadas, transforma a matriz em lista
    e aplica as regras de negócio estritas (Interno vs Externo vs N/A).
    """
    arquivo_excel = 'TREINAMENTOS VALORES ATUAIS.xlsx'
    arquivo_csv = 'TREINAMENTOS_NORMATIVOS.csv'
    
    df = None
    
    # 4.1 TENTATIVA DE LEITURA
    try:
        df = pd.read_excel(arquivo_excel, header=0, engine='openpyxl')
    except:
        try:
            df = pd.read_csv(arquivo_csv, header=0)
        except:
            st.error("❌ ERRO CRÍTICO: Nenhum arquivo de dados encontrado na pasta.")
            return None

    # 4.2 LIMPEZA DE COLUNAS DE TOTAL (Para evitar duplicação de valores)
    # Remove qualquer coluna que contenha "TOTAL" ou "SOMA" no nome
    cols_proibidas = [c for c in df.columns if 'TOTAL' in str(c).upper() or 'SOMA' in str(c).upper()]
    if cols_proibidas:
        df = df.drop(columns=cols_proibidas)

    # 4.3 VALIDAÇÃO DE ESTRUTURA
    # Garante que as colunas chaves existem antes de prosseguir
    colunas_id = ['CONTRATANTE', 'OBRAS', 'COORDENADOR', 'GERENCIA EXECUTIVA']
    for col in colunas_id:
        if col not in df.columns:
            st.error(f"Coluna obrigatória '{col}' não encontrada no arquivo.")
            return None

    # 4.4 UNPIVOT (TRANSFORMAÇÃO MATRIZ -> LISTA)
    # Transforma colunas de Treinamento (NR10, NR35...) em linhas de dados
    df_melted = df.melt(id_vars=colunas_id, var_name='Treinamento', value_name='Valor_Bruto')

    # --------------------------------------------------------------------------
    # 4.5 MOTOR DE CLASSIFICAÇÃO (LÓGICA DE NEGÓCIO)
    # --------------------------------------------------------------------------
    def classificar_seguro(valor):
        """
        Analisa o conteúdo da célula e decide:
        - É Custo? (Externo)
        - É Saving? (Interno)
        - É Lixo? (N/A, Vazio -> Ignorar)
        """
        # Checa se é vazio/nulo
        if pd.isna(valor) or str(valor).strip() in ['', '-', 'nan', 'None']:
            return None, None
            
        val_str = str(valor).strip().upper()
        
        # REGRA DE EXCLUSÃO: Se for N/A ou Sem Realização, ignora a linha
        if val_str in ['N/A', 'NA', 'N.A', 'SEM REALIZAÇÃO']:
            return None, None 

        # REGRA DE SAVING: Se contiver "INTERNO" ou "PRUMO"
        if 'INTERNO' in val_str or 'PRUMO' in val_str:
            return 0.0, 'Interno (SESMT)'

        # REGRA DE CUSTO: Se for numérico
        if isinstance(valor, (int, float)):
            if valor > 0: return float(valor), 'Externo (Custo)'
            return None, None

        # REGRA DE CUSTO (STRING): Tenta converter "R$ 1.200,00" para float
        try:
            limpo = val_str.replace('R$', '').replace(' ', '')
            if ',' in limpo:
                limpo = limpo.replace('.', '').replace(',', '.') # Inverte pontuação BR -> US
            custo = float(limpo)
            if custo > 0: return custo, 'Externo (Custo)'
        except:
            return None, None # Se falhar, considera lixo
            
        return None, None
    # --------------------------------------------------------------------------

    # Aplica a classificação linha a linha
    resultado = df_melted['Valor_Bruto'].apply(classificar_seguro).tolist()
    
    # Cria novas colunas processadas
    df_melted['Custo_Final'] = [x[0] for x in resultado]
    df_melted['Status'] = [x[1] for x in resultado]
    
    # Remove linhas inválidas (que retornaram None na classificação)
    df_limpo = df_melted.dropna(subset=['Status'])
    
    # Padroniza nomes dos treinamentos (ex: "NR - 10" vira "NR 10")
    df_limpo['Treinamento'] = df_limpo['Treinamento'].str.replace('NR - ', 'NR ').str.strip()

    # Cria coluna oculta para Busca Global (Concatena todos os campos de texto)
    df_limpo['BUSCA_GERAL'] = (
        df_limpo['Treinamento'].astype(str) + " " + 
        df_limpo['OBRAS'].astype(str) + " " + 
        df_limpo['COORDENADOR'].astype(str) + " " + 
        df_limpo['GERENCIA EXECUTIVA'].astype(str) + " " +
        df_limpo['CONTRATANTE'].astype(str)
    ).str.upper()

    return df_limpo

# Executa o carregamento inicial
df = carregar_dados_final()


# ==============================================================================
# 5. BARRA LATERAL (FILTROS)
# ==============================================================================

if df is not None:
    st.sidebar.title("Filtros")
    
    # Filtro 1: Busca Global Inteligente
    termo_busca = st.sidebar.text_input("Busca Global", placeholder="Ex: NR 10, Coordenador...", label_visibility="collapsed")
    
    # Aplica filtro de busca na base global
    df_global = df.copy()
    if termo_busca:
        df_global = df_global[df_global['BUSCA_GERAL'].str.contains(termo_busca.upper(), na=False)]
    
    st.sidebar.divider()
    
    # Filtros Hierárquicos (Um filtra as opções do próximo)
    # 1. Contratante
    opt_contratante = sorted(df_global['CONTRATANTE'].astype(str).unique())
    sel_contratante = st.sidebar.multiselect("Contratante", opt_contratante, default=opt_contratante)
    df_f1 = df_global[df_global['CONTRATANTE'].isin(sel_contratante)]
    
    # 2. Gerência Executiva
    opt_gerencia = sorted(df_f1['GERENCIA EXECUTIVA'].astype(str).unique())
    sel_gerencia = st.sidebar.multiselect("Gerência Executiva", opt_gerencia, default=opt_gerencia)
    df_f2 = df_f1[df_f1['GERENCIA EXECUTIVA'].isin(sel_gerencia)]

    # 3. Coordenador
    opt_coord = sorted(df_f2['COORDENADOR'].astype(str).unique())
    sel_coord = st.sidebar.multiselect("Coordenador", opt_coord, default=opt_coord)
    df_f3 = df_f2[df_f2['COORDENADOR'].isin(sel_coord)]

    # 4. Obras
    opt_obras = sorted(df_f3['OBRAS'].astype(str).unique())
    sel_obras = st.sidebar.multiselect("Obras", opt_obras, default=opt_obras)
    df_f4 = df_f3[df_f3['OBRAS'].isin(sel_obras)]

    # 5. Treinamento Específico
    opt_treino = sorted(df_f4['Treinamento'].astype(str).unique())
    sel_treino = st.sidebar.multiselect("Treinamentos", opt_treino, default=[])
    
    # Dataframe Final pronto para uso
    df_filtered = df_f4.copy()
    if sel_treino:
        df_filtered = df_filtered[df_filtered['Treinamento'].isin(sel_treino)]


    # ==========================================================================
    # 6. CÁLCULO DE KPIS (INDICADORES)
    # ==========================================================================
    
    # KPI Investimento: Soma tudo que é classificado como 'Externo'
    inv_total = df_filtered[df_filtered['Status'] == 'Externo (Custo)']['Custo_Final'].sum()
    
    # KPI Quantidade Interna
    qtd_interno = len(df_filtered[df_filtered['Status'] == 'Interno (SESMT)'])
    
    # KPI Saving: Quantidade Interna * Valor de Mercado (R$ 200,00)
    # (Para alterar o valor do saving, mude o número 200.00 abaixo)
    saving = qtd_interno * 200.00
    
    # KPI Quantidade Total (Registros Válidos)
    qtd_total = len(df_filtered)
    
    # KPI Maior Investidor: Agrupa por coordenador e vê quem tem maior custo
    top_inv = df_filtered[df_filtered['Status']=='Externo (Custo)'].groupby('COORDENADOR')['Custo_Final'].sum().sort_values(ascending=False)
    nome_inv = top_inv.index[0] if not top_inv.empty else "N/A"
    val_inv = top_inv.iloc[0] if not top_inv.empty else 0


    # ==========================================================================
    # 7. CONSTRUÇÃO DO DASHBOARD (VISUALIZAÇÃO)
    # ==========================================================================

    st.title("COORDENAÇÃO DG | Dashboard QSSMA")
    st.markdown("**Gestão de Custos e Treinamentos Normativos**")
    st.divider()

    # --- 7.1 CARTÕES DE MÉTRICAS (LINHA SUPERIOR) ---
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Investimento Total", formatar_brl(inv_total))
    c2.metric("Total Registros", qtd_total)
    
    # O texto "Economia: R$..." ficará verde devido ao hack CSS
    c3.metric("Realizados Internamente", qtd_interno, delta=f"Economia: {formatar_brl(saving)}")
    
    c4.metric("Maior Investidor", formatar_brl(val_inv), delta=nome_inv, delta_color="inverse")

    st.divider()

    # --- 7.2 GRÁFICOS PRINCIPAIS (LINHA DO MEIO) ---
    col_orig1, col_orig2 = st.columns([2, 1])
    
    # GRÁFICO 1: TOP 10 CUSTOS POR TREINAMENTO
    with col_orig1:
        st.subheader("💰 Top 10 Custos (Por Treinamento)")
        df_ext = df_filtered[df_filtered['Status'] == 'Externo (Custo)']
        
        if not df_ext.empty:
            df_chart = df_ext.groupby('Treinamento')['Custo_Final'].sum().reset_index().sort_values('Custo_Final', ascending=True).tail(10)
            df_chart['fmt'] = df_chart['Custo_Final'].apply(formatar_brl)
            
            fig = px.bar(df_chart, x='Custo_Final', y='Treinamento', orientation='h', text='fmt')
            # Cor Marrom para indicar Custo
            fig.update_traces(marker_color=COR_PRUMO_BROWN, textfont_color='white')
            fig.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem custos externos registrados para esta seleção.")
    
    # GRÁFICO 2: PIZZA DE STATUS
    with col_orig2:
        st.subheader("📌 Status da Demanda")
        df_pie = df_filtered['Status'].value_counts().reset_index()
        df_pie.columns = ['Status', 'Qtd']
        
        # Mapa de cores da identidade visual
        cores = {
            'Externo (Custo)': COR_PRUMO_BROWN,   # Marrom
            'Interno (SESMT)': COR_PRUMO_ORANGE,  # Laranja
            'Não Aplicável (N/A)': '#D1D5DB'      # Cinza
        }
        fig2 = px.pie(df_pie, values='Qtd', names='Status', hole=0.6, color='Status', color_discrete_map=cores)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- 7.3 RANKINGS COMPARATIVOS (NOVA SEÇÃO) ---
    st.markdown("### 📈 Rankings Comparativos")
    
    # Seletor de Agrupamento Dinâmico
    col_sel, _ = st.columns([1, 4])
    with col_sel:
        agrupar = st.selectbox("Comparar por:", ["COORDENADOR", "OBRAS", "GERENCIA EXECUTIVA"], index=0)

    g_new1, g_new2, g_new3 = st.columns(3)

    # RANKING 1: QUEM GASTA MAIS (EXTERNO)
    with g_new1:
        st.markdown("**💸 Quem mais investe? (Externo)**")
        df_rank_ext = df_filtered[df_filtered['Status']=='Externo (Custo)'].groupby(agrupar)['Custo_Final'].sum().reset_index()
        df_rank_ext = df_rank_ext.sort_values('Custo_Final', ascending=True).tail(10)
        
        if not df_rank_ext.empty:
            df_rank_ext['fmt'] = df_rank_ext['Custo_Final'].apply(formatar_brl)
            fig_r1 = px.bar(df_rank_ext, x='Custo_Final', y=agrupar, orientation='h', text='fmt')
            fig_r1.update_traces(marker_color=COR_PRUMO_BROWN, textfont_color='white') # Marrom
            fig_r1.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_r1, use_container_width=True)
        else:
            st.info("Sem dados de custo.")

    # RANKING 2: QUEM GERA MAIS ECONOMIA (INTERNO)
    with g_new2:
        st.markdown("**🛡️ Quem mais gera Saving? (Interno)**")
        df_rank_int = df_filtered[df_filtered['Status']=='Interno (SESMT)'].groupby(agrupar).size().reset_index(name='Qtd')
        df_rank_int['Valor_Saving'] = df_rank_int['Qtd'] * 200.00
        df_rank_int = df_rank_int.sort_values('Valor_Saving', ascending=True).tail(10)
        
        if not df_rank_int.empty:
            df_rank_int['fmt'] = df_rank_int['Valor_Saving'].apply(formatar_brl)
            fig_r2 = px.bar(df_rank_int, x='Valor_Saving', y=agrupar, orientation='h', text='fmt')
            # Laranja (Identidade visual para Interno)
            fig_r2.update_traces(marker_color=COR_PRUMO_ORANGE, textfont_color='white') 
            fig_r2.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_r2, use_container_width=True)
        else:
            st.info("Sem dados de saving.")

    # RANKING 3: EFICIÊNCIA (VOLUME)
    with g_new3:
        st.markdown("**📊 Eficiência (Interno vs Externo)**")
        # Prepara dados empilhados
        df_prop = df_filtered.groupby([agrupar, 'Status']).size().reset_index(name='Qtd')
        # Filtra os 10 maiores volumes totais
        top_vol = df_prop.groupby(agrupar)['Qtd'].sum().sort_values(ascending=False).head(10).index
        df_prop = df_prop[df_prop[agrupar].isin(top_vol)]
        
        # Cores consistentes
        cores_prop = {'Externo (Custo)': COR_PRUMO_BROWN, 'Interno (SESMT)': COR_PRUMO_ORANGE}
        fig_r3 = px.bar(df_prop, x='Qtd', y=agrupar, color='Status', orientation='h', 
                        color_discrete_map=cores_prop, text='Qtd')
        fig_r3.update_layout(xaxis_title="Qtd", yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', 
                             legend=dict(orientation="h", y=-0.2), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_r3, use_container_width=True)

    st.divider()

    # --- 7.4 TABELAS FINAIS ---
    tab_det, tab_audit = st.tabs(["📋 Detalhamento da Base", "🕵️‍♂️ Auditoria de Valores"])
    
    with tab_det:
        # Tabela limpa para consulta
        df_show = df_filtered[['OBRAS', 'COORDENADOR', 'GERENCIA EXECUTIVA', 'Treinamento', 'Status', 'Custo_Final']].copy()
        df_show['Custo Visual'] = df_show['Custo_Final'].apply(formatar_brl)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    with tab_audit:
        # Tabela para encontrar erros de lançamento no Excel
        st.info("Auditoria de Valores (Top 50 Maiores Custos Unitários)")
        audit = df_filtered[df_filtered['Status'] == 'Externo (Custo)'].sort_values('Custo_Final', ascending=False).head(50)
        audit['Valor'] = audit['Custo_Final'].apply(formatar_brl)
        st.dataframe(audit[['Treinamento', 'OBRAS', 'COORDENADOR', 'Valor']], use_container_width=True)