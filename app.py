import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import re
from st_copy_to_clipboard import st_copy_to_clipboard

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

# 4. 모델 설정 (최신 3.1 Pro Preview 적용 및 출력 길이 최대화)
generation_config = {
    "temperature": 0.0,        # 창의성 0 (분석 모드)
    "top_p": 1.0,
    "max_output_tokens": 8192, # 출력 길이 최대화 (텍스트 잘림 방지)
}

# 🚀 요청하신 최신 모델로 변경 완료
model = genai.GenerativeModel(
    model_name='gemini-3.1-pro-preview',
    generation_config=generation_config,
    safety_settings=safety_settings 
)

# 5. 시스템 프롬프트 (QR코드 상세 가이드 및 전수 조사 강제)
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

SYSTEM_PROMPT_POST = """
[SYSTEM SETTING: RIGOROUS ANALYTICAL MODE]
당신은 'KWCAG 정보접근성 품질 관리관'입니다. 
목표: 업로드된 '게시글 내 삽입 이미지'의 성격을 먼저 분류하고, 그에 맞는 검사 및 결과 도출을 수행하는 것입니다.

**[작업 원칙: 이미지 성격 분류]**
가장 먼저 이 이미지가 다음 중 어느 것인지 면밀하게 판단하십시오.
- **[텍스트를 포함하는 이미지]**: 의도적으로 정보 전달을 위해 텍스트를 넣어 제작한 이미지 (예: 카드뉴스, 인포그래픽, 포스터 이미지 등)
- **[텍스트를 포함하지 않는 이미지]**: 일반적인 행사 사진, 풍경 사진, 인물 사진 등. (주의: 사진 배경에 우연히 찍힌 현수막이나 간판의 텍스트가 있다고 해서 '텍스트를 포함하는 이미지'로 분류해서는 안 됩니다.)

**[작업 원칙: 로고 제외 필수]**
- 상단 또는 하단에 위치한 기관 로고(예: 경기도평생교육진흥원 등)는 명도 대비 검사 대상에서 **반드시 제외**하십시오.
- 로고에 포함된 텍스트 역시 텍스트 추출(Full OCR) 대상에서 **제외**하십시오.

**[출력 포맷]**

### [텍스트를 포함하는 이미지] (또는 ### [텍스트를 포함하지 않는 이미지])

---

**(만약 [텍스트를 포함하는 이미지]로 분류된 경우, 아래 포맷으로 출력)**
**1단계: 명도 대비 판정**
- ✅ 적격 / ⚠️ 주의 / ❌ 부적격

**2단계: 상세 분석 (전수 조사 리스트)**
- 위반된 부분의 [위치/내용]과 [문제점]을 구체적으로 나열하십시오.
- 위반 사항이 없다면 "특이사항 없음"이라고 적으십시오.

**3단계: 텍스트 소스 (전체 추출)** `※ 복사 후 '이미지 설명' 입력란에 입력하세요.`
- 상하단 로고 제외, 본문 핵심 내용 전체를 추출. 표나 리스트가 있다면 구조를 유지할 것.
- 반드시 아래 코드 블록 안에 출력:
```text
(추출한 텍스트 전체 내용을 여기에 출력)
```

---

**(만약 [텍스트를 포함하지 않는 이미지]로 분류된 경우, 아래 포맷으로 출력)**
**1단계: 대체 텍스트 요약** `※ 복사 후 '이미지 설명' 입력란에 입력하세요.`
- 시각장애인이 이미지를 보지 않고도 맥락을 이해할 수 있도록, 사진의 핵심 내용이나 현장의 분위기, 주요 피사체의 행동 등을 요약하여 제공하십시오.
- 반드시 아래 코드 블록 안에 출력:
```text
(대체 텍스트 내용을 여기에 출력)
```
**(END OF OUTPUT)**
"""

# 6. UI 구성
st.title("🏛️ 경평원 정보접근성 검사기")
st.info("💡 최신 Gemini 3.1 Pro 기반 정밀 분석 모드가 적용되었습니다.")

# 세션 상태 초기화
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None

