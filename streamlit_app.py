import os
import requests
import json
import base64
from datetime import datetime, timedelta
import streamlit as st
from openai import OpenAI
import pandas as pd
import re

# 페이지 설정
st.set_page_config(
    page_title="AIDT Weekly 뉴스레터 생성기",
    page_icon="📬",
    layout="wide"
)

# 세션 상태 초기화 - 가장 먼저 실행
if 'issue_number' not in st.session_state:
    st.session_state['issue_number'] = 1
if 'newsletter_html' not in st.session_state:
    st.session_state['newsletter_html'] = ""
if 'generated' not in st.session_state:
    st.session_state['generated'] = False
if 'subscribers' not in st.session_state:
    st.session_state['subscribers'] = pd.DataFrame({
        '이메일': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        '이름': ['김테스트', '이데모', '박샘플'],
        '부서': ['마케팅', 'IT', '인사'],
        '구독일': ['2025-02-01', '2025-02-15', '2025-03-01']
    })


# 사이드바 생성
st.sidebar.title("AIDT Weekly 뉴스레터")
st.sidebar.image("https://via.placeholder.com/150x100?text=AIDT", width=150)

# API 키 입력
with st.sidebar.expander("API 설정", expanded=True):
    openai_api_key = st.text_input("OpenAI API 키", type="password", 
                                  help="OpenAI API 키를 입력하세요. 이 키는 저장되지 않습니다.")
    news_api_key = st.text_input("News API 키 (선택사항)", type="password",
                               help="News API 키를 입력하세요. 뉴스 기능을 사용하지 않으려면 비워두세요.")

# 메인 페이지 제목
st.title("AIDT Weekly 뉴스레터 생성기")
st.markdown("---")

# 유틸리티 함수
def get_openai_client():
    """OpenAI 클라이언트를 생성합니다."""
    if not openai_api_key:
        st.error("OpenAI API 키를 입력해주세요.")
        st.stop()
    return OpenAI(api_key=openai_api_key)

def fetch_ai_news(max_articles=3):
    """AI 관련 최신 뉴스를 가져옵니다."""
    if not news_api_key:
        return []
        
    try:
        params = {
            "q": "artificial intelligence",
            "language": "ko",
            "apiKey": news_api_key,
            "pageSize": max_articles,
            "sortBy": "publishedAt"
        }
        
        response = requests.get("https://newsapi.org/v2/top-headlines", params=params)
        if response.status_code == 200:
            return response.json()["articles"]
        else:
            st.sidebar.warning(f"뉴스 가져오기 실패: {response.status_code}")
            return []
    except Exception as e:
        st.sidebar.warning(f"뉴스 API 호출 중 오류 발생: {e}")
        return []

def generate_ai_tip(client):
    """AI 활용 팁을 생성합니다."""
    with st.spinner('AI 팁을 생성하는 중...'):
        prompt = """
        직장에서 AI 도구(ChatGPT, 코파일럿 등)를 효과적으로 활용하기 위한 실용적인 팁을 생성해주세요.
        다음 형식으로 작성해 주세요:
        
        1. 제목: [팁의 제목]
        2. 팁 내용: [3-5개의 구체적인 조언]
        3. 실제 사례: [팁을 적용한 짧은 예시]
        4. 오늘의 공유 팁: [한 문장으로 된 핵심 조언]
        
        팁은 구체적이고 실용적이어야 하며, 직장인이 바로 적용할 수 있는 내용이어야 합니다.
        """
        
        # 사이드바에서 선택한 모델과 설정값 사용
        selected_model = model_option if 'model_option' in locals() else "gpt-4"
        selected_temp = temperature if 'temperature' in locals() else 0.7
        selected_max_tokens = max_tokens if 'max_tokens' in locals() else 500
        
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "당신은 AI 디지털 트랜스포메이션 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=selected_max_tokens,
            temperature=selected_temp
        )
        
        return parse_ai_tip(response.choices[0].message.content)

