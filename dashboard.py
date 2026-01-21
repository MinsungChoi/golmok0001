import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page config
st.set_page_config(page_title="서울시 상권 종합 분석 대시보드", layout="wide")

# Set Korean font for Matplotlib
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

@st.cache_data
def load_data():
    sales = pd.read_csv("서울시_상권분석서비스(추정매출-서울시).csv", encoding='cp949')
    income = pd.read_csv("서울시 상권분석서비스(소득소비-상권).csv", encoding='cp949')
    stores = pd.read_csv("서울시_상권분석서비스(점포상권).csv", encoding='cp949')
    workplace = pd.read_csv("서울시_상권분석서비스(직장인구-상권).csv", encoding='cp949')
    metadata = pd.read_csv("소상공인시장진흥공단_주요상권현황_20240101 (2).csv", encoding='cp949')
    
    # Pre-add year/quarter columns to all relevant dfs
    for df in [sales, income, stores, workplace]:
        df['연도'] = df['기준_년분기_코드'] // 10
        df['분기'] = df['기준_년분기_코드'] % 10
        
    return sales, income, stores, workplace, metadata

sales_df, income_df, stores_df, workplace_df, metadata_df = load_data()

st.title("📊 서울시 상권 5대 데이터셋 통합 대시보드")
st.markdown("""
본 대시보드는 **매출, 소득/소비, 점포현황, 직장인구, 상권마스터** 데이터를 기반으로 서울시 골목 상권을 다각도로 진단합니다.
""")

# Sidebar settings
st.sidebar.header("🔍 분석 범위 설정")
years = sorted(sales_df['연도'].unique(), reverse=True)
selected_year = st.sidebar.selectbox("연도 선택", years, index=0)

quarter_options = ["전체 (연간 합산/평균)"] + sorted([str(q) for q in sales_df[sales_df['연도'] == selected_year]['분기'].unique()], reverse=True)
selected_q_label = st.sidebar.selectbox("분기 선택", quarter_options, index=0)

# Data Filtering & Aggregation Logic
if "전체" in selected_q_label:
    # Aggregation for the whole year
    s_f = sales_df[sales_df['연도'] == selected_year]
    i_raw = income_df[income_df['연도'] == selected_year]
    st_raw = stores_df[stores_df['연도'] == selected_year]
    w_raw = workplace_df[workplace_df['연도'] == selected_year]
    
    # Aggregate Income: mean for income, sum for expenditures
    spend_cols = [c for c in income_df.columns if '지출_총금액' in c]
    i_f = i_raw.groupby(['상권_코드', '상권_코드_명', '상권_구분_코드_명']).agg({
        '월_평균_소득_금액': 'mean',
        **{col: 'sum' for col in spend_cols}
    }).reset_index()
    
    # Aggregate Stores: average counts and rates per quarter
    st_f = st_raw.groupby(['상권_코드', '상권_코드_명', '서비스_업종_코드_명']).agg({
        '점포_수': 'mean',
        '개업_율': 'mean',
        '폐업_률': 'mean'
    }).reset_index()
    
    # Aggregate Workplace: average population
    w_age_cols = [c for c in workplace_df.columns if '직장_인구_수' in c]
    w_f = w_raw.groupby(['상권_코드', '상권_코드_명']).agg({
        '총_직장_인구_수': 'mean',
        **{col: 'mean' for col in w_age_cols}
    }).reset_index()
    
    display_period = f"{selected_year}년 전체"
else:
    q = int(selected_q_label)
    selected_q = int(f"{selected_year}{q}")
    s_f = sales_df[sales_df['기준_년분기_코드'] == selected_q]
    i_f = income_df[income_df['기준_년분기_코드'] == selected_q]
    st_f = stores_df[stores_df['기준_년분기_코드'] == selected_q]
    w_f = workplace_df[workplace_df['기준_년분기_코드'] == selected_q]
    display_period = f"{selected_year}년 {q}분기"

# Tabs
tabs = st.tabs(["💡 통합 주제", "📈 매출 트렌드", "💰 소득/소비", "🏪 점포/생존력", "💼 직장인구", "🧠 전략 인사이트"])

