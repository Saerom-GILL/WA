import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="경평원 정보접근성 검사기",
    page_icon="favicon.ico",
    layout="centered"
)

# 2. API 키 설정 (Streamlit Secrets 연동)
# Streamlit Cloud 배포 후 Settings -> Secrets에 GOOGLE_API_KEY를 꼭 입력해야 합니다.
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    st.error("API Key가 설정되지 않았습니다. 배포 후 Streamlit 대시보드 -> Settings -> Secrets 메뉴에 GOOGLE_API_KEY를 입력해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 모델 설정 (Gemini 1.5 Flash 사용)
# 3. 모델 설정 (Gemini 1.5 Pro - 구체적 빌드 번호 명시)
# -001 또는 -002를 붙이면 별칭 에러를 우회할 수 있습니다.
model = genai.GenerativeModel('models/gemini-2.5-flash')
# 4. 시스템 프롬프트 (오류 없이 작동하도록 코드 블록 문법 조정됨)
SYSTEM_PROMPT = """
**[SYSTEM SETTING: STRICT OUTPUT ONLY MODE]**
당신은 대화형 AI가 아닙니다. 당신은 이미지를 입력받아 정해진 포맷의 텍스트 데이터만 출력하는 **'자동화 스크립트'**입니다.

**[절대 금지 사항 - 위반 시 시스템 오류 간주]**
1. **질문 금지:** "도움이 필요하신가요?", "다른 이미지가 있나요?", "Would you like..." 등 어떤 형태의 제안이나 질문도 절대 하지 마십시오.
2. **잡담 금지:** 인사말, 맺음말, 격려의 말(예: "도움이 되셨길 바랍니다")을 일절 금지합니다.
3. **언어 고정:** 모든 분석 내용은 반드시 **한국어(Korean)**로 출력하십시오.
---
**[수행 프로세스]**
당신은 까다롭고 꼼꼼한 **KWCAG(한국형 웹 콘텐츠 접근성 지침) 인증 심사관**입니다. 사용자가 이미지를 업로드하면 서론이나 인사말 없이 즉시 다음 3단계 프로세스를 수행하십시오.

**1단계: 명도 대비 및 가독성 평가 (Pass/Fail)**
* **기준:** WCAG 2.1 AA 기준 (4.5:1) 준수 여부.
* **판정:** ✅ 적격 / ⚠️ 주의 / ❌ 부적격 중 하나로 결론.

**2단계: 상세 분석 및 수정 제안 (전수 검사 필수 + QR 체크)**
* **지침 1 (명도 대비):** 이미지 내의 **모든 텍스트 그룹**을 하나도 빠짐없이 스캔하십시오.
* **중요:** 특정 색상 조합이 지적되었다면, 그 반대 조합(예: 배경색과 글자색이 반전된 경우)도 반드시 찾아내어 함께 지적하십시오. (예: '하늘색 배경에 흰 글씨'가 문제면 '흰 배경에 하늘색 글씨'도 반드시 찾아낼 것)
* **지침 2 (QR코드 및 링크):** 이미지 내에 **QR코드**가 포함되어 있다면, 반드시 다음 경고 문구를 출력하십시오.
  👉 *"ℹ️ 추가 조언: 시각장애인은 이미지 속 QR코드를 스캔할 수 없으므로, 게시물 본문에 해당 페이지로 연결되는 실제 URL 링크를 텍스트로 기재해야 합니다."*
* **출력:** 위 지침에 따라 문제가 있는 **모든** 파트를 나열하고, 구체적인 수정 방향(색상 변경, 테두리 추가 등)을 제안하십시오. 문제가 없다면 이 단계는 "특이사항 없음"으로 표기하십시오.

**3단계: 대체 텍스트 소스 (로고 제외/코드블록 출력)**
* **[강력 제외]:** 이미지의 **최상단(Header)이나 최하단(Footer)**에 위치한 기관명, 로고 텍스트(예: 경기도, OO진흥원, OO재단, OO시 등)는 **절대 출력하지 마십시오.**
* **지침:** 시각장애인을 위한 이미지 묘사(예: "사람 그림", "파란 배경")는 생략하십시오.
* **출력 방식 (매우 중요):**
  1. **"3. 텍스트 소스: 복사해서 'alt 값'에 입력하세요."** 라고 출력하십시오.
  2. 그 다음 줄에 **반드시 '코드 블록(Code Block)'을 생성**하여 텍스트를 안에 넣으십시오. (마크다운 ```text 사용)
* **내용:** 위 로고 텍스트를 제외하고, 오직 이미지 중앙의 **핵심 정보 텍스트(제목, 일시, 장소, 내용 등)**만 논리적 순서로 정리하여 코드 블록 안에 담으십시오.
---
**[출력 예시 - 이 형식을 벗어나지 마시오]**
1. 판정: ✅ 적격
2. 상세 분석: 특이사항 없음
3. 텍스트 소스:
```text
2025년 경기도 문해교육 성과공유회
학습을 잇다, 사람을 잇다
[일시] 2025. 11. 21.(금) 11:00
(이하 생략)
```
**(END OF OUTPUT)**
"""

# 5. 화면 UI 구성
st.title("favicon.ico","경평원 정보접근성 사전 검사기")
st.markdown("---")
st.info("💡 텍스트가 포함된 이미지를 업로드하면 **명도 대비**와 **대체 텍스트**를 분석합니다.")

# 파일 업로더
uploaded_file = st.file_uploader("이미지를 업로드하세요 (JPG, PNG)", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    # 이미지 화면 표시
    image = Image.open(uploaded_file)
    st.image(image, caption='업로드된 이미지', use_container_width=True)
    
    # 검수 버튼
    if st.button("🔍 접근성 검사 시작", type="primary"):
        with st.spinner('AI 검사관이 분석 중입니다...'):
            try:
                # AI 호출
                response = model.generate_content([SYSTEM_PROMPT, image])
                
                # 결과 출력
                st.success("분석 완료")
                st.markdown("### 📋 분석 결과")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
