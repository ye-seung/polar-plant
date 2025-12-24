import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import unicodedata
from pathlib import Path
import io

# 페이지 설정
st.set_page_config(
    page_title="극지식물 EC 농도 연구",
    page_icon="🌱",
    layout="wide"
)

# 한글 폰트 설정
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 학교별 설정
SCHOOL_CONFIG = {
    "송도고": {"ec": 1.0, "color": "#FF6B6B", "samples": 29},
    "하늘고": {"ec": 2.0, "color": "#4ECDC4", "samples": 45},
    "아라고": {"ec": 4.0, "color": "#95E1D3", "samples": 106},
    "동산고": {"ec": 8.0, "color": "#FFE66D", "samples": 58}
}

def normalize_filename(name):
    """파일명 정규화 (NFC/NFD 모두 처리)"""
    return unicodedata.normalize("NFC", name)

@st.cache_data
def load_env_data():
    """환경 데이터 로딩 (CSV 4개)"""
    data_path = Path("data")
    env_data = {}
    
    if not data_path.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다.")
        return env_data
    
    # 모든 CSV 파일 탐색
    for file_path in data_path.iterdir():
        if file_path.suffix.lower() == '.csv':
            filename = normalize_filename(file_path.name)
            
            # 학교명 추출
            for school in SCHOOL_CONFIG.keys():
                school_normalized = normalize_filename(school)
                if school_normalized in filename:
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8-sig')
                        env_data[school] = df
                        break
                    except Exception as e:
                        st.warning(f"⚠️ {filename} 로딩 실패: {e}")
    
    return env_data

@st.cache_data
def load_growth_data():
    """생육 데이터 로딩 (XLSX 1개, 4개 시트)"""
    data_path = Path("data")
    growth_data = {}
    
    if not data_path.exists():
        return growth_data
    
    # XLSX 파일 찾기
    xlsx_files = list(data_path.glob("*.xlsx"))
    
    if not xlsx_files:
        st.error("❌ 생육결과 XLSX 파일을 찾을 수 없습니다.")
        return growth_data
    
    xlsx_path = xlsx_files[0]
    
    try:
        # 모든 시트 읽기
        excel_file = pd.ExcelFile(xlsx_path)
        
        for sheet_name in excel_file.sheet_names:
            sheet_normalized = normalize_filename(sheet_name)
            
            # 학교명 매칭
            for school in SCHOOL_CONFIG.keys():
                school_normalized = normalize_filename(school)
                if school_normalized in sheet_normalized:
                    df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
                    growth_data[school] = df
                    break
        
    except Exception as e:
        st.error(f"❌ XLSX 파일 로딩 실패: {e}")
    
    return growth_data

def calculate_school_stats(env_data, growth_data, school):
    """학교별 통계 계산"""
    stats = {}
    
    # 환경 데이터 통계
    if school in env_data:
        env_df = env_data[school]
        stats['temp_avg'] = env_df['temperature'].mean()
        stats['humidity_avg'] = env_df['humidity'].mean()
        stats['ph_avg'] = env_df['ph'].mean()
        stats['ec_avg'] = env_df['ec'].mean()
    
    # 생육 데이터 통계
    if school in growth_data:
        growth_df = growth_data[school]
        stats['weight_avg'] = growth_df['생중량(g)'].mean()
        stats['leaf_avg'] = growth_df['잎 수(장)'].mean()
        stats['above_avg'] = growth_df['지상부 길이(mm)'].mean()
        stats['below_avg'] = growth_df['지하부길이(mm)'].mean()
        stats['sample_count'] = len(growth_df)
    
    return stats