# Tab 1: Themes
with tabs[0]:
    st.header(f"🎯 {display_period} 데이터 통합 분석 주제")
    st.markdown("""
    *   **입체적 상권 진단**: 단순 매출액을 넘어 배후 인구의 소득 수준과 실제 점포의 폐업률을 연계하여 상권의 '체력'을 측정합니다.
    *   **공급 과잉 모니터링**: 특정 업종의 점포 수가 급증할 때 매출 효율성이 정체되는 구간을 탐색합니다.
    *   **타겟 세대 최적화**: 직장인 인구의 연령대 비중과 매출 연령대 비중을 비교하여 '미스매치'가 발생하는 상권을 찾아냅니다.
    """)

# Tab 2: Sales
with tabs[1]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("업종별 매출 순위 (Top 10)")
        top_10 = s_f.groupby('서비스_업종_코드_명')['당월_매출_금액'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(top_10, x='당월_매출_금액', y='서비스_업종_코드_명', orientation='h', color='당월_매출_금액',
                     labels={'당월_매출_금액':'매출액', '서비스_업종_코드_명':'업종'}, color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"📝 **해석**: {display_period} 기준으로 가장 높은 매출을 기록한 업종은 '{top_10.iloc[0,0]}'입니다. 상위 업종들의 매출 규모를 통해 해당 시기의 서울시 핵심 소비 트렌드를 파악할 수 있습니다.")

    with col2:
        st.subheader("소비자 연령대 분포")
        age_cols = [c for c in s_f.columns if '연령대' in c and '금액' in c]
        age_sum = s_f[age_cols].sum()
        age_labels = [c.split('_')[1]+'대' for c in age_sum.index]
        fig = px.pie(values=age_sum.values, names=age_labels, hole=.3)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"📝 **해석**: 현재 상권의 주력 소비층은 **{age_labels[age_sum.argmax()]}**입니다. 타겟 마케팅 시 이 연령대의 라이프스타일을 최우선적으로 고려해야 합니다.")

# Tab 3: Income/Expenditure
with tabs[2]:
    st.subheader("상권 배후 소득 vs 지출 상관관계")
    i_plot = i_f.dropna(subset=['월_평균_소득_금액', '지출_총금액']).copy()
    i_plot = i_plot[i_plot['지출_총금액'] > 0]
    if not i_plot.empty:
        fig = px.scatter(i_plot, x='월_평균_소득_금액', y='지출_총금액', size='지출_총금액',
                         color='상권_구분_코드_명', hover_name='상권_코드_명', trendline="ols",
                         labels={'월_평균_소득_금액':'월 평균 소득', '지출_총금액':'지출 총액'})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("📝 **해석**: 소득과 지출의 상관관계를 보여줍니다. 회귀선 위쪽에 위치한 상권은 소득 대비 소비 성향이 강한 '활성 상권'이며, 아래쪽은 소득은 높으나 지향 지출이 적은 '잠재 상권'으로 분류됩니다.")
    
    st.subheader("세부 지출 항목 비중")
    spend_cols = [c for c in i_f.columns if '지출_총금액' in c and c != '지출_총금액']
    avg_spend = i_f[spend_cols].mean().sort_values()
    fig = px.pie(values=avg_spend.values, names=[c.replace('_지출_총금액','') for c in avg_spend.index], hole=.4)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("📝 **해석**: 실제 가계 지출이 어디에 집중되는지 보여줍니다. '식료품'이나 '의료비' 비중이 높을수록 필수재 중심 상권이며, '여가/문화' 비중이 높을수록 감성 소비형 상권의 특징을 가집니다.")