def parse_ai_tip(content):
    """AI가 생성한 팁을 파싱하여 구조화된 형태로 반환합니다."""
    lines = content.split('\n')
    tip = {
        "title": "",
        "content": [],
        "example": "",
        "share_tip": ""
    }
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if "제목:" in line:
            tip["title"] = line.split("제목:")[1].strip()
        elif "팁 내용:" in line:
            current_section = "content"
        elif "실제 사례:" in line:
            current_section = "example"
            tip["example"] = line.split("실제 사례:")[1].strip()
        elif "오늘의 공유 팁:" in line:
            tip["share_tip"] = line.split("오늘의 공유 팁:")[1].strip()
        elif current_section == "content" and line.strip():
            # 숫자. 으로 시작하는 라인은 새로운 팁
            if line[0].isdigit() and ". " in line:
                tip_text = line.split(". ", 1)[1]
                tip["content"].append(tip_text)
            else:
                # 이어지는 내용
                if tip["content"]:
                    tip["content"][-1] += " " + line
    
    return tip

def generate_success_story(client):
    """AI 성공 사례를 생성합니다."""
    with st.spinner('성공 사례를 생성하는 중...'):
        prompt = """
        회사 내에서 AI를 활용하여 업무 프로세스를 개선한 성공 사례를 생성해주세요.
        다음 형식으로 작성해 주세요:
        
        1. 제목: [부서명]의 [간결한 성공 사례 제목]
        2. 문제 상황: [AI 도입 전 어떤 문제가 있었는지]
        3. AIDT 적용 방법: [어떤 AI 기술을 어떻게 적용했는지]
        4. 결과: [도입 후 개선된 점, 가능하면 구체적인 수치 포함]
        5. 담당자 코멘트: [성공 사례의 담당자가 한 말]
        
        사례는 구체적이고 현실적이어야 하며, 다양한 부서(HR, 마케팅, 재무, 고객 서비스 등)에서 적용할 수 있는 내용이어야 합니다.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 AI 디지털 트랜스포메이션 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return parse_success_story(response.choices[0].message.content)

def parse_success_story(content):
    """AI가 생성한 성공 사례를 파싱하여 구조화된 형태로 반환합니다."""
    lines = content.split('\n')
    story = {
        "title": "",
        "problem": "",
        "method": "",
        "result": "",
        "comment": ""
    }
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if "제목:" in line:
            story["title"] = line.split("제목:")[1].strip()
        elif "문제 상황:" in line:
            story["problem"] = line.split("문제 상황:")[1].strip()
        elif "AIDT 적용 방법:" in line:
            story["method"] = line.split("AIDT 적용 방법:")[1].strip()
        elif "결과:" in line:
            story["result"] = line.split("결과:")[1].strip()
        elif "담당자 코멘트:" in line:
            story["comment"] = line.split("담당자 코멘트:")[1].strip()
    
    return story

def generate_qa_content(client):
    """Q&A 콘텐츠를 생성합니다."""
    with st.spinner('Q&A 콘텐츠를 생성하는 중...'):
        prompt = """
        회사에서 AI 디지털 트랜스포메이션(AIDT)을 도입하면서 직원들이 자주 묻는 질문과 그에 대한 답변을 생성해주세요.
        질문은 기술적인 부분보다는 일반 직원들의 우려나 궁금증에 초점을 맞추어 주세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 AI 디지털 트랜스포메이션 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.7
        )
        
        return {
            "question": "Q: AIDT를 업무에 적용하려면 어디서부터 시작해야 할까요?",
            "answer": response.choices[0].message.content
        }

def generate_upcoming_events(client):
    """다가오는 이벤트 정보를 생성합니다."""
    with st.spinner('이벤트 정보를 생성하는 중...'):
        today = datetime.now()
        next_week = today + timedelta(days=7)
        
        prompt = f"""
        AI 디지털 트랜스포메이션(AIDT)과 관련된 사내 이벤트를 생성해주세요.
        오늘은 {today.strftime('%Y년 %m월 %d일')}이고, 이벤트는 이번 주부터 다음 주({next_week.strftime('%Y년 %m월 %d일')}) 사이에 진행된다고 가정합니다.
        이벤트는 제목, 날짜, 시간, 간단한 설명을 포함해야 합니다.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 AI 디지털 트랜스포메이션 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        event_text = response.choices[0].message.content
        
        # 첫 번째 줄을 제목으로, 나머지를 설명으로 간주
        lines = event_text.split('\n', 1)
        title = lines[0].strip()
        description = lines[1].strip() if len(lines) > 1 else ""
        
        # 날짜 형식 추출 (예: "3월 15일(금) 오후 2시")
        date_pattern = r'\d+월\s+\d+일\(\w+\)\s+[오전|오후]\s+\d+시'
        date_match = re.search(date_pattern, event_text)
        date_str = date_match.group(0) if date_match else f"{(today + timedelta(days=5)).strftime('%m월 %d일')}(금) 오후 2시"
        
        return {
            "title": title,
            "date": date_str,
            "description": description
        }

def generate_ai_caution(client):
    """AI 사용 시 주의사항을 생성합니다."""
    with st.spinner('AI 주의사항을 생성하는 중...'):
        prompt = """
        직장에서 AI 도구를 사용할 때 주의해야 할 점에 대한 짧은 팁을 작성해주세요.
        특히 데이터 보안, 정보 검증, 윤리적 사용에 관한 내용을 포함해 주세요.
        100단어 내외로 간결하게 작성해 주세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 AI 디지털 트랜스포메이션 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content

