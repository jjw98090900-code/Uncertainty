import numpy as np
import matplotlib.pyplot as plt

def run_mcs_hierarchical(params, N=1000000):
    """
    sCO2 열교환기 계층적 몬테카를로 불확도 평가 엔진 (N회 시뮬레이션)
    """
    # ==========================================
    # 1. 운전 조건 및 기준값 (Nominal Values)
    # ==========================================
    P_nom = params.get('P_nom', 8.0)              
    T_in_nom = params.get('T_in_nom', 60.0)          
    T_out_nom = params.get('T_out_nom', 40.0)         
    DP_nom = params.get('DP_nom', 100.0)           
    
    T_avg_nom = (T_in_nom + T_out_nom) / 2.0  
    dT_nom = T_in_nom - T_out_nom             
    cp_nom = 2.45                             # sCO2 cp (pseudo-critical region 가정)
    
    m_dot_nom = 1.0                           # kg/s
    Q_nom = m_dot_nom * cp_nom * dT_nom       # kW

    # ==========================================
    # 2. 센서 오차 범위 (Type B - Rectangular limits)
    # ==========================================
    err_C_rel   = params.get('err_C_rel', 0.01)          
    err_DP_abs  = params.get('err_DP_abs', 0.06)          
    err_RTD_abs = params.get('err_RTD_abs', 0.25)          
    # calc_engine.py 내부
    err_P_abs   = params.get('err_P_abs', 0.004)   # 이제 UI에서 보낸 값을 우선 사용합니다.
    err_DAQ_abs = params.get('err_DAQ_abs', 0.10)  # 이제 UI에서 보낸 값을 우선 사용합니다.
    
    # cp 민감도 계수 (Taylor Series Expansion)
    theta_T = -0.08 # dcp/dT
    theta_P = 0.25  # dcp/dP

    # ==========================================
    # 3. 기초 기기 오차 난수 생성 (Type B Uniform Distribution)
    # ==========================================
    C_rel_err_sampled   = np.random.uniform(-err_C_rel, err_C_rel, N) 
    DP_abs_err_sampled  = np.random.uniform(-err_DP_abs, err_DP_abs, N)
    P_abs_err_sampled   = np.random.uniform(-err_P_abs, err_P_abs, N)
    
    RTD_in_abs_err_sampled  = np.random.uniform(-err_RTD_abs, err_RTD_abs, N) 
    RTD_out_abs_err_sampled = np.random.uniform(-err_RTD_abs, err_RTD_abs, N)
    DAQ_in_abs_err_sampled  = np.random.uniform(-err_DAQ_abs, err_DAQ_abs, N)
    DAQ_out_abs_err_sampled = np.random.uniform(-err_DAQ_abs, err_DAQ_abs, N)

    # 시각화 공통 설정
    alpha_val = 0.7
    bins_count = 100

    # =========================================================================
    # [계층 1] 기초 기기 사양 분포 시각화 (fig_specs) - 5개 독립 요인
    # =========================================================================
    fig_specs, axs_specs = plt.subplots(2, 3, figsize=(18, 10))
    fig_specs.suptitle("Hierarchical Step 1: Fundamental Instrument Specs Distributions", fontsize=16, fontweight='bold')
    spec_color = 'dodgerblue'

    axs_specs[0, 0].hist(C_rel_err_sampled*100, bins=bins_count, color=spec_color, alpha=alpha_val, density=True) 
    axs_specs[0, 0].set_title("1. Discharge Coeff. Spec Error (%)", fontsize=12)
    axs_specs[0, 0].grid(True, alpha=0.3)

    axs_specs[0, 1].hist(DP_abs_err_sampled, bins=bins_count, color=spec_color, alpha=alpha_val, density=True)
    axs_specs[0, 1].set_title("2. DP Sensor Spec Error (kPa)", fontsize=12)
    axs_specs[0, 1].grid(True, alpha=0.3)

    axs_specs[0, 2].hist(P_abs_err_sampled, bins=bins_count, color=spec_color, alpha=alpha_val, density=True)
    axs_specs[0, 2].set_title("3. Static Pressure Spec Error (MPa)", fontsize=12)
    axs_specs[0, 2].grid(True, alpha=0.3)

    axs_specs[1, 0].hist(RTD_in_abs_err_sampled, bins=bins_count, color=spec_color, alpha=alpha_val, density=True)
    axs_specs[1, 0].set_title("4. RTD Spec Error (°C)", fontsize=12)
    axs_specs[1, 0].grid(True, alpha=0.3)

    axs_specs[1, 1].hist(DAQ_in_abs_err_sampled, bins=bins_count, color=spec_color, alpha=alpha_val, density=True)
    axs_specs[1, 1].set_title("5. DAQ Spec Error (°C)", fontsize=12)
    axs_specs[1, 1].grid(True, alpha=0.3)

    axs_specs[1, 2].axis('off') # 6번째 빈 칸 숨김 처리
    fig_specs.tight_layout(rect=[0, 0.03, 1, 0.97])

    # ==========================================
    # 4. MCS 계층적 오차 전파 (Propagated Errors)
    # ==========================================
    # A1. Mass Flow Rate (m_dot) 합성
    DP_dist = DP_nom + DP_abs_err_sampled  
    DP_dist = np.abs(DP_dist) # 차압 음수 방지 수치 안정화
    m_dot_dist = m_dot_nom * (1 + C_rel_err_sampled) * np.sqrt(DP_dist / DP_nom) 
    m_rel_err_dist = (m_dot_dist - m_dot_nom) / m_dot_nom * 100.0 
    
    # A2. Temp. Difference (ΔT) 합성
    T_in_dist  = T_in_nom + RTD_in_abs_err_sampled + DAQ_in_abs_err_sampled
    T_out_dist = T_out_nom + RTD_out_abs_err_sampled + DAQ_out_abs_err_sampled
    dT_dist    = T_in_dist - T_out_dist
    dT_rel_err_dist = (dT_dist - dT_nom) / dT_nom * 100.0
    
    # A3. Specific Heat (cp) 합성
    T_avg_dist = (T_in_dist + T_out_dist) / 2.0
    P_dist     = P_nom + P_abs_err_sampled
    cp_dist    = cp_nom + theta_T * (T_avg_dist - T_avg_nom) + theta_P * (P_dist - P_nom)
    cp_rel_err_dist = (cp_dist - cp_nom) / cp_nom * 100.0

    # B1. Final Heat Duty (Q) 합성
    Q_dist = m_dot_dist * cp_dist * dT_dist
    Q_rel_err_dist = (Q_dist - Q_nom) / Q_nom * 100.0
    
    # =========================================================================
    # [계층 2] 주요 변수 합성 오차 분포 시각화 (fig_synth)
    # =========================================================================
    fig_synth, axs_synth = plt.subplots(1, 3, figsize=(18, 5))
    fig_synth.suptitle("Hierarchical Step 2: Propagated Intermediary Sub-Models Distributions", fontsize=16, fontweight='bold')
    comp_color = 'darkorange'

    axs_synth[0].hist(m_rel_err_dist, bins=bins_count, color=comp_color, alpha=alpha_val, density=True)
    axs_synth[0].set_title(f"2-1. Mass Flow Rate ($\dot{{m}}$) Rel. Error (%)\nStd Dev: {np.std(m_rel_err_dist):.3f}%", fontsize=12)
    axs_synth[0].grid(True, alpha=0.3)

    axs_synth[1].hist(dT_rel_err_dist, bins=bins_count, color=comp_color, alpha=alpha_val, density=True)
    axs_synth[1].set_title(f"2-2. Temp. Difference ($\Delta T$) Rel. Error (%)\nStd Dev: {np.std(dT_rel_err_dist):.3f}%", fontsize=12)
    axs_synth[1].grid(True, alpha=0.3)

    axs_synth[2].hist(cp_rel_err_dist, bins=bins_count, color=comp_color, alpha=alpha_val, density=True)
    axs_synth[2].set_title(f"2-3. Specific Heat ($c_p$) Rel. Error (%)\nStd Dev: {np.std(cp_rel_err_dist):.3f}%", fontsize=12)
    axs_synth[2].grid(True, alpha=0.3)

    fig_synth.tight_layout(rect=[0, 0.03, 1, 0.97])

    # =========================================================================
    # [계층 3] 최종 Heat Duty 불확도 시각화 (fig_final)
    # =========================================================================
    fig_final, ax_final = plt.subplots(1, 1, figsize=(10, 6))
    fig_final.suptitle("Hierarchical Step 3: Final Heat Duty (Q) Expanded Uncertainty", fontsize=16, fontweight='bold')
    
    ax_final.hist(Q_rel_err_dist, bins=bins_count, color='crimson', alpha=0.8, density=True)
    
    # 통계 계산
    ci_lower = np.percentile(Q_rel_err_dist, 2.5)
    ci_upper = np.percentile(Q_rel_err_dist, 97.5)
    U_rel_95 = (ci_upper - ci_lower) / 2.0
    
    # 시각화 처리
    ax_final.axvline(x=ci_lower, color='black', linestyle='--', linewidth=2, label=f'95% CI Lower ({ci_lower:.3f}%)')
    ax_final.axvline(x=ci_upper, color='black', linestyle='--', linewidth=2, label=f'95% CI Upper ({ci_upper:.3f}%)')
    ax_final.set_title(f"Final: Heat Duty (Q) Rel. Error (%)\nExpanded Uncertainty (k=2): ±{U_rel_95:.3f}%", fontsize=12)
    ax_final.legend()
    ax_final.grid(True, alpha=0.3)

    fig_final.tight_layout(rect=[0, 0.03, 1, 0.97])

    # ==========================================
    # 5. 통계 데이터 추출 및 최종 반환 (Return)
    # ==========================================
    stat_results = {
        # 1. 5개의 독립된 기초 센서 표준불확도 (1σ)
        'std_C': np.std(C_rel_err_sampled) * 100.0,
        'std_DP': np.std(DP_abs_err_sampled),      
        'std_P': np.std(P_abs_err_sampled),        
        'std_RTD': np.std(RTD_in_abs_err_sampled), 
        'std_DAQ': np.std(DAQ_in_abs_err_sampled), 
        
        # 2. 중간 합성 변수 상대불확도 (1σ)
        'std_m_dot': np.std(m_rel_err_dist), 
        'std_dT': np.std(dT_rel_err_dist),   
        'std_cp': np.std(cp_rel_err_dist),   
        
        # 3. 최종 확장불확도 (k=2, 95%)
        'U_Q_95': U_rel_95                   
    }

    return stat_results, fig_specs, fig_synth, fig_final