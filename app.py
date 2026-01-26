import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 페이지 설정
st.set_page_config(
    page_title="경평원 정보접근성 검사기",
    page_icon="favicon.ico", 
    layout="centered"
)

# 2. API 설정
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    st.error("API Key가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 안전 설정 (필수: 텍스트 추출 중단 방지를 위해 모든 필터 해제)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# 4. 모델 설정 (Flash 모델 최적화)
generation_config = {
    "temperature": 0.0,        # 창의성 0 (분석 모드)
    "top_p": 1.0,
    "max_output_tokens": 8192, # 출력 길이 최대화 (텍스트 잘림 방지)
}

# 모델 초기화 (안정적인 1.5 Flash 사용)
model = genai.GenerativeModel(
    model_name='models/gemini-2.5-flash',
    generation_config=generation_config,
    safety_settings=safety_settings 
)

# 5. 시스템 프롬프트 (QR코드 상세 가이드 강화)
SYSTEM_PROMPT = """
[SYSTEM SETTING: RIGOROUS ANALYTICAL MODE]
당신은 'KWCAG 정보접근성 품질 관리관'입니다. 
목표: 이미지 내 텍스트를 **끝까지 완전하게 추출(Full OCR)**하고, 명도 대비 위반 및 QR코드 접근성을 **전수 조사**하는 것입니다.

**[작업 원칙]**
1. **Full OCR:** 이미지의 텍스트가 아무리 길어도 중간에 자르지 말고 끝까지 출력하십시오.
2. **전수 조사:** 명도 대비 위반 사항을 발견하면 즉시 멈추지 말고, 이미지 끝까지 스캔하여 모든 위반 사항을 나열하십시오.
3. **QR코드 필수 체크:** QR코드는 시각장애인에게 치명적인 장벽임을 인지하고 상세히 안내하십시오.

**[출력 포맷]**

**1단계: 명도 대비 판정**
- ✅ 적격 / ⚠️ 주의 / ❌ 부적격

**2단계: 상세 분석 (전수 조사 리스트)**
- 위반된 부분의 [위치/내용]과 [문제점]을 구체적으로 나열하십시오.
- 위반 사항이 없다면 "특이사항 없음"이라고 적으십시오.

**★ QR코드 발견 시 출력 양식 (매우 중요)**
만약 이미지에 QR코드가 있다면, 반드시 아래 형식을 그대로 사용하여 출력하십시오:
> **[QR코드]** (위치: 예-우측 상단)에 QR코드가 (개수)개 포함되어 있습니다.
> 👉 "ℹ️ **추가 조언:** 시각장애인은 이미지 속 QR코드를 스캔할 수 없으므로, 게시물 본문에 해당 페이지로 연결되는 실제 URL 링크를 텍스트로 기재해야 합니다."

**3단계: 텍스트 소스 (전체 추출)**
- 상하단 로고 제외, 본문 핵심 내용 전체.
- 표나 리스트가 있다면 구조를 유지할 것.
- 반드시 아래 코드 블록 안에 출력:
```text
(추출한 텍스트 전체 내용을 여기에 출력)
```
**(END OF OUTPUT)**
"""

# 6. UI 구성
st.title("🏛️ 경평원 정보접근성 검사기")
st.info("💡 텍스트 전수 조사 & QR코드 상세 가이드 모드 적용됨")

uploaded_file = st.file_uploader("이미지 업로드 (JPG, PNG)", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='검수 대상 이미지', use_container_width=True)
    
    if st.button("🔍 진단 시작", type="primary"):
        with st.spinner('AI가 이미지를 정밀 분석 중입니다...'):
            try:
                response = model.generate_content([SYSTEM_PROMPT, image])
                
                st.success("분석 완료")
                st.markdown("### 📋 진단 결과")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"오류 발생: {e}")
                st.caption("일시적인 오류일 수 있습니다. 다시 시도해주세요.")