def format_newsletter(issue_number, data):
    """뉴스레터 내용을 HTML 형식으로 포맷팅합니다."""
    today = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 뉴스 요약
    news_html = ""
    if data['news']:
        news_summary = f"<p><strong>AI 관련 주요 소식:</strong> "
        for i, article in enumerate(data['news']):
            if i > 0:
                news_summary += " / "
            news_summary += f"<a href='{article['url']}'>{article['title']}</a>"
        news_summary += "</p>"
        news_html = news_summary
    
    # 팁 콘텐츠 형식화
    tip_content_html = "<ol>"
    for item in data['tip']["content"]:
        if ':' in item:
            tip_content_html += f"<li><strong>{item.split(':')[0]}:</strong> {':'.join(item.split(':')[1:])}</li>"
        else:
            tip_content_html += f"<li>{item}</li>"
    tip_content_html += "</ol>"
    
    # HTML 템플릿
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AIDT Weekly - 제{issue_number}호 ({today})</title>
        <style>
            body {{
                font-family: 'Noto Sans KR', Arial, sans-serif;
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
                padding: 20px;
            }}
            .header {{
                text-align: center;
                padding: 20px 0;
                border-bottom: 2px solid #0066cc;
            }}
            .header img {{
                max-width: 150px;
                height: auto;
            }}
            .header h1 {{
                color: #0066cc;
                margin: 10px 0 5px;
                font-size: 24px;
            }}
            .header p {{
                color: #666;
                margin: 0;
                font-size: 14px;
            }}
            .section {{
                margin: 25px 0;
                clear: both;
            }}
            .section h2 {{
                color: #0066cc;
                margin-top: 0;
                padding-bottom: 5px;
                border-bottom: 1px solid #eee;
                font-size: 18px;
            }}
            .tip-box {{
                background-color: #e9f5ff;
                border-left: 4px solid #0066cc;
                padding: 15px;
                margin: 20px 0;
            }}
            .tip-box h3 {{
                margin-top: 0;
                color: #0066cc;
                font-size: 16px;
            }}
            .success-story {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
            }}
            .success-story p.quote {{
                font-style: italic;
                color: #666;
                border-left: 3px solid #ccc;
                padding-left: 10px;
                margin-left: 0;
            }}
            .q-and-a {{
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
            }}
            .q-and-a p.question {{
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .events {{
                background-color: #fff8e9;
                padding: 15px;
                border-radius: 5px;
            }}
            .footer {{
                text-align: center;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #999;
                font-size: 12px;
            }}
            .footer a {{
                color: #0066cc;
                text-decoration: none;
            }}
            .button {{
                display: inline-block;
                background-color: #0066cc;
                color: white !important;
                padding: 8px 15px;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 10px;
            }}
            .share-tip {{
                background-color: #fffbe6;
                border: 1px dashed #ffd700;
                padding: 12px 15px;
                margin: 20px 0;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AIDT Weekly</h1>
                <p>제{issue_number}호 | {today}</p>
            </div>

            <div class="section">
                <h2>🔔 주요 소식</h2>
                <p>안녕하세요! <strong>AIDT Weekly</strong> 제{issue_number}호를 발행합니다. 이번 주에도 AI 디지털 트랜스포메이션에 관한 유용한 소식과 팁을 전해드립니다.</p>
                
                {news_html}
            </div>

            <div class="section">
                <h2>💡 이번 주 AIDT 팁</h2>
                <h3>{data['tip']["title"]}</h3>
                
                {tip_content_html}
                
                <div class="share-tip">
                    <strong>오늘의 공유 팁</strong><br>
                    {data['tip']["share_tip"]}
                </div>
            </div>

            <div class="section">
                <h2>🏆 성공 사례</h2>
                <div class="success-story">
                    <h3>{data['success']["title"]}</h3>
                    <p><strong>문제 상황:</strong> {data['success']["problem"]}</p>
                    <p><strong>AIDT 적용 방법:</strong> {data['success']["method"]}</p>
                    <p><strong>결과:</strong> {data['success']["result"]}</p>
                    <p class="quote">"{data['success']["comment"]}"</p>
                </div>
            </div>

            <div class="section">
                <h2>❓ 질문 & 답변</h2>
                <div class="q-and-a">
                    <p class="question">{data['qa']["question"]}</p>
                    <p>{data['qa']["answer"]}</p>
                    
                    <p><a href="#" class="button">질문 제출하기</a></p>
                </div>
            </div>

            <div class="section">
                <h2>📅 다가오는 이벤트</h2>
                <div class="events">
                    <p><strong>{data['event']["date"]}</strong> - {data['event']["title"]}</p>
                    <p>{data['event']["description"]}</p>
                    <p><a href="#" class="button">일정 확인하기</a></p>
                </div>
            </div>

            <div class="tip-box">
                <h3>AI 사용 시 주의사항</h3>
                <p>{data['caution']}</p>
            </div>

            <div class="footer">
                <p>이 뉴스레터는 매주 월요일에 발송됩니다.<br>
                문의사항: <a href="mailto:aidt@company.com">aidt@company.com</a><br>
                © {datetime.now().year} AIDT 추진팀</p>
                
                <p>
                    <a href="#">구독 취소</a> | 
                    <a href="#">과거 뉴스레터 보기</a> | 
                    <a href="#">피드백 제출</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def get_html_download_link(html_string, filename="뉴스레터.html"):
    """HTML 파일 다운로드 링크를 생성합니다."""
    b64 = base64.b64encode(html_string.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">뉴스레터 HTML 파일 다운로드</a>'
    return href

# 설정 탭
# 그리고 number_input 부분을 다음과 같이 수정
with st.expander("뉴스레터 설정", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        # 직접 st.session_state.issue_number를 사용하지 말고 아래와 같이 작성
        current_issue = st.session_state['issue_number']
        issue_number = st.number_input("뉴스레터 호수", min_value=1, value=current_issue)
        st.session_state['issue_number'] = issue_number
    with col2:
        newsletter_date = st.date_input("발행일", datetime.now())

# 뉴스레터 생성 버튼
if st.button("뉴스레터 생성하기"):
    if not openai_api_key:
        st.error("OpenAI API 키를 입력해주세요.")
    else:
        try:
            with st.spinner('뉴스레터를 생성하는 중입니다...'):
                # OpenAI 클라이언트 생성
                client = get_openai_client()
                
                # 각 섹션 콘텐츠 생성
                progress_bar = st.progress(0)
                
                # 뉴스 가져오기
                news = fetch_ai_news(3)
                progress_bar.progress(20)
                
                # AI 팁 생성
                tip = generate_ai_tip(client)
                progress_bar.progress(40)
                
                # 성공 사례 생성
                success = generate_success_story(client)
                progress_bar.progress(60)
                
                # Q&A 콘텐츠 생성
                qa = generate_qa_content(client)
                progress_bar.progress(80)
                
                # 이벤트 정보 생성
                event = generate_upcoming_events(client)
                
                # AI 주의사항 생성
                caution = generate_ai_caution(client)
                progress_bar.progress(100)
                
                # 데이터 구성
                newsletter_data = {
                    'news': news,
                    'tip': tip,
                    'success': success,
                    'qa': qa,
                    'event': event,
                    'caution': caution
                }
                
                # HTML 형식으로 포맷팅
                html_content = format_newsletter(issue_number, newsletter_data)
                
                # 세션 상태에 저장
                st.session_state.newsletter_html = html_content
                st.session_state.generated = True
                
                st.success("뉴스레터가 성공적으로 생성되었습니다!")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# 생성된 뉴스레터 표시
if st.session_state.generated:
    tabs = st.tabs(["미리보기", "HTML 코드", "다운로드"])
    
    with tabs[0]:  # 미리보기 탭
        st.components.v1.html(st.session_state.newsletter_html, height=600, scrolling=True)
    
    with tabs[1]:  # HTML 코드 탭
        st.code(st.session_state.newsletter_html, language="html")
    
    with tabs[2]:  # 다운로드 탭
        today = datetime.now().strftime("%Y%m%d")
        filename = f"aidt_weekly_{st.session_state.issue_number}_{today}.html"
        st.markdown(get_html_download_link(st.session_state.newsletter_html, filename), unsafe_allow_html=True)
        
        st.markdown("### 이메일 발송 설정")
        st.info("현재 이 데모에서는 실제 이메일 발송 기능을 제공하지 않습니다. 다운로드한 HTML 파일을 이메일 서비스에 업로드하여 발송하세요.")
        
        # 구독자 관리 데모
        st.markdown("### 구독자 관리")
        
        # 구독자 목록 표시
        st.dataframe(st.session_state.subscribers)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 구독자 추가 기능
            st.markdown("#### 구독자 추가")
            new_email = st.text_input("이메일", key="new_email")
            new_name = st.text_input("이름", key="new_name")
            new_dept = st.text_input("부서", key="new_dept")
            
            if st.button("구독자 추가"):
                if not new_email or '@' not in new_email:
                    st.warning("유효한 이메일 주소를 입력해주세요.")
                else:
                    new_row = pd.DataFrame({
                        '이메일': [new_email],
                        '이름': [new_name or ''],
                        '부서': [new_dept or ''],
                        '구독일': [datetime.now().strftime("%Y-%m-%d")]
                    })
                    st.session_state.subscribers = pd.concat([st.session_state.subscribers, new_row], ignore_index=True)
                    st.success("구독자가 추가되었습니다!")
        
        with col2:
            # 구독자 삭제 기능
            st.markdown("#### 구독자 삭제")
            if len(st.session_state.subscribers) > 0:
                email_to_delete = st.selectbox(
                    "삭제할 구독자 선택",
                    options=st.session_state.subscribers['이메일'].tolist()
                )
                
                if st.button("구독자 삭제"):
                    st.session_state.subscribers = st.session_state.subscribers[
                        st.session_state.subscribers['이메일'] != email_to_delete
                    ].reset_index(drop=True)
                    st.success("구독자가 삭제되었습니다!")
            else:
                st.info("삭제할 구독자가 없습니다.")

# 사이드바에 도움말 추가
with st.sidebar.expander("도움말"):
    st.markdown("""
    ### 사용 방법
    1. OpenAI API 키를 입력하세요. (필수)
    2. News API 키를 입력하면 최신 AI 뉴스를 가져올 수 있습니다. (선택)
    3. 뉴스레터 호수와 발행일을 설정하세요.
    4. '뉴스레터 생성하기' 버튼을 클릭하세요.
    5. 생성된 뉴스레터를 미리보고, HTML 코드를 확인하거나 파일로 다운로드할 수 있습니다.
    6. 구독자 관리 섹션에서 구독자를 추가하거나 삭제할 수 있습니다.
    
    ### 참고사항
    - 이 앱은 OpenAI의 GPT 모델을 사용하여 콘텐츠를 생성합니다.
    - 생성된 콘텐츠는 검토 후 사용하는 것을 권장합니다.
    - API 키는 로컬에만 저장되며 서버로 전송되지 않습니다.
    """)

# 푸터 추가
st.sidebar.markdown("---")
st.sidebar.markdown("© 2025 AIDT 추진팀")

# 모델 선택 옵션 추가
with st.sidebar.expander("고급 설정"):
    model_option = st.selectbox(
        "OpenAI 모델 선택",
        options=["gpt-4", "gpt-3.5-turbo"],
        index=0,
        help="콘텐츠 생성에 사용할 OpenAI 모델을 선택하세요. GPT-4가 더 고품질의 결과를 제공하지만, GPT-3.5는 더 빠르고 비용이 저렴합니다."
    )
    
    temperature = st.slider(
        "창의성 수준", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.7, 
        step=0.1,
        help="낮은 값은 더 일관된 결과를, 높은 값은 더 창의적인 결과를 제공합니다."
    )
    
    max_tokens = st.slider(
        "최대 토큰 수",
        min_value=100,
        max_value=1000,
        value=500,
        step=50,
        help="각 콘텐츠 생성 요청당 최대 토큰 수를 설정합니다."
    )