def create_summary_image(text, original_image):
    font_path = "NotoSansKR.otf"
    try:
        font_title = ImageFont.truetype(font_path, 24)
        font_body = ImageFont.truetype(font_path, 16)
        font_watermark = ImageFont.truetype(font_path, 12) # 폰트 크기 대폭 축소
    except IOError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_watermark = ImageFont.load_default()

    # 이모지 치환 (Pillow 렌더링 시 엑박/깨짐 방지)
    text = text.replace("✅", "[O]").replace("⚠️", "[!]").replace("❌", "[X]")
    text = text.replace("👉", "->").replace("ℹ️", "[안내]")

    # 1. 썸네일 생성 (크기 약간 확대)
    thumb_width = 350
    w_percent = (thumb_width / float(original_image.size[0]))
    h_size = int((float(original_image.size[1]) * float(w_percent)))
    thumb_img = original_image.resize((thumb_width, h_size), Image.Resampling.LANCZOS)

    # 2. 텍스트 줄바꿈 처리 (가로 길이를 넉넉하게 잡고, wrap 기준 수정)
    # 한글은 폭을 더 차지하므로 width를 보수적으로 설정
    wrap_width = 45 
    wrapped_lines = []
    for line in text.split('\n'):
        if line.strip() == "":
            wrapped_lines.append(("", False))
        elif line.startswith("**") and line.endswith("**"):
            wrapped_lines.append((line.replace("**", ""), True)) # 제목
        else:
            # 일반 텍스트의 마크다운 기호(* 등) 제거
            clean_line = line.replace("*", "").replace("#", "")
            for wrapped in textwrap.wrap(clean_line, width=wrap_width):
                wrapped_lines.append((wrapped, False))
            
    line_height = 28 # 줄간격 여유
    text_height = len(wrapped_lines) * line_height + 150
    
    # 3. 전체 이미지 크기 계산 (폭을 1200으로 넓혀 텍스트 잘림 방지)
    img_width = 1200
    img_height = max(text_height, h_size + 150)

    # 기본 배경 생성 (살짝 회색빛)
    img = Image.new('RGB', (img_width, img_height), color='#f4f6f8')
    d = ImageDraw.Draw(img)

    # 하얀색 카드 형태 (HTML/CSS 효과)
    card_margin = 30
    d.rounded_rectangle(
        [(card_margin, card_margin), (img_width - card_margin, img_height - card_margin)], 
        radius=15, 
        fill="white", 
        outline="#e0e0e0", 
        width=2
    )

    # 워터마크 패턴 (카드 위, 텍스트 아래에 촘촘하게 깔리도록 수정)
    watermark_text = " 경기도평생교육진흥원 정보접근성 검사기 - 팝업/대형배너 검사 결과 "
    watermark_color = (242, 242, 245) # 텍스트를 방해하지 않는 매우 연한 색상

    # 간격을 2배 더 촘촘하게 (y축 15, x축 350 간격)
    for y in range(card_margin, img_height - card_margin, 15):
        for x in range(card_margin - 200, img_width - card_margin, 350):
            # 지그재그 패턴으로 엇갈리게 배치
            offset = 175 if (y // 15) % 2 == 0 else 0
            d.text((x + offset, y), watermark_text, font=font_watermark, fill=watermark_color)

    # 제목
    d.text((card_margin + 40, card_margin + 40), "팝업 / 대형 배너 검사 결과", font=font_title, fill='#1e1e1e')
    d.line([(card_margin + 40, card_margin + 80), (img_width - card_margin - 40, card_margin + 80)], fill="#eeeeee", width=2)

    # 이미지 삽입
    img.paste(thumb_img, (card_margin + 40, card_margin + 110))

    # 텍스트 렌더링 영역 (이미지 우측)
    text_x = card_margin + 40 + thumb_width + 50
    y = card_margin + 110
    for line_text, is_bold in wrapped_lines:
        current_font = font_title if is_bold else font_body
        color = '#1e1e1e' if is_bold else '#333333'
        d.text((text_x, y), line_text, font=current_font, fill=color)
        y += (35 if is_bold else line_height)
        
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def render_inspection_ui(category):
    # 뒤로 가기 버튼
    if st.button("⬅️ 다른 유형 선택하기"):
        st.session_state.selected_category = None
        st.rerun()

    st.subheader(f"[{category}] 검사")
    
    # 카테고리별로 고유한 key를 부여하여 위젯 충돌 방지
    uploaded_file = st.file_uploader(f"이미지 업로드 ({category})", type=["jpg", "png", "jpeg"], key=f"uploader_{category}")

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='검수 대상 이미지', use_container_width=True)

        # 현재 업로드된 파일명으로 고유 식별자 생성
        file_id = f"{category}_{uploaded_file.name}"

        # 파일이 변경되면 이전 결과 초기화
        if 'current_file_id' not in st.session_state or st.session_state.current_file_id != file_id:
            st.session_state.current_file_id = file_id
            st.session_state.result_text = None
            st.session_state.summary_text = None
            st.session_state.img_bytes = None

        if st.button("🔍 점검 시작", type="primary", key=f"btn_{category}"):
            with st.spinner('최신 AI가 이미지를 정밀 분석 중입니다...'):
                try:
                    # 카테고리별 프롬프트 분기 처리
                    prompt_to_use = SYSTEM_PROMPT_POST if category == '게시글 내 삽입 이미지' else SYSTEM_PROMPT
                    response = model.generate_content([prompt_to_use, image])

                    st.success("점검 완료")

                    # 세션 상태에 결과 저장
                    st.session_state.result_text = response.text

                    result_text = response.text
                    summary_text = result_text.split("**3단계:")[0] if "**3단계:" in result_text else result_text
                    st.session_state.summary_text = summary_text

                    if category == '팝업 / 대형 배너':
                        st.session_state.img_bytes = create_summary_image(summary_text, image)

                except Exception as e:
                    st.error(f"오류 발생: {e}")
                    st.caption("일시적인 오류일 수 있습니다. 다시 시도해주세요.")

        # 세션에 결과가 있으면 화면에 렌더링
        if st.session_state.result_text is not None:
            if category == '팝업 / 대형 배너':
                st.markdown("### 📋 점검 결과")
                st.markdown(st.session_state.result_text)
                st.markdown("---")
                st.markdown("#### 📸 결과 캡처 이미지")
                st.info("아래 버튼을 눌러 검사 결과 이미지를 다운로드하세요.")
                st.download_button(
                    label="저장하기",
                    data=st.session_state.img_bytes,
                    file_name="inspection_result.png",
                    mime="image/png",
                    type="primary"
                )

            elif category == '썸네일':
                # 마크다운 기호 제거하여 화면에 보이는 텍스트(Plain Text) 형태로 변환
                plain_text = st.session_state.summary_text.replace("**", "").replace("### ", "").replace("## ", "").replace("> ", "")

                # 결과 헤더와 복사 버튼을 한 줄에 배치하여 직관성 향상
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown("### 📋 점검 결과")
                with col2:
                    st_copy_to_clipboard(
                        text=plain_text,
                        before_copy_label="📋 결과 복사",
                        after_copy_label="✅ 복사 완료!"
                    )

                # 중복 출력을 방지하고, 화면에 1~2단계 요약 결과만 한 번 표시
                st.markdown(st.session_state.summary_text)
                st.caption("ℹ️ 위 복사 버튼을 누르면 텍스트가 복사되어 바로 붙여넣기할 수 있습니다.")

            elif category == '게시글 내 삽입 이미지':
                st.markdown("### 📋 점검 결과")
                st.markdown(st.session_state.result_text)
# 메인 화면 라우팅
if st.session_state.selected_category is None:
    st.markdown("### 📌 검사할 콘텐츠 유형을 선택하세요")
    st.write("진행하고자 하는 정보접근성 검사 항목을 아래에서 선택해 주세요.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🖼️ 팝업 / 대형 배너", use_container_width=True):
            st.session_state.selected_category = '팝업 / 대형 배너'
            st.rerun()

    with col2:
        if st.button("📱 썸네일", use_container_width=True):
            st.session_state.selected_category = '썸네일'
            st.rerun()

    with col3:
        if st.button("📝 게시글 내 삽입 이미지", use_container_width=True):
            st.session_state.selected_category = '게시글 내 삽입 이미지'
            st.rerun()

else:
    render_inspection_ui(st.session_state.selected_category)
