import streamlit as st
from openai import OpenAI
from datetime import datetime
import time
import base64
import os
import re

# components 모듈을 명시적으로 임포트
try:
    import streamlit.components.v1 as components
except ImportError:
    st.error("streamlit.components.v1 모듈을 임포트할 수 없습니다. Streamlit을 최신 버전으로 업데이트해 보세요.")

def convert_markdown_to_html(text):
    """마크다운 텍스트를 HTML로 변환합니다."""
    # 제목 변환 (# 제목)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    
    # 굵은 텍스트 (**텍스트**)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # 기울임 텍스트 (*텍스트*)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # 글머리 기호 (- 항목)
    text = re.sub(r'^\- (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # 줄바꿈을 <br>과 <p>로 변환
    paragraphs = text.split('\n\n')
    for i, paragraph in enumerate(paragraphs):
        if not paragraph.startswith('<h') and not paragraph.startswith('<li'):
            # 이미 HTML 태그가 아닌 경우만 <p> 태그로 감싸기
            if '<li>' in paragraph:
                # 리스트 항목이 있는 경우 <ul> 태그로 감싸기
                paragraph = f'<ul>{paragraph}</ul>'
            else:
                paragraph = f'<p>{paragraph}</p>'
        paragraphs[i] = paragraph.replace('\n', '<br>')
    
    return ''.join(paragraphs)

def get_preview_html():
    """미리보기 HTML을 생성합니다."""
    date = datetime.now().strftime('%Y년 %m월 %d일')
    issue_number = 1
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AIDT Weekly - 미리보기</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .container {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            .preview-badge {{
                background-color: #ff7f50;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 14px;
                margin-left: 10px;
                vertical-align: middle;
            }}
            header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            h1 {{
                color: #2c3e50;
                font-size: 28px;
                margin-bottom: 10px;
            }}
            .issue-date {{
                color: #7f8c8d;
                font-size: 16px;
                margin-bottom: 20px;
            }}
            section {{
                margin-bottom: 40px;
            }}
            h2 {{
                color: #3498db;
                font-size: 22px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
                margin-top: 30px;
            }}
            p {{
                margin-bottom: 15px;
            }}
            ul {{
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 10px;
            }}
            strong {{
                color: #2c3e50;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #7f8c8d;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>AIDT Weekly <span class="preview-badge">미리보기</span></h1>
                <div class="issue-date">제{issue_number}호 | {date}</div>
            </header>
            
            <section>
                <h2>🔔 주요 소식</h2>
                <h2>주요소식 1</h2>
                <ul>
                <li>제목: OpenAI, GPT-5 개발 계획 발표</li>
                <li>내용: OpenAI가 차세대 모델인 GPT-5의 개발 계획을 공개했습니다.</li>
                <li>효과: 기업들은 더 정확하고 맥락을 이해하는 AI 솔루션을 도입할 수 있게 될 것입니다.</li>
                </ul>
            </section>
            
            <section>
                <h2>💡 이번 주 AIDT 팁</h2>
                <h2>이번 주 팁: 프롬프트 엔지니어링 마스터하기</h2>
                <p>AI 모델에서 최상의 결과를 얻기 위한 프롬프트 작성법을 알아봅니다.</p>
            </section>
            
            <section>
                <h2>🏆 성공 사례</h2>
                <h2>현대자동차의 AI 활용 성공 사례</h2>
                <p><strong>배경:</strong> 생산 라인의 효율성과 품질 관리 향상이 필요했습니다.</p>
                <p><strong>결과:</strong> 불량률 30% 감소, 검사 시간 50% 단축을 달성했습니다.</p>
            </section>
            
            <section>
                <h2>📅 다가오는 이벤트</h2>
                <h2>컨퍼런스 및 워크샵</h2>
                <ul>
                <li><strong>AI Seoul 2025</strong> - 2025년 4월 15-17일 - COEX</li>
                </ul>
            </section>
            
            <section>
                <h2>❓ 질문 & 답변</h2>
                <p><strong>Q: 중소기업이 AI를 도입할 때 가장 주의해야 할 점은 무엇인가요?</strong></p>
                <p><strong>A:</strong> 중소기업이 AI를 도입할 때는 명확한 목표 설정, 현실적인 기대치, 그리고 단계적 접근이 중요합니다.</p>
            </section>
            
            <div class="footer">
                <p>© {datetime.now().year} AIDT Weekly | 실제 생성된 뉴스레터는 이와 다를 수 있습니다.</p>
                <p>이 미리보기는 예시 콘텐츠로, 실제 생성 시 최신 AI 관련 내용으로 업데이트됩니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

def generate_newsletter(api_key):
    os.environ["OPENAI_API_KEY"] = api_key  # API 키 설정
    
    # 클라이언트 초기화
    client = OpenAI(api_key=api_key)
    
    date = datetime.now().strftime('%Y년 %m월 %d일')
    issue_number = 1
    
    prompts = {
        'main_news': """
        AIDT Weekly 뉴스레터의 '주요 소식' 섹션을 생성해주세요.
        형식:
        
        ## 주요소식 1
        - 제목: [AI 관련 새로운 소식]
        - 내용: [구체적인 내용]
        - 효과: [도입 효과나 의의]
        
        ## 주요소식 2
        - 제목: [다른 AI 관련 소식]
        - 내용: [구체적인 내용]
        - 효과: [도입 효과나 의의]
        """,
        'aidt_tips': """
        AIDT Weekly 뉴스레터의 'AI 활용 팁' 섹션을 생성해주세요.
        형식:
        
        ## 이번 주 팁: [팁 제목]
        
        [팁에 대한 설명과 활용 방법을 상세히 서술해주세요]
        
        **실행 단계:**
        - 1단계: [설명]
        - 2단계: [설명]
        - 3단계: [설명]
        
        **이 팁을 활용하면:**
        - [장점 1]
        - [장점 2]
        """,
        'success_story': """
        AIDT Weekly 뉴스레터의 '성공 사례' 섹션을 생성해주세요.
        형식:
        
        ## [회사/기관 이름]의 AI 활용 성공 사례
        
        **배경:** [기업이 직면한 문제 또는 도전 과제]
        
        **솔루션:** [어떤 AI 기술을 도입했는지]
        
        **결과:** [구체적인 성과와 비즈니스 효과]
        
        **시사점:** [다른 기업들이 배울 수 있는 교훈]
        """,
        'events': f"""
        AIDT Weekly 뉴스레터의 '다가오는 이벤트' 섹션을 생성해주세요.
        현재 날짜는 {date}입니다.
        형식:
        
        ## 컨퍼런스 및 워크샵
        - **[이벤트 이름]** - [날짜] - [장소/온라인]
          [간단한 설명과 참여 대상]
        
        ## 웨비나
        - **[웨비나 제목]** - [날짜 및 시간]
          [주제 및 참여 방법]
        
        ## 교육 과정
        - **[과정명]** - [시작 날짜 ~ 종료 날짜]
          [교육 내용 및 신청 방법]
        """,
        'qa': """
        AIDT Weekly 뉴스레터의 'Q&A' 섹션을 생성해주세요.
        형식:
        
        ## 이번 주 질문
        
        **Q: [AI 관련 자주 묻는 질문]**
        
        **A:** [전문가의 자세한 답변]
        
        **추가 자료:**
        - [관련 자료 링크 또는 설명]
        - [관련 자료 링크 또는 설명]
        """
    }
    
    newsletter_content = {}
    
    for section, prompt in prompts.items():
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "AI 디지털 트랜스포메이션 뉴스레터 콘텐츠 생성 전문가. 깔끔하고 전문적인 뉴스레터 콘텐츠를 생성합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            newsletter_content[section] = convert_markdown_to_html(response.choices[0].message.content)
        except Exception as e:
            newsletter_content[section] = f"<p>콘텐츠 생성 오류: {e}</p>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AIDT Weekly - 제{issue_number}호</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .container {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            h1 {{
                color: #2c3e50;
                font-size: 28px;
                margin-bottom: 10px;
            }}
            .issue-date {{
                color: #7f8c8d;
                font-size: 16px;
                margin-bottom: 20px;
            }}
            section {{
                margin-bottom: 40px;
            }}
            h2 {{
                color: #3498db;
                font-size: 22px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
                margin-top: 30px;
            }}
            h3 {{
                color: #2c3e50;
                font-size: 18px;
                margin-top: 20px;
                margin-bottom: 10px;
            }}
            p {{
                margin-bottom: 15px;
            }}
            ul {{
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 10px;
            }}
            strong {{
                color: #2c3e50;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #7f8c8d;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>AIDT Weekly</h1>
                <div class="issue-date">제{issue_number}호 | {date}</div>
            </header>
            
            <section>
                <h2>🔔 주요 소식</h2>
                {newsletter_content['main_news']}
            </section>
            
            <section>
                <h2>💡 이번 주 AIDT 팁</h2>
                {newsletter_content['aidt_tips']}
            </section>
            
            <section>
                <h2>🏆 성공 사례</h2>
                {newsletter_content['success_story']}
            </section>
            
            <section>
                <h2>📅 다가오는 이벤트</h2>
                {newsletter_content['events']}
            </section>
            
            <section>
                <h2>❓ 질문 & 답변</h2>
                {newsletter_content['qa']}
            </section>
            
            <div class="footer">
                <p>© {datetime.now().year} AIDT Weekly | 본 뉴스레터를 구독해 주셔서 감사합니다.</p>
                <p>문의사항이나 제안이 있으시면 언제든지 연락해 주세요.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

def create_download_link(html_content, filename):
    """HTML 콘텐츠를 다운로드할 수 있는 링크를 생성합니다."""
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'
    return href

def main():
    st.title("AIDT 뉴스레터 생성기")
    st.write("GPT-4를 활용하여 AI 디지털 트랜스포메이션 관련 뉴스레터를 자동으로 생성합니다.")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["뉴스레터 생성", "미리보기"])
    
    with tab1:
        api_key = st.text_input("OpenAI API 키 입력", type="password")
        
        if st.button("뉴스레터 생성"):
            if not api_key:
                st.error("API 키를 입력하세요.")
            else:
                with st.spinner("뉴스레터 생성 중... (약 1-2분 소요될 수 있습니다)"):
                    try:
                        html_content = generate_newsletter(api_key)
                        filename = f"AIDT_Weekly_{datetime.now().strftime('%Y%m%d')}.html"
                        
                        st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                        st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                        
                        # 미리보기 표시 (iframe 사용)
                        st.subheader("생성된 뉴스레터")
                        st.markdown(
                            f'<iframe srcdoc="{html_content.replace(chr(34), chr(39))}" width="100%" height="600" frameborder="0"></iframe>',
                            unsafe_allow_html=True
                        )
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
    
    with tab2:
        st.subheader("뉴스레터 레이아웃 미리보기")
        st.write("아래는 뉴스레터가 어떻게 보이는지 예시로 보여주는 미리보기입니다. 실제 생성된 뉴스레터는 최신 AI 관련 내용으로 채워집니다.")
        
        # 미리보기 HTML (iframe 사용)
        preview_html = get_preview_html()
        st.markdown(
            f'<iframe srcdoc="{preview_html.replace(chr(34), chr(39))}" width="100%" height="600" frameborder="0"></iframe>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()