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

# 3. 모델 설정 (Flash 모델의 게으름 방지 세팅)
# temperature=0 : 창의성을 0으로 낮춰서 사실 기반 분석력 극대화
generation_config = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_output_tokens": 4096,
}

# 모델 선택 (1.5 Flash가 가성비/속도 최적. 필요시 'gemini-1.5-pro-001'로 변경)
model = genai.GenerativeModel(
    model_name='models/gemini-2.5-flash', 
    generation_config=generation_config
)

# 4. 시스템 프롬프트 (Lazy 현상 방지 + 전수 조사 강제)
SYSTEM_PROMPT = """
[SYSTEM SETTING: ANALYTICAL MODE]
당신은 엄격한 'KWCAG 정보접근성 품질 관리관'입니다. 
당신의 목표는 이미지 내의 '모든' 텍스트를 전수 조사하여 명도 대비 위반 사항을 단 하나도 빠짐없이 찾아내는 것입니다.

**[분석 알고리즘 - 반드시 이 순서대로 사고할 것]**
1. **공간 스캔:** 이미지를 상단, 중단, 하단, 좌우로 나누어 시선을 이동하며 모든 텍스트 덩어리를 찾으십시오.
2. **개별 검증:** 찾은 모든 텍스트 덩어리에 대해 각각 배경색과 글자색의 명도 대비(4.5:1)를 확인하십시오.
3. **위반 누적:** 위반 사항이 발견되면 즉시 멈추지 말고 리스트에 계속 추가하십시오. (절대 하나만 찾고 끝내지 마십시오.)
4. **최종 출력:** 누적된 모든 위반 사항을 보고하십시오.

**[절대 금지 사항]**
- "대표적인 예시로..."라며 하나만 지적하고 끝내기 금지.
- 질문, 잡담, 서론, 맺음말 절대 금지.
- 무조건 한국어로 출력.

**[수행 프로세스 및 출력 형식]**

**1단계: 명도 대비 및 가독성 평가**
- 판정: ✅ 적격 / ⚠️ 주의 / ❌ 부적격 (하나라도 위반 시 부적격)

**2단계: 상세 분석 (전수 조사 결과)**
- (형식: [위치/텍스트] 문제점 설명 -> 개선 권장)
- 위반 사항이 여러 개면 번호를 매겨 모두 나열할 것.
- QR코드가 있다면: "ℹ️ QR코드 경고: 본문에 URL 텍스트 병기 필수" 출력.
- 특이사항 없으면 "특이사항 없음" 출력.

**3단계: 텍스트 소스 (OCR)**
- 상하단 로고/기관명 제외. 본문 핵심 내용만 추출.
- 반드시 아래와 같이 코드 블록을 생성하여 출력:
```text
(여기에 추출한 텍스트 내용)
```
**(END OF OUTPUT)**
"""

# 5. UI 구성
st.title("🏛️ 경평원 정보접근성 검사기 (Pro)")
st.info("💡 AI가 이미지 전체를 꼼꼼하게 스캔하여 '모든' 위반 사항을 찾아냅니다.")

uploaded_file = st.file_uploader("이미지 업로드 (JPG, PNG)", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='검수 대상 이미지', use_container_width=True)
    
    if st.button("🔍 정밀 진단 시작", type="primary"):
        with st.spinner('AI가 픽셀 단위로 전수 조사 중입니다...'):
            try:
                response = model.generate_content([SYSTEM_PROMPT, image])
                st.success("분석 완료")
                st.markdown("### 📋 진단 결과")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"오류 발생: {e}")