# Tab 4: Stores
with tabs[3]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("상권별 점포 밀집도 (상위 20)")
        top_stores = st_f.groupby('상권_코드_명')['점포_수'].sum().sort_values(ascending=False).head(20).reset_index()
        fig = px.bar(top_stores, x='점포_수', y='상권_코드_명', orientation='h', color='점포_수', color_continuous_scale='Reds')
        st.plotly_chart(fig, use_container_width=True)
        st.caption("📝 **해석**: 점포 수가 가장 밀집된 지역들입니다. 과도한 밀집은 과당 경쟁으로 이어질 수 있으므로, 해당 지역 진입 시 차별화 전략이 필수적입니다.")
    
    with col2:
        st.subheader("업종별 생존 지표 (개업률 vs 폐업률)")
        rate_by_biz = st_f.groupby('서비스_업종_코드_명')[['개업_율', '폐업_률']].mean().reset_index()
        if not rate_by_biz.empty:
            fig = px.scatter(rate_by_biz, x='개업_율', y='폐업_률', hover_name='서비스_업종_코드_명', text='서비스_업종_코드_명',
                             labels={'개업_율':'평균 개업률(%)', '폐업_률':'평균 폐업률(%)'})
            max_val = max(rate_by_biz['개업_율'].max(), rate_by_biz['폐업_률'].max())
            fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(dash="dash", color="gray"))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("📝 **해석**: 대각선(점선) 위에 있는 업종은 개업보다 폐업이 더 활발한 '위험 업종'입니다. 반대로 아래쪽 업종은 시장이 확장되고 있는 '성장 업종'으로 판단할 수 있습니다.")
        else:
            st.info("해당 기간의 점포 생존 지표 데이터가 없습니다.")

# Tab 5: Workplace
with tabs[4]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("직장인 유동인구 상위 상권")
        w_sum = w_f.groupby('상권_코드_명')['총_직장_인구_수'].sum().sort_values(ascending=False).head(20).reset_index()
        if not w_sum.empty:
            fig = px.bar(w_sum, x='총_직장_인구_수', y='상권_코드_명', orientation='h', color='총_직장_인구_수', color_continuous_scale='Greens')
            st.plotly_chart(fig, use_container_width=True)
            st.caption("📝 **해석**: 고정적인 배후 수요(직장인)가 풍부한 지역입니다. 이들 상권은 평일 점심 및 퇴근 시간대 소비가 핵심적인 매출원이 됩니다.")
        else:
            st.info("해당 기간의 직장인 인구 데이터가 없습니다.")
    
    with col2:
        st.subheader("직장인 연령대 분포")
        w_age_cols = [c for c in workplace_df.columns if '연령대' in c and '직장_인구_수' in c and '남성' not in c and '여성' not in c]
        w_age_sum = w_f[[c for c in w_age_cols if c in w_f.columns]].sum()
        if not w_age_sum.empty and w_age_sum.sum() > 0:
            w_labels = [c.split('_')[1]+'대' for c in w_age_sum.index]
            fig = px.pie(values=w_age_sum.values, names=w_labels)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"📝 **해석**: 이 지역의 직장인 인프라는 주로 **{w_labels[w_age_sum.argmax()]}**로 구성되어 있습니다. 직장인 대상 B2C 서비스 기획 시 핵심 타겟이 됩니다.")
        else:
            st.info("해당 기간의 직장인 연령대 분포 데이터가 없습니다.")

# Tab 6: Insights (Integrated)
with tabs[5]:
    st.header("💡 소상공인 활성화를 위한 통합 데이터 진단")
    st.markdown(f"""
    **{display_period}** 통합 분석 결과:
    
    1.  **적정 경쟁 구도 파악**: 점포 수가 유지되면서 개결 매출이 상승하는 업종을 우선적으로 지원해야 합니다.
    2.  **직장인 수요 연계**: 직장 인구가 많은 상권에서는 '시간 효율성'을 극대화한 서비스(예: 사전 주문 시스템)의 효용이 매우 높게 나타납니다.
    3.  **소득-지출 미스매치 활용**: 소득은 높으나 지출이 낮은 지역에 대해 프리미엄화된 소상공인 문화 콘텐츠(테마 상점가)를 조성하여 외부 유출을 막아야 합니다.
    """)
    st.success("상세한 수치 근거는 'revitalization_insights_rationale.md' 리포트에서 확인하실 수 있습니다.")
