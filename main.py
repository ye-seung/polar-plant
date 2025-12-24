import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

# 한글 폰트 (CSS)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# ✅ 데이터 폴더 경로 (핵심 수정)
# main.py 기준 data 폴더
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ===============================
# 상수 정의
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
# 한글 파일명 안전 탐색 (NFC/NFD)
# ===============================
def find_file_by_name(directory: Path, target_name: str):
    if not directory.exists():
        st.error(f"데이터 폴더를 찾을 수 없다: {directory}")
        return None

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
    env_data = {}

    for school in EC_TARGET.keys():
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_by_name(DATA_DIR, filename)

        if file_path is None:
            st.error(f"{filename} 파일을 찾을 수 없다.")
            return None

        df = pd.read_csv(file_path)
        df["time"] = pd.to_datetime(df["time"])
        df["학교"] = school
        env_data[school] = df

    return env_data

@st.cache_data
def load_growth_data():
    file_path = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")

    if file_path is None:
        st.error("4개교_생육결과데이터.xlsx 파일을 찾을 수 없다.")
        return None

    xls = pd.ExcelFile(file_path)
    growth_data = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        df["EC"] = EC_TARGET.get(sheet)
        growth_data[sheet] = df

    return growth_data

# ===============================
# 데이터 로딩 실행
# ===============================
with st.spinner("데이터를 불러오는 중이다..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(EC_TARGET.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# Tab 1: 실험 개요
# ======================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write(
        "본 연구는 서로 다른 EC 농도 조건에서 재배된 극지식물의 생육 결과를 비교하여 "
        "최적의 EC 농도를 도출하는 것을 목적으로 한다."
    )

    summary_rows = []
    total_plants = 0

    for school, df in growth_data.items():
        count = len(df)
        total_plants += count
        summary_rows.append([school, EC_TARGET[school], count, SCHOOL_COLOR[school]])

    summary_df = pd.DataFrame(
        summary_rows,
        columns=["학교명", "EC 목표", "개체수", "표시 색상"]
    )

    st.dataframe(summary_df, use_container_width=True)

    all_env = pd.concat(env_data.values())
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("총 개체수", total_plants)
    col2.metric("평균 온도", f"{all_env['temperature'].mean():.2f} ℃")
    col3.metric("평균 습도", f"{all_env['humidity'].mean():.2f} %")
    col4.metric("최적 EC", "2.0 (하늘고)")

# ======================================================
# Tab 2: 환경 데이터
# ===============================
