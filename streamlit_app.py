import streamlit as st
from openai import OpenAI
from datetime import datetime
import time
import base64
import os
import re

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
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .content {{
                padding: 20px;
            }}
            .header {{
                background-color: #3498db;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .title {{
                margin: 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .issue-date {{
                margin-top: 5px;
                font-size: 14px;
            }}
            .section {{
                margin-bottom: 25px;
                border-bottom: 1px solid #eee;
                padding-bottom: 20px;
            }}
            .section:last-child {{
                border-bottom: none;
            }}
            .section-title {{
                color: #3498db;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
            }}
            .section-icon {{
                margin-right: 8px;
            }}
            h3 {{
                font-size: 16px;
                margin-bottom: 5px;
                color: #2c3e50;
            }}
            p {{
                margin: 0 0 10px;
            }}
            ul {{
                padding-left: 20px;
                margin-top: 5px;
                margin-bottom: 10px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 15px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
            .preview-badge {{
                background-color: #ff7f50;
                color: white;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-left: 10px;
                vertical-align: middle;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">AIDT Weekly <span class="preview-badge">미리보기</span></div>
                <div class="issue-date">제{issue_number}호 | {date}</div>
            </div>
            
            <div class="content">
                <div class="section">
                    <div class="section-title"><span class="section-icon">🔔</span> 주요 소식</div>
                    <h3>OpenAI, GPT-5 개발 계획 발표</h3>
                    <p>OpenAI가 차세대 모델인 GPT-5의 개발 계획을 공개했습니다. 새 모델은 멀티모달 기능을 강화하고 더 긴 컨텍스트를 처리할 수 있게 됩니다.</p>
                    <p>기업들은 더 정확하고 맥락을 이해하는 AI 솔루션을 도입할 수 있게 될 것으로 예상됩니다.</p>
                    
                    <h3>EU, AI 규제 프레임워크 확정</h3>
                    <p>유럽연합이 AI 규제에 관한 최종 프레임워크를 확정했습니다. 이는 AI 개발과 사용에 대한 새로운 표준을 제시합니다.</p>
                    <p>글로벌 기업들은 EU 시장 진출을 위해 새로운 규제를 준수해야 합니다.</p>
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">💡</span> 이번 주 AIDT 팁</div>
                    <h3>프롬프트 엔지니어링 마스터하기</h3>
                    <p>AI 모델에서 최상의 결과를 얻기 위한 프롬프트 작성법을 알아봅니다.</p>
                    <p><strong>실행 단계:</strong></p>
                    <ul>
                        <li>명확한 목표 설정하기</li>
                        <li>구체적인 지시사항 포함하기</li>
                        <li>예시 추가하기</li>
                    </ul>
                    <p>이 팁을 활용하면 AI 모델의 출력 품질이 크게 향상되고 작업 시간을 단축할 수 있습니다.</p>
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">🏆</span> 성공 사례</div>
                    <h3>현대자동차의 AI 활용 성공 사례</h3>
                    <p><strong>배경:</strong> 생산 라인의 효율성과 품질 관리 향상이 필요했습니다.</p>
                    <p><strong>솔루션:</strong> 컴퓨터 비전 AI를 도입하여 자동차 부품 검사 자동화 시스템을 구축했습니다.</p>
                    <p><strong>결과:</strong> 불량률 30% 감소, 검사 시간 50% 단축, 연간 비용 20억 원 절감을 달성했습니다.</p>
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">📅</span> 다가오는 이벤트</div>
                    <h3>컨퍼런스 및 워크샵</h3>
                    <p><strong>AI Seoul 2025</strong> - 2025년 4월 15-17일 - COEX</p>
                    <p>한국 최대 AI 컨퍼런스로, 국내외 AI 전문가들의 강연과 네트워킹 기회 제공</p>
                    
                    <h3>웨비나</h3>
                    <p><strong>생성형 AI와 비즈니스 혁신</strong> - 2025년 3월 25일 오후 2시</p>
                    <p>기업 환경에서 생성형 AI를 효과적으로 활용하는 방법에 대한 웨비나</p>
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">❓</span> 질문 & 답변</div>
                    <p><strong>Q: 중소기업이 AI를 도입할 때 가장 주의해야 할 점은 무엇인가요?</strong></p>
                    <p><strong>A:</strong> 중소기업이 AI를 도입할 때는 명확한 목표 설정, 현실적인 기대치, 그리고 단계적 접근이 중요합니다. 모든 프로세스를 한 번에 자동화하려 하기보다 가장 효과가 큰 영역부터 시작하는 것이 좋습니다.</p>
                </div>
            </div>
            
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
        
        ## 첫 번째 소식 제목
        내용을 1-2문장으로 간략하게 작성하세요. 핵심 내용만 포함해주세요.
        영향이나 중요성을 한 문장으로 추가해주세요.
        
        ## 두 번째 소식 제목
        내용을 1-2문장으로 간략하게 작성하세요. 핵심 내용만 포함해주세요.
        영향이나 중요성을 한 문장으로 추가해주세요.
        """,
        'aidt_tips': """
        AIDT Weekly 뉴스레터의 'AI 활용 팁' 섹션을 생성해주세요.
        형식:
        
        ## 이번 주 팁: 팁 제목
        
        팁에 대한 설명을 2-3문장으로 간결하게 작성해주세요.
        
        **핵심 단계:**
        - 첫 번째 단계
        - 두 번째 단계
        - 세 번째 단계
        
        이 팁을 활용했을 때의 이점을 한 문장으로 작성해주세요.
        """,
        'success_story': """
        AIDT Weekly 뉴스레터의 '성공 사례' 섹션을 생성해주세요.
        형식:
        
        ## 회사/기관 이름의 AI 활용 사례
        
        **배경:** 한 문장으로 배경 설명
        
        **솔루션:** 한 문장으로 도입한 AI 기술 설명
        
        **결과:** 구체적인 수치로 성과 요약 (예: 30% 비용 절감, 40% 시간 단축 등)
        """,
        'events': f"""
        AIDT Weekly 뉴스레터의 '다가오는 이벤트' 섹션을 생성해주세요.
        현재 날짜는 {date}입니다.
        형식:
        
        ## 컨퍼런스/웨비나 제목
        - 날짜/시간: [날짜 정보]
        - 장소/형식: [장소 또는 온라인 여부]
        - 내용: 한 문장으로 간략한 설명
        
        ## 다른 이벤트 제목
        - 날짜/시간: [날짜 정보]
        - 장소/형식: [장소 또는 온라인 여부]
        - 내용: 한 문장으로 간략한 설명
        """,
        'qa': """
        AIDT Weekly 뉴스레터의 'Q&A' 섹션을 생성해주세요.
        형식:
        
        ## 간단명료한 질문?
        
        답변을 2-3문장으로 간결하게 작성해주세요. 불필요한 설명은 제외하고 핵심 정보만 포함해주세요.
        """
    }
    
    newsletter_content = {}
    
    for section, prompt in prompts.items():
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "AI 디지털 트랜스포메이션 뉴스레터 콘텐츠 생성 전문가. 간결하고 핵심적인 내용만 포함한 뉴스레터를 작성합니다."},
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
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .content {{
                padding: 20px;
            }}
            .header {{
                background-color: #3498db;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .title {{
                margin: 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .issue-date {{
                margin-top: 5px;
                font-size: 14px;
            }}
            .section {{
                margin-bottom: 25px;
                border-bottom: 1px solid #eee;
                padding-bottom: 20px;
            }}
            .section:last-child {{
                border-bottom: none;
            }}
            .section-title {{
                color: #3498db;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
            }}
            .section-icon {{
                margin-right: 8px;
            }}
            h2, h3 {{
                font-size: 16px;
                margin-bottom: 5px;
                color: #2c3e50;
            }}
            p {{
                margin: 0 0 10px;
            }}
            ul {{
                padding-left: 20px;
                margin-top: 5px;
                margin-bottom: 10px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 15px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">AIDT Weekly</div>
                <div class="issue-date">제{issue_number}호 | {date}</div>
            </div>
            
            <div class="content">
                <div class="section">
                    <div class="section-title"><span class="section-icon">🔔</span> 주요 소식</div>
                    {newsletter_content['main_news']}
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">💡</span> 이번 주 AIDT 팁</div>
                    {newsletter_content['aidt_tips']}
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">🏆</span> 성공 사례</div>
                    {newsletter_content['success_story']}
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">📅</span> 다가오는 이벤트</div>
                    {newsletter_content['events']}
                </div>
                
                <div class="section">
                    <div class="section-title"><span class="section-icon">❓</span> 질문 & 답변</div>
                    {newsletter_content['qa']}
                </div>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} AIDT Weekly | 뉴스레터 구독을 감사드립니다.</p>
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
        st.write("아래는 뉴스레터가 어떻게 보이는지 예시로 보여주는 미리보기입니다.")
        
        # 미리보기 HTML (iframe 사용)
        preview_html = get_preview_html()
        st.markdown(
            f'<iframe srcdoc="{preview_html.replace(chr(34), chr(39))}" width="100%" height="600" frameborder="0"></iframe>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()