# 메인 앱
def main():
    st.title("🌱 pH와 EC에 따른 나도수영 생중량 분석")
    
    # 데이터 로딩
    with st.spinner("📊 데이터 로딩 중..."):
        env_data = load_env_data()
        growth_data = load_growth_data()
    
    if not env_data or not growth_data:
        st.error("❌ 데이터를 불러올 수 없습니다. data 폴더와 파일을 확인해주세요.")
        return
    
    # 사이드바
    st.sidebar.header("🔍 학교 선택")
    school_options = ["전체"] + list(SCHOOL_CONFIG.keys())
    selected_school = st.sidebar.selectbox("학교를 선택하세요", school_options)
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🧪 pH와 생중량", "⚡ EC와 생중량"])
    
    # 탭1: 실험 개요
    with tab1:
        st.header("연구 배경 및 목적")
        st.markdown("""
        본 연구는 **극지식물 나도수영**의 최적 재배 조건을 찾기 위해 4개 학교에서 서로 다른 **EC 농도**로 
        재배 실험을 진행하였습니다. pH, 온도, 습도 등의 환경 요인과 생중량의 관계를 분석하여 
        최적의 생육 조건을 도출합니다.
        """)
        
        # 학교별 EC 조건 표
        st.subheader("📋 학교별 EC 조건")
        config_df = pd.DataFrame([
            {
                "학교명": school,
                "EC 목표": f"{config['ec']} dS/m",
                "개체수": f"{config['samples']}개",
                "대표색상": config['color']
            }
            for school, config in SCHOOL_CONFIG.items()
        ])
        st.dataframe(config_df, use_container_width=True, hide_index=True)
        
        # 주요 지표 카드
        st.subheader("📊 주요 지표")
        
        total_samples = sum(config['samples'] for config in SCHOOL_CONFIG.values())
        all_temps = [stats['temp_avg'] for school in SCHOOL_CONFIG.keys() 
                     if (stats := calculate_school_stats(env_data, growth_data, school)) 
                     and 'temp_avg' in stats]
        all_humidity = [stats['humidity_avg'] for school in SCHOOL_CONFIG.keys() 
                        if (stats := calculate_school_stats(env_data, growth_data, school)) 
                        and 'humidity_avg' in stats]
        
        avg_temp = sum(all_temps) / len(all_temps) if all_temps else 0
        avg_humidity = sum(all_humidity) / len(all_humidity) if all_humidity else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 개체수", f"{total_samples}개")
        with col2:
            st.metric("평균 온도", f"{avg_temp:.1f}°C")
        with col3:
            st.metric("평균 습도", f"{avg_humidity:.1f}%")
        with col4:
            st.metric("최적 EC", "2.0 dS/m", delta="하늘고")
        
        # 학교별 환경 데이터 그래프
        st.subheader("🌡️ 학교별 환경 데이터 비교")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("EC 평균", "pH 평균", "온도 평균", "습도 평균"),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        schools = list(SCHOOL_CONFIG.keys())
        ec_values = []
        ph_values = []
        temp_values = []
        humidity_values = []
        
        for school in schools:
            stats = calculate_school_stats(env_data, growth_data, school)
            ec_values.append(stats.get('ec_avg', 0))
            ph_values.append(stats.get('ph_avg', 0))
            temp_values.append(stats.get('temp_avg', 0))
            humidity_values.append(stats.get('humidity_avg', 0))
        
        colors = [SCHOOL_CONFIG[s]['color'] for s in schools]
        
        # EC
        fig.add_trace(go.Scatter(x=schools, y=ec_values, mode='lines+markers',
                                 line=dict(color='#FF6B6B', width=3),
                                 marker=dict(size=10, color=colors),
                                 name='EC'), row=1, col=1)
        
        # pH
        fig.add_trace(go.Scatter(x=schools, y=ph_values, mode='lines+markers',
                                 line=dict(color='#4ECDC4', width=3),
                                 marker=dict(size=10, color=colors),
                                 name='pH'), row=1, col=2)
        
        # 온도
        fig.add_trace(go.Scatter(x=schools, y=temp_values, mode='lines+markers',
                                 line=dict(color='#95E1D3', width=3),
                                 marker=dict(size=10, color=colors),
                                 name='온도'), row=2, col=1)
        
        # 습도
        fig.add_trace(go.Scatter(x=schools, y=humidity_values, mode='lines+markers',
                                 line=dict(color='#FFE66D', width=3),
                                 marker=dict(size=10, color=colors),
                                 name='습도'), row=2, col=2)
        
        fig.update_xaxes(title_text="학교", row=2, col=1)
        fig.update_xaxes(title_text="학교", row=2, col=2)
        fig.update_yaxes(title_text="EC (dS/m)", row=1, col=1)
        fig.update_yaxes(title_text="pH", row=1, col=2)
        fig.update_yaxes(title_text="온도 (°C)", row=2, col=1)
        fig.update_yaxes(title_text="습도 (%)", row=2, col=2)
        
        fig.update_layout(
            height=600,
            showlegend=False,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 탭2: pH와 생중량
    with tab2:
        st.header("🧪 pH와 생중량의 관계")
        
        schools = list(SCHOOL_CONFIG.keys())
        ph_values = []
        weight_values = []
        
        for school in schools:
            stats = calculate_school_stats(env_data, growth_data, school)
            ph_values.append(stats.get('ph_avg', 0))
            weight_values.append(stats.get('weight_avg', 0))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=ph_values,
            y=weight_values,
            mode='lines+markers+text',
            marker=dict(
                size=15,
                color=[SCHOOL_CONFIG[s]['color'] for s in schools],
                line=dict(width=2, color='white')
            ),
            line=dict(width=3, color='rgba(100,100,100,0.3)'),
            text=schools,
            textposition="top center",
            textfont=dict(size=12, color='black'),
            name='학교별 데이터'
        ))
        
        fig.update_layout(
            title="pH에 따른 생중량 변화",
            xaxis_title="pH 평균",
            yaxis_title="생중량 평균 (g)",
            height=500,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=14),
            hovermode='closest',
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 상관관계 분석
        col1, col2 = st.columns(2)
        
        with col1:
            correlation = pd.Series(ph_values).corr(pd.Series(weight_values))
            st.metric("pH-생중량 상관계수", f"{correlation:.3f}")
        
        with col2:
            optimal_idx = weight_values.index(max(weight_values))
            optimal_school = schools[optimal_idx]
            st.metric("최대 생중량 학교", optimal_school, 
                     delta=f"pH {ph_values[optimal_idx]:.2f}")
    
    # 탭3: EC와 생중량
    with tab3:
        st.header("⚡ EC와 생중량의 관계")
        
        schools = list(SCHOOL_CONFIG.keys())
        ec_values = []
        weight_values = []
        ph_values = []
        
        for school in schools:
            stats = calculate_school_stats(env_data, growth_data, school)
            ec_values.append(stats.get('ec_avg', 0))
            weight_values.append(stats.get('weight_avg', 0))
            ph_values.append(stats.get('ph_avg', 0))
        
        # EC와 생중량 관계
        fig1 = go.Figure()
        
        fig1.add_trace(go.Scatter(
            x=ec_values,
            y=weight_values,
            mode='lines+markers+text',
            marker=dict(
                size=15,
                color=[SCHOOL_CONFIG[s]['color'] for s in schools],
                line=dict(width=2, color='white')
            ),
            line=dict(width=3, color='rgba(100,100,100,0.3)'),
            text=schools,
            textposition="top center",
            textfont=dict(size=12, color='black'),
            name='학교별 데이터'
        ))
        
        # 최적 EC 강조 (하늘고)
        optimal_idx = schools.index("하늘고")
        fig1.add_annotation(
            x=ec_values[optimal_idx],
            y=weight_values[optimal_idx],
            text="최적 조건",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            ax=40,
            ay=-40,
            font=dict(size=14, color="red", family="Malgun Gothic")
        )
        
        fig1.update_layout(
            title="EC에 따른 생중량 변화",
            xaxis_title="EC 평균 (dS/m)",
            yaxis_title="생중량 평균 (g)",
            height=500,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=14),
            hovermode='closest',
            plot_bgcolor='rgba(240,240,240,0.5)'
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # 상관관계 분석
        col1, col2 = st.columns(2)
        
        with col1:
            correlation = pd.Series(ec_values).corr(pd.Series(weight_values))
            st.metric("EC-생중량 상관계수", f"{correlation:.3f}")
        
        with col2:
            optimal_idx = weight_values.index(max(weight_values))
            optimal_school = schools[optimal_idx]
            st.metric("최대 생중량 학교", optimal_school, 
                     delta=f"EC {ec_values[optimal_idx]:.2f}")
        
        st.markdown("---")
        
        # EC, pH, 생중량 통합 그래프
        st.subheader("🔬 EC, pH, 생중량 통합 분석")
        
        fig2 = go.Figure()
        
        # 3D scatter plot
        fig2.add_trace(go.Scatter3d(
            x=ec_values,
            y=ph_values,
            z=weight_values,
            mode='markers+text',
            marker=dict(
                size=12,
                color=weight_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="생중량 (g)"),
                line=dict(width=1, color='white')
            ),
            text=schools,
            textposition="top center",
            textfont=dict(size=10, color='black'),
            name='학교별 데이터'
        ))
        
        fig2.update_layout(
            title="EC, pH, 생중량의 3차원 관계",
            scene=dict(
                xaxis_title="EC (dS/m)",
                yaxis_title="pH",
                zaxis_title="생중량 (g)",
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.3))
            ),
            height=600,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # 결과 요약
        st.subheader("📈 분석 결과 요약")
        
        summary_data = []
        for i, school in enumerate(schools):
            summary_data.append({
                "학교": school,
                "EC (dS/m)": f"{ec_values[i]:.2f}",
                "pH": f"{ph_values[i]:.2f}",
                "생중량 (g)": f"{weight_values[i]:.3f}",
                "순위": ""
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('생중량 (g)', ascending=False).reset_index(drop=True)
        summary_df['순위'] = range(1, len(summary_df) + 1)
        
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # 다운로드 버튼
        buffer = io.BytesIO()
        summary_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        
        st.download_button(
            label="📥 결과 다운로드 (XLSX)",
            data=buffer,
            file_name="극지식물_EC분석_결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
