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

# 3. 안전 설정 (중요: 출력이 중간에 멈추는 것을 방지하기 위해 필터 해제)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# 4. 모델 설정 (토큰 최대치 8192로 확장)
generation_config = {
    "temperature": 0.0,        # 창의성 0 (분석 모드)
    "top_p": 1.0,
    "max_output_tokens": 8192, # <--- 여기가 핵심입니다. 텍스트가 잘리지 않게 최대치로 설정.
}

# 5. 시스템 프롬프트 (OCR 누락 방지 + 구역별 스캔 강제)
SYSTEM_PROMPT = """
[SYSTEM SETTING: RIGOROUS INSPECTION MODE]
당신은 'KWCAG 정보접근성 품질 관리관'입니다. 
당신의 목표는 이미지 내의 텍스트를 **완전히 끝까지 읽어내고(Full OCR)**, 명도 대비 위반 사항을 **하나도 빠짐없이 전수 조사**하는 것입니다.

**[OCR 추출 절대 원칙]**
1. 요약하지 마십시오. 이미지에 있는 모든 글자를 있는 그대로 가져오십시오.
2. 중간에 멈추지 마십시오. 글자가 1000자가 넘어도 끝까지 출력하십시오.
3. 표나 리스트가 있다면 그 구조를 유지하며 텍스트를 추출하십시오.

**[명도 대비 분석 알고리즘]**
1. **격자 스캔:** 이미지를 3x3 격자로 나누었다고 상상하고, 왼쪽 상단부터 오른쪽 하단까지 순서대로 훑으십시오.
2. **크기 무관:** 제목처럼 큰 글씨라고 해서 명도 대비가 확실할 것이라 단정 짓지 말고 무조건 검사하십시오.
3. **전수 기록:** 문제가 발견되면 즉시 출력 리스트에 넣으십시오. (대표 사례 1개만 적는 것 금지)

**[수행 프로세스 및 출력 형식]**

**1단계: 명도 대비 및 가독성 평가**
- 판정: ✅ 적격 / ⚠️ 주의 / ❌ 부적격 (하나라도 위반 시 부적격)

**2단계: 상세 분석 (전수 조사 결과)**
- (형식: [위치/텍스트] 문제점 설명 -> 개선 권장)
- 예시:
  1. [상단 타이틀] 노란 배경/흰 글씨 (명도비 1.2:1) -> 검정 테두리 필요
  2. [우측 하단 전화번호] 연회색 글씨 -> 진한 회색으로 변경 필요
- QR코드가 있다면: "ℹ️ QR코드 경고: 본문에 URL 텍스트 병기 필수" 출력.
- 특이사항 없으면 "특이사항 없음" 출력.

**3단계: 텍스트 소스 (Full OCR)**
- 상하단 로고/기관명 제외. 본문 내용을 **끝까지** 추출.
- 반드시 아래 코드 블록 안에 출력:
```text
(여기에 추출한 텍스트 내용. 중간에 끊지 말 것.)
```
**(END OF OUTPUT)**
"""

# 6. UI 구성
st.title("🏛️ 경평원 정보접근성 검사기 (Pro)")
st.info("💡 이미지의 모든 텍스트를 끝까지 읽고 정밀 분석합니다.")

# 사이드바 혹은 메인에 옵션 추가
use_pro_model = st.checkbox("🚀 고성능 모드 사용 (속도는 느리지만 더 꼼꼼함)")

uploaded_file = st.file_uploader("이미지 업로드 (JPG, PNG)", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='검수 대상 이미지', use_container_width=True)
    
    # 모델 선택 로직
    if use_pro_model:
        # Pro 모델 (무료 티어 사용 시 쿼터 제한 주의)
        # 1.5 Pro가 쿼터에 걸린다면 2.0 Flash를 대안으로 사용 고려
        target_model = 'gemini-1.5-pro' 
        btn_label = "🔍 고성능 정밀 진단 시작 (Pro)"
    else:
        # Flash 모델 (기본)
        target_model = 'models/gemini-2.5-flash'
        btn_label = "🔍 접근성 진단 시작 (Flash)"

    if st.button(btn_label, type="primary"):
        with st.spinner(f'{target_model} 모델이 이미지를 픽셀 단위로 분석 중입니다...'):
            try:
                # 모델 초기화 (버튼 누를 때 선택된 모델로 로드)
                model = genai.GenerativeModel(
                    model_name=target_model,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                response = model.generate_content([SYSTEM_PROMPT, image])
                
                st.success("분석 완료")
                st.markdown("### 📋 진단 결과")
                st.markdown(response.text)
                
            except Exception as e:
                # 에러 처리 강화
                if "429" in str(e):
                    st.error("🚨 사용량 초과(Quota Exceeded)입니다. 잠시 후 다시 시도하거나 '고성능 모드'를 끄고 시도해주세요.")
                else:
                    st.error(f"오류 발생: {e}")
