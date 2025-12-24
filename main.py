import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 경로 설정 (main.py 기준)
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ===============================
# 상수
# ===============================
EC_TARGET = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# ===============================
# 한글 파일명 안전 탐색
# ===============================
def find_file_by_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for file in directory.iterdir():
        name_nfc = unicodedata.normalize("NFC", file.name)
        name_nfd = unicodedata.normalize("NFD", file.name)
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return file
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    env = {}
    for school in EC_TARGET:
        path = find_file_by_name(DATA_DIR, f"{school}_환경데이터.csv")
        if path is None:
            st.error(f"{school}_환경데이터.csv 파일을 찾을 수 없다.")
            return None
        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"])
        df["학교"] = school
        env[school] = df
    return env

@st.cache_data
def load_growth_data():
    path = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if path is None:
        st.error("4개교_생육결과데이터.xlsx 파일을 찾을 수 없다.")
        return None

    xls = pd.ExcelFile(path)
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        df["EC"] = EC_TARGET[sheet]
        data[sheet] = df
    return data

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ===============================
# 사이드바
# ===============================
school_option = st.sidebar.selectbox(
    "학교 선택", ["전체"] + list(EC_TARGET.keys())
)

st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1
# ===============================
with tab1:
    all_env = pd.concat(env_data.values())
    all_growth = pd.concat(growth_data.values())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", len(all_growth))
    col2.metric("평균 온도", f"{all_env['temperature'].mean():.2f} ℃")
    col3.metric("평균 습도", f"{all_env['humidity'].mean():.2f} %")
    col4.metric("최적 EC", "2.0 (하늘고)")

# ===============================
# Tab 2
# ===============================
with tab2:
    avg_df = all_env.groupby("학교").mean(numeric_only=True).reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "EC 비교")
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(
        x=list(EC_TARGET.keys()),
        y=list(EC_TARGET.values()),
        name="목표 EC",
        row=2, col=2
    )

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic")
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("환경 데이터 원본 및 다운로드"):
        all_env_sorted = all_env.sort_values("time")
        st.dataframe(all_env_sorted, use_container_width=True)

        csv_buffer = io.BytesIO()
        all_env_sorted.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        csv_buffer.seek(0)

        st.download_button(
            label="환경데이터 CSV 다운로드",
            data=csv_buffer.getvalue(),
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ===============================
# Tab 3
# ===============================
with tab3:
    mean_weight = all_growth.groupby("EC")["생중량(g)"].mean().reset_index()
    best_ec = mean_weight.loc[mean_weight["생중량(g)"].idxmax(), "EC"]

    st.metric("🥇 최적 EC (평균 생중량 최대)", best_ec)

    fig = px.bar(mean_weight, x="EC", y="생중량(g)")
    fig.update_layout(font=dict(family="Malgun Gothic"))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("생육 데이터 원본 및 다운로드"):
        st.dataframe(all_growth, use_container_width=True)

        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            label="생육결과 XLSX 다운로드",
            data=buffer.getvalue(),
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
