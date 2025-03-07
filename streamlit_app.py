import streamlit as st
from openai import OpenAI
from datetime import datetime
import base64

def generate_newsletter(api_key):
    # OpenAI 클라이언트 초기화 (API 키 직접 전달)
    client = OpenAI(api_key=api_key)
    
    date = datetime.now().strftime('%Y년 %m월 %d일')
    issue_number = 1
    
    prompts = {
        'main_news': """
        AIDT Weekly 뉴스레터의 '주요 소식' 섹션을 생성해주세요.
        형식:
        [인사말]
        # 주요소식 1
        - 제목: [AI 관련 새로운 소식]
        - 내용: [구체적인 내용]
        - 효과: [도입 효과나 의의]
        """,
        'aidt_tips': """
        AIDT Weekly 뉴스레터의 'AI 활용 팁' 섹션을 생성해주세요.
        """,
        'success_story': """
        AIDT Weekly 뉴스레터의 '성공 사례' 섹션을 생성해주세요.
        """,
        'events': f"""
        AIDT Weekly 뉴스레터의 '다가오는 이벤트' 섹션을 생성해주세요.
        현재 날짜는 {date}입니다.
        """,
        'qa': """
        AIDT Weekly 뉴스레터의 'Q&A' 섹션을 생성해주세요.
        """
    }
    
    newsletter_content = {}
    
    for section, prompt in prompts.items():
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "AI 디지털 트랜스포메이션 뉴스레터 콘텐츠 생성 전문가"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            newsletter_content[section] = response.choices[0].message.content
        except Exception as e:
            newsletter_content[section] = f"콘텐츠 생성 오류: {e}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AIDT Weekly - 제{issue_number}호</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #3498db; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AIDT Weekly</h1>
            <p>제{issue_number}호 | {date}</p>
            <h2>🔔 주요 소식</h2>
            <div>{newsletter_content['main_news'].replace('\n', '<br>')}</div>
            <h2>💡 이번 주 AIDT 팁</h2>
            <div>{newsletter_content['aidt_tips'].replace('\n', '<br>')}</div>
            <h2>🏆 성공 사례</h2>
            <div>{newsletter_content['success_story'].replace('\n', '<br>')}</div>
            <h2>📅 다가오는 이벤트</h2>
            <div>{newsletter_content['events'].replace('\n', '<br>')}</div>
            <h2>❓ 질문 & 답변</h2>
            <div>{newsletter_content['qa'].replace('\n', '<br>')}</div>
        </div>
    </body>
    </html>
    """
    return html_content

def create_download_link(html_content, filename):
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">뉴스레터 다운로드</a>'
    return href

# Streamlit 앱 시작
st.title("AIDT 뉴스레터 생성기")

# API 키 입력
api_key = st.text_input("OpenAI API 키 입력", type="password")

# 뉴스레터 생성 버튼
if st.button("뉴스레터 생성"):
    if not api_key:
        st.error("API 키를 입력하세요.")
    else:
        with st.spinner("뉴스레터 생성 중... (약 1-2분 소요될 수 있습니다)"):
            try:
                html_content = generate_newsletter(api_key)
                filename = f"AIDT_Weekly_{datetime.now().strftime('%Y%m%d')}.html"
                st.success("뉴스레터가 성공적으로 생성되었습니다!")
                st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                
                # 미리보기 표시
                st.subheader("뉴스레터 미리보기")
                st.components.v1.html(html_content, height=500, scrolling=True)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")