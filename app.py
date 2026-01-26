import streamlit as st
import google.generativeai as genai

# API 키 설정
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"API 키 설정 오류: {e}")
    st.stop()

st.title("🛠️ 사용 가능한 모델 리스트 조회")

if st.button("모델 목록 불러오기"):
    try:
        st.write("조회 중...")
        # 사용 가능한 모든 모델 리스트를 가져옵니다
        models = genai.list_models()
        
        found_pro = False
        st.markdown("### 📋 내 API 키로 쓸 수 있는 모델들:")
        
        for m in models:
            # 모델 이름과 지원하는 기능을 출력
            if 'generateContent' in m.supported_generation_methods:
                st.code(m.name) # 예: models/gemini-1.5-pro
                if "1.5-pro" in m.name:
                    found_pro = True
        
        if found_pro:
            st.success("✅ 1.5 Pro 모델이 목록에 있습니다! 위 이름을 복사해서 쓰세요.")
        else:
            st.error("❌ 목록에 1.5 Pro가 안 보입니다. API 키가 Flash 전용이거나 라이브러리 문제입니다.")
            
    except Exception as e:
        st.error(f"에러 발생: {e}")
