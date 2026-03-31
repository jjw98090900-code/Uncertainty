import streamlit as st
import matplotlib.pyplot as plt

# ⚠️ [수정 1] 화면 설정은 무조건 가장 먼저 실행되어야 프레임워크 에러가 나지 않습니다.
st.set_page_config(layout="wide", page_title="sCO2 열교환기 불확도 평가 대시보드")

# ==========================================
# 보안: 접속 암호 검증 로직
# ==========================================
def check_password():
    """올바른 암호를 입력했는지 확인하는 함수"""
    def password_entered():
        # 설정하신 암호 "wndnjs"
        if st.session_state["password"] == "wndnjs":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 보안을 위해 입력 기록 삭제
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 최초 접속 시 암호 입력창 출력
        st.text_input("연구 데이터 보안을 위해 접속 암호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # 암호 틀렸을 시
        st.text_input("연구 데이터 보안을 위해 접속 암호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 암호가 일치하지 않습니다. 다시 입력해 주십시오.")
        return False
    return True

# 암호가 통과되지 않으면 여기서 아래 코드의 실행을 완전히 멈춤
if not check_password():
    st.stop()

# ==========================================
# ⚠️ [수정 2] 중복 임포트 제거 및 계산 엔진 호출
# ==========================================
try:
    import calc_engine # 이전에 파일명을 짧게 바꾸셨다면 우선 적용
except ModuleNotFoundError:
    import HeatExchangerUncertainty_Calculate as calc_engine # 원본 파일명 유지 시 적용

st.title("sCO2 열교환기 몬테카를로 불확도 평가 계산기")
st.markdown("---")

# ==========================================
# 좌측 사이드바: 사용자 입력(Input) UI 구성
# ==========================================
st.sidebar.header("운전 조건 및 센서 스펙 입력")

st.sidebar.subheader("1. 운전 조건 (Nominal)")
P_nom = st.sidebar.number_input("운전 압력 (MPa)", value=8.0, step=0.1)
T_in_nom = st.sidebar.number_input("입구 온도 (°C)", value=60.0, step=1.0)
T_out_nom = st.sidebar.number_input("출구 온도 (°C)", value=40.0, step=1.0)
DP_nom = st.sidebar.number_input("기준 차압 (kPa)", value=100.0, step=10.0)

# [수정] 센서 오차 입력항을 5개로 확장
st.sidebar.subheader("2. 센서 오차 한계 (Type B)")
err_C_rel = st.sidebar.number_input("유출계수 오차 (비율)", value=0.010, format="%.3f")
err_DP_abs = st.sidebar.number_input("차압 센서 오차 (kPa)", value=0.060, format="%.3f")
err_P_abs = st.sidebar.number_input("정압 센서 오차 (MPa)", value=0.004, format="%.4f") # 추가
err_RTD_abs = st.sidebar.number_input("RTD 센서 오차 (°C)", value=0.25, format="%.2f")
err_DAQ_abs = st.sidebar.number_input("DAQ 시스템 오차 (°C)", value=0.10, format="%.2f") # 추가

st.sidebar.markdown("---")

# ==========================================
# 메인 화면: 실행 버튼 및 결과(Output) 출력
# ==========================================
if 'mcs_completed' not in st.session_state:
    st.session_state['mcs_completed'] = False

if st.sidebar.button("MCS 시뮬레이션 실행"):
    with st.spinner('연산 중...'):
        # [수정] 백엔드로 넘길 딕셔너리에 5개 오차를 모두 포함
        user_params = {
            'P_nom': P_nom, 'T_in_nom': T_in_nom, 'T_out_nom': T_out_nom, 'DP_nom': DP_nom,
            'err_C_rel': err_C_rel, 
            'err_DP_abs': err_DP_abs, 
            'err_P_abs': err_P_abs,    # 백엔드 params.get('err_P_abs')와 매칭
            'err_RTD_abs': err_RTD_abs, 
            'err_DAQ_abs': err_DAQ_abs  # 백엔드 params.get('err_DAQ_abs')와 매칭
        }
        
        # 백엔드 엔진 호출
        stat_results, fig_specs, fig_synth, fig_final = calc_engine.run_mcs_hierarchical(params=user_params, N=1000000)
        
        # 세션 상태에 결과 저장
        st.session_state['stat_results'] = stat_results
        st.session_state['fig_specs'] = fig_specs
        st.session_state['fig_synth'] = fig_synth
        st.session_state['fig_final'] = fig_final
        st.session_state['mcs_completed'] = True
    st.success("✅ 연산 완료!")

# 2. 결과 계층적 출력
if st.session_state['mcs_completed']:
    stat_results = st.session_state['stat_results']
    
    # -------------------------------------------------------------------------
    # 계층 1: 기초 기기 사양 불확도
    # ⚠️ [수정 3] 5개의 독립 센서 오차를 나란히 출력하도록 수정 완료
    # -------------------------------------------------------------------------
    st.header("[계층 1] 개별 센서 표준불확도 ($1\sigma$, Type B)")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("유출계수 오차", f"± {stat_results['std_C']:.3f} %")
    c2.metric("차압 센서 오차", f"± {stat_results['std_DP']:.3f} kPa")
    c3.metric("정압 센서 오차", f"± {stat_results['std_P']:.4f} MPa")
    c4.metric("RTD 센서 오차", f"± {stat_results['std_RTD']:.3f} °C")
    c5.metric("DAQ 오차", f"± {stat_results['std_DAQ']:.3f} °C")
    
    st.markdown("##### [Figure 1] 기초 기기 오차 사양 난수 분포")
    st.pyplot(st.session_state['fig_specs'])
    
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 계층 2: 주요 변수 합성 불확도
    # -------------------------------------------------------------------------
    st.header("[계층 2] 주요 변수 합성 오차 분포 ($1\sigma$)")
    st.caption("개별 센서 오차들이 질량유량, 온도차, 비열 연산식에 전파되어 합성된 분포")

    c4, c5, c6 = st.columns(3)
    c4.metric("질량유량 ($\dot{m}$) 상대오차", f"± {stat_results['std_m_dot']:.3f} %")
    c5.metric("온도차 ($\Delta T$) 상대오차", f"± {stat_results['std_dT']:.3f} %")
    c6.metric("비열 ($c_p$) 상대오차", f"± {stat_results['std_cp']:.3f} %")
    
    st.markdown("##### [Figure 2] 주요 합성 변수들의 확률 오차 분포")
    st.pyplot(st.session_state['fig_synth'])
    
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 계층 3: 최종 합성 불확도 (Heat Duty)
    # -------------------------------------------------------------------------
    st.header("[계층 3] 최종 Heat Duty ($Q$) 확장불확도 (95%)")
    
    U_Q = stat_results['U_Q_95']
    st.success(f"### **최종 sCO2 열교환기 성능($Q$) 95% 확장 불확도 ($k=2$): ± {U_Q:.3f} %**")

    c7, c8 = st.columns([1, 2])
    with c8:
        st.markdown("##### [Figure 3] 최종 sCO2 Heat Duty 성능 확률 오차 분포 및 95% 신뢰구간")
        st.pyplot(st.session_state['fig_final'])
