import streamlit as st
import openai
import os
from fpdf import FPDF

# --- CSS for styling ---
st.markdown('''
    <style>
    .quiz-btn {
        background-color: #ff9800 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.7em 2em;
        font-size: 1.2em;
        position: sticky;
        top: 0;
        z-index: 100;
        margin-bottom: 1em;
    }
    .quiz-card {
        background: #fffbe7;
        border-radius: 12px;
        box-shadow: 0 2px 8px #0001;
        padding: 1.2em 1em 1em 1em;
        margin-bottom: 1.5em;
        border: 1.5px solid #ffe0b2;
    }
    .wrong-check {
        color: #e53935;
        font-weight: bold;
        margin-left: 0.5em;
    }
    @media (max-width: 600px) {
        .quiz-card { padding: 0.7em 0.3em; font-size: 1em; }
        .quiz-btn { font-size: 1em; padding: 0.5em 1em; }
    }
    </style>
''', unsafe_allow_html=True)

# OpenAI API 키 설정 (환경변수 사용 권장)
# 환경변수에서 읽어오거나, 직접 입력(노출 주의)
import os
from dotenv import load_dotenv

load_dotenv()

# --- OpenAI API KEY ---
openai.api_key = os.getenv("OPENAI_API_KEY")
  
st.title('GPT-4o 기반 자동 퀴즈 생성기')

# 교재 내용 입력
text_input = st.text_area('교재 내용을 입력하세요', height=200)

# 이미지 업로드 기능 추가
uploaded_image = st.file_uploader('이미지(예: 교재 사진 등)를 첨부할 수 있습니다.', type=['png', 'jpg', 'jpeg'])
if uploaded_image:
    st.image(uploaded_image, caption='업로드한 이미지', use_column_width=True)

# 오답노트 세션 상태 초기화
if 'wrong_notes' not in st.session_state:
    st.session_state['wrong_notes'] = []
if 'quizzes' not in st.session_state:
    st.session_state['quizzes'] = []
if 'user_answers' not in st.session_state:
    st.session_state['user_answers'] = []
if 'checked' not in st.session_state:
    st.session_state['checked'] = []
if 'wrong_only_mode' not in st.session_state:
    st.session_state['wrong_only_mode'] = False

# 퀴즈 생성 함수
def generate_quiz(text):
    prompt = f"""
    아래 교재 내용을 바탕으로 객관식 2문제, 주관식 2문제를 각각 생성해줘.
    각 문제는 다음 형식으로 반환해줘:
    [문제유형: 객관식/주관식]
    문제:
    선택지(객관식만):
    정답:
    해설:
    
    교재 내용:
    {text}
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7
    )
    return response.choices[0].message.content

# 퀴즈 파싱 함수
def parse_quiz(raw):
    quizzes = []
    blocks = raw.strip().split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        quiz = {'type': '', 'question': '', 'choices': [], 'answer': '', 'explanation': ''}
        for line in lines:
            if line.startswith('[문제유형:'):
                quiz['type'] = line.replace('[문제유형:', '').replace(']', '').strip()
            elif line.startswith('문제:'):
                quiz['question'] = line.replace('문제:', '').strip()
            elif line.startswith('선택지:'):
                quiz['choices'] = [c.strip() for c in line.replace('선택지:', '').split(';') if c.strip()]
            elif line.startswith('정답:'):
                quiz['answer'] = line.replace('정답:', '').strip()
            elif line.startswith('해설:'):
                quiz['explanation'] = line.replace('해설:', '').strip()
        if quiz['question']:
            quizzes.append(quiz)
    return quizzes

# 퀴즈 생성 버튼 (스타일 적용)
quiz_btn = st.button('퀴즈 생성', key='quiz_btn', help='GPT-4o로 퀴즈 자동 생성', use_container_width=True)
if quiz_btn and text_input.strip():
    with st.spinner('GPT-4o가 퀴즈를 생성 중입니다...'):
        try:
            raw = generate_quiz(text_input)
            quizzes = parse_quiz(raw)
            st.session_state['quizzes'] = quizzes
            st.session_state['user_answers'] = [''] * len(quizzes)
            st.session_state['checked'] = [False] * len(quizzes)
            st.session_state['wrong_notes'] = []
            st.session_state['wrong_only_mode'] = False
        except Exception as e:
            st.error(f'퀴즈 생성 실패: {e}')

# 오답만 다시 풀기 버튼
if st.session_state['wrong_notes'] and not st.session_state['wrong_only_mode']:
    if st.button('오답만 다시 풀기', key='retry_wrong', use_container_width=True):
        st.session_state['quizzes'] = st.session_state['wrong_notes']
        st.session_state['user_answers'] = [''] * len(st.session_state['wrong_notes'])
        st.session_state['checked'] = [False] * len(st.session_state['wrong_notes'])
        st.session_state['wrong_only_mode'] = True
        st.experimental_rerun()

# 퀴즈 카드 표시 및 오답 체크
if st.session_state['quizzes']:
    st.subheader('생성된 퀴즈')
    for idx, quiz in enumerate(st.session_state['quizzes']):
        with st.container():
            st.markdown(f'<div class="quiz-card">', unsafe_allow_html=True)
            st.markdown(f"**Q{idx+1}. {quiz['question']}**")
            user = None
            if quiz['type'] == '객관식' and quiz['choices']:
                user = st.radio('선택지', quiz['choices'], key=f'choice_{idx}')
            else:
                user = st.text_input('정답 입력', key=f'input_{idx}')
            check_btn = st.button('정답 확인', key=f'check_{idx}', use_container_width=True)
            if check_btn:
                st.session_state['checked'][idx] = True
                st.session_state['user_answers'][idx] = user
                # 오답 체크
                if user.strip() == quiz['answer'].strip():
                    st.success('정답입니다!')
                else:
                    st.error('오답입니다.')
                    st.markdown('<span class="wrong-check">오답 체크됨</span>', unsafe_allow_html=True)
                    note = {
                        'question': quiz['question'],
                        'answer': quiz['answer'],
                        'explanation': quiz['explanation']
                    }
                    if note not in st.session_state['wrong_notes']:
                        st.session_state['wrong_notes'].append(note)
            if st.session_state['checked'][idx]:
                st.info(f"정답: {quiz['answer']}")
                st.caption(f"해설: {quiz['explanation']}")
            st.markdown('</div>', unsafe_allow_html=True)

# 오답노트 출력 및 PDF 다운로드
def save_pdf(notes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, '오답노트', ln=1, align='C')
    for i, note in enumerate(notes, 1):
        pdf.multi_cell(0, 10, f"Q{i}. {note['question']}\n정답: {note['answer']}\n해설: {note['explanation']}\n", border=1)
    return pdf.output(dest='S').encode('latin1')

if st.session_state['wrong_notes']:
    st.subheader('오답노트')
    for i, note in enumerate(st.session_state['wrong_notes'], 1):
        st.markdown(f"**Q{i}. {note['question']}**")
        st.markdown(f"- 정답: {note['answer']}")
        st.markdown(f"- 해설: {note['explanation']}")
    pdf_bytes = save_pdf(st.session_state['wrong_notes'])
    st.download_button('오답노트 PDF 다운로드', data=pdf_bytes, file_name='오답노트.pdf', mime='application/pdf')
