import streamlit as st
from openai import OpenAI
from datetime import datetime, timedelta
import time
import base64
import os
import re
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class InternalEvent:
    """사내 이벤트를 위한 데이터 클래스"""
    title: str
    date_time: str
    location: str
    description: str

@dataclass
class NewsletterConfig:
    """뉴스레터 설정을 위한 데이터 클래스"""
    AI_TIP_TOPICS: List[str] = (
        "효과적인 프롬프트 작성의 기본 원칙 (Chain of Thought, Chain of Draft)",
        "특정 업무별 최적의 프롬프트 템플릿",
        "AI를 활용한 데이터 분석 프롬프트 기법",
        "창의적 작업을 위한 AI 프롬프트 전략",
        "AI와 협업하여 문제 해결하기",
        "다양한 AI 도구 활용법 비교",
        "업무 자동화를 위한 AI 프롬프트 설계",
        "AI를 활용한 의사결정 지원 기법"
    )
    MAX_NEWS_DAYS: int = 7
    MAX_NEWS_ARTICLES: int = 5
    MAX_OPENAI_NEWS: int = 3

@dataclass
class HighlightSettings:
    """하이라이트 박스 설정을 위한 데이터 클래스"""
    title: str = "중부Infra AT/DT 뉴스레터 개시"
    subtitle: str = "AI, 어떻게 시작할지 막막하다면?"
    link_text: str = "AT/DT 추진방향 →"
    link_url: str = "#"

def fetch_real_time_news(api_key: str, query: str = "AI digital transformation", 
                        days: int = 7, language: str = "en") -> List[Dict[str, Any]]:
    """NewsAPI를 사용하여 실시간 뉴스를 가져옵니다."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=min(days, 7))
    
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'from': start_date.strftime('%Y-%m-%d'),
        'to': end_date.strftime('%Y-%m-%d'),
        'sortBy': 'publishedAt',
        'language': language,
        'apiKey': api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        news_data = response.json()
        return news_data['articles']
    else:
        raise Exception(f"뉴스 가져오기 실패: {response.status_code} - {response.text}")

def format_news_info(articles: List[Dict[str, Any]], title: str = "최근 뉴스") -> str:
    """뉴스 기사 정보를 포맷팅합니다."""
    news_info = f"{title}:\n\n"
    for i, article in enumerate(articles):
        pub_date = datetime.fromisoformat(
            article['publishedAt'].replace('Z', '+00:00')
        ).strftime('%Y년 %m월 %d일')
        
        news_info += f"{i+1}. 제목: {article['title']}\n"
        news_info += f"   날짜: {pub_date}\n"
        news_info += f"   요약: {article['description']}\n"
        news_info += f"   출처: {article['source']['name']}\n"
        news_info += f"   URL: {article['url']}\n\n"
    
    return news_info

def generate_events_content(client: OpenAI, internal_events: Optional[List[InternalEvent]] = None) -> str:
    """이벤트 섹션 컨텐츠를 생성합니다."""
    prompt = """
    AIDT Weekly 뉴스레터의 '주요 행사 안내' 섹션을 생성해주세요.
    
    다음 형식으로 국내/외 주요 AI 컨퍼런스나 행사를 각각 1개씩 작성해주세요:
    
    ## 국내 주요 행사
    날짜/시간: [날짜 정보]
    장소/형식: [장소 또는 온라인 여부]
    내용: [한 문장으로 간략한 설명]
    
    ## 해외 주요 행사
    날짜/시간: [날짜 정보]
    장소/형식: [장소 또는 온라인 여부]
    내용: [한 문장으로 간략한 설명]
    """
    
    if internal_events:
        prompt += "\n\n## 사내 주요 일정\n"
        for event in internal_events:
            prompt += f"""
            {event.title}
            날짜/시간: {event.date_time}
            장소/형식: {event.location}
            내용: {event.description}
            """

    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "AI 컨퍼런스와 행사 정보 전문가입니다. 명확하고 실용적인 정보만 제공합니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content

def get_newsletter_styles() -> str:
    """뉴스레터 스타일 CSS를 반환합니다."""
    return """
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.5;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f9f9f9;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }
        .header {
            background-color: #333333;
            color: white;
            padding: 15px 20px;
            text-align: left;
        }
        .title {
            margin: 0;
            font-size: 20px;
            font-weight: bold;
        }
        .content {
            padding: 20px;
        }
        .section {
            margin-bottom: 25px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        .section-title {
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            background-color: #3e3e3e;
            padding: 8px 10px;
            border-radius: 4px;
        }
        .events-section h2 {
            font-size: 14px;
            color: #333333;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }
        .event-item {
            margin-bottom: 15px;
        }
        .event-details {
            margin-left: 15px;
            line-height: 1.2;
        }
        .event-details p {
            margin: 0;
            padding: 0;
            font-size: 10pt;
        }
        .tip-title {
            background-color: #f2f2f2;
            padding: 8px 10px;
            margin-bottom: 10px;
            border-radius: 4px;
            font-weight: bold;
        }
        .prompt-examples-title {
            background-color: #f2f2f2;
            padding: 8px 10px;
            margin: 15px 0 10px 0;
            border-radius: 4px;
            font-weight: bold;
        }
        .highlight-box {
            background-color: #fff9f5;
            border: 1px solid #ffe0cc;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }
        .highlight-title {
            color: #ff5722;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            text-align: center;
        }
        .highlight-subtitle {
            color: #666;
            font-size: 12px;
            text-align: center;
            margin-bottom: 15px;
        }
        .footer {
            background-color: #f1f1f1;
            padding: 10px;
            text-align: center;
            font-size: 9pt;
            color: #666;
        }
    </style>
    """

def convert_markdown_to_html(text: str) -> str:
    """마크다운 텍스트를 HTML로 변환합니다."""
    
    # 이벤트 섹션 특별 처리
    if "주요 행사" in text:
        # 이벤트 항목 간 줄간격 제거
        text = re.sub(r'(날짜/시간:.*?)(\n\n)', r'\1\n', text, flags=re.DOTALL)
        text = re.sub(r'(장소/형식:.*?)(\n\n)', r'\1\n', text, flags=re.DOTALL)
        text = re.sub(r'(내용:.*?)(\n\n)', r'\1\n', text, flags=re.DOTALL)
    
    # AT/DT 팁 섹션 특별 처리
    if "이번 주 팁:" in text:
        text = re.sub(
            r'^## 이번 주 팁: (.*?)$',
            r'<div class="tip-title">이번 주 팁: \1</div>',
            text,
            flags=re.MULTILINE
        )
        text = re.sub(
            r'\*\*핵심 프롬프트 예시:\*\*',
            r'<div class="prompt-examples-title">핵심 프롬프트 예시:</div>',
            text
        )
    
    # 기본 마크다운 변환
    text = re.sub(r'^# (.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    
    # 문단 처리
    paragraphs = text.split('\n\n')
    for i, paragraph in enumerate(paragraphs):
        if not any(tag in paragraph for tag in ['<h', '<div', '<li']):
            paragraphs[i] = f'<p>{paragraph}</p>'
        paragraphs[i] = paragraph.replace('\n', '<br>')
    
    return ''.join(paragraphs)

def generate_newsletter(openai_api_key: str, news_api_key: str, news_query: str,
                       language: str = "en", internal_events: Optional[List[InternalEvent]] = None,
                       issue_num: int = 1, highlight_settings: Optional[HighlightSettings] = None) -> str:
    """뉴스레터를 생성합니다."""
    client = OpenAI(api_key=openai_api_key)
    config = NewsletterConfig()
    
    if highlight_settings is None:
        highlight_settings = HighlightSettings()
    
    try:
        # 뉴스 수집
        news_articles = fetch_real_time_news(news_api_key, news_query, config.MAX_NEWS_DAYS, language)
        openai_articles = fetch_real_time_news(news_api_key, "OpenAI", config.MAX_NEWS_DAYS, language)
        
        # 뉴스 정보 포맷팅
        news_info = format_news_info(news_articles[:config.MAX_NEWS_ARTICLES], "일반 뉴스")
        openai_news_info = format_news_info(openai_articles[:config.MAX_OPENAI_NEWS], "OpenAI 관련 뉴스")
        
        # 현재 주차의 AI 팁 주제 선택
        current_topic = config.AI_TIP_TOPICS[(issue_num - 1) % len(config.AI_TIP_TOPICS)]
        
        # 주요 소식 생성
        main_news_prompt = f"""
        AIDT Weekly 뉴스레터의 '주요 소식' 섹션을 생성해주세요.
        
        === OpenAI 관련 뉴스 ===
        {openai_news_info}
        
        === 일반 뉴스 ===
        {news_info}
        
        총 2개의 주요 소식을 선택하여 작성해주세요:
        1. OpenAI 관련 뉴스에서 가장 중요한 1개
        2. 일반 뉴스에서 가장 중요한 1개
        
        각 소식은 다음 형식으로 작성:
        ## [주제]의 [핵심 강점/특징]은 [주목할만합니다/확인됐습니다/중요합니다].
        """
        
        main_news_response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "AI 뉴스 전문 에디터입니다."},
                {"role": "user", "content": main_news_prompt}
            ],
            temperature=0.7
        )
        
        # AT/DT 팁 생성
        tips_prompt = f"""
        이번 주 팁 주제는 "{current_topic}"입니다.
        실용적인 팁을 다음 형식으로 작성해주세요:
        
        ## 이번 주 팁: [주제에 맞는 구체적인 팁 제목]
        
        [팁에 대한 배경과 중요성 2-3문장]
        
        **핵심 프롬프트 예시:**
        - 첫 번째 프롬프트 템플릿 (Chain of Thought 활용):
          예시: [실제 예시]
          프롬프트: [템플릿]
        
        - 두 번째 프롬프트 템플릿 (Chain of Draft 활용):
          예시: [실제 예시]
          프롬프트: [템플릿]
        
        - 세 번째 프롬프트 템플릿 (Chain of Thought와 Chain of Draft 결합):
          예시: [실제 예시]
          프롬프트: [템플릿]
        """
        
        tips_response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "AI 프롬프트 엔지니어링 전문가입니다."},
                {"role": "user", "content": tips_prompt}
            ],
            temperature=0.7
        )
        
        # 이벤트 섹션 생성
        events_content = generate_events_content(client, internal_events)
        
        # 각 섹션 HTML 변환
        main_news_html = convert_markdown_to_html(main_news_response.choices[0].message.content)
        tips_html = convert_markdown_to_html(tips_response.choices[0].message.content)
        events_html = convert_markdown_to_html(events_content)
        
        # 날짜 정보
        date = datetime.now().strftime('%Y년 %m월 %d일')
        
        # 최종 HTML 생성
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AIDT Weekly - 제{issue_num}호</title>
            {get_newsletter_styles()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="title">중부Infra AT/DT Weekly</div>
                    <div class="issue-info">제{issue_num}호 | {date}</div>
                </div>
                
                <div class="content">
                    <div class="newsletter-intro">
                        <p>중부Infra AT/DT 뉴스레터는 모두가 AI발전 속도에 뒤쳐지지 않고 업무에 적용할 수 있도록 가장 흥미로운 AI 활용법을 전합니다.</p>
                    </div>
                    
                    <div class="highlight-box">
                        <div class="highlight-title">{highlight_settings.title}</div>
                        <div class="highlight-subtitle">{highlight_settings.subtitle}</div>
                        <p style="text-align: right;"><a href="{highlight_settings.link_url}">{highlight_settings.link_text}</a></p>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">주요 소식</div>
                        <div class="section-container main-news">
                            {main_news_html}
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">이번 주 AT/DT 팁</div>
                        <div class="section-container aidt-tips">
                            {tips_html}
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">주요 행사 안내</div>
                        <div class="section-container events-section">
                            {events_html}
                        </div>
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
    
    except Exception as e:
        raise Exception(f"뉴스레터 생성 중 오류 발생: {str(e)}")

def create_download_link(html_content: str, filename: str) -> str:
    """HTML 콘텐츠를 다운로드할 수 있는 링크를 생성합니다."""
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #ff5722; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'

def main():
    st.title("AIDT 뉴스레터 생성기")
    st.write("GPT-4와 실시간 뉴스 API를 활용하여 AI 디지털 트랜스포메이션 관련 뉴스레터를 자동으로 생성합니다.")
    
    # API 키 입력
    with st.expander("API 키 설정", expanded=True):
        st.info("NewsAPI.org에서 API 키를 발급받을 수 있습니다. (https://newsapi.org)")
        openai_api_key = st.text_input("OpenAI API 키 입력", type="password")
        news_api_key = st.text_input("News API 키 입력", type="password")
    
    # 뉴스레터 기본 설정
    with st.expander("뉴스레터 기본 설정", expanded=True):
        issue_number = st.number_input("뉴스레터 호수", min_value=1, value=1, step=1)
        
        news_query = st.text_input(
            "뉴스 검색어", 
            value="Telecommunication AND AI digital transformation AND artificial intelligence",
            help="뉴스 API 검색어를 입력하세요. OR, AND 등의 연산자를 사용할 수 있습니다."
        )
        
        language = st.selectbox(
            "뉴스 언어",
            options=["en", "ko", "ja", "zh", "fr", "de"],
            format_func=lambda x: {
                "en": "영어", "ko": "한국어", "ja": "일본어",
                "zh": "중국어", "fr": "프랑스어", "de": "독일어"
            }[x],
            help="뉴스 검색 결과의 언어를 선택하세요."
        )
        
        st.info("⚠️ 참고: NewsAPI 무료 플랜은 약 7일 이내의 최신 뉴스만 조회할 수 있습니다.")
    
    # 하이라이트 박스 설정
    with st.expander("하이라이트 박스 설정"):
        highlight_settings = HighlightSettings(
            title=st.text_input("하이라이트 제목", value="중부Infra AT/DT 뉴스레터 개시"),
            subtitle=st.text_input("하이라이트 부제목", value="AI, 어떻게 시작할지 막막하다면?"),
            link_text=st.text_input("링크 텍스트", value="AT/DT 추진방향 →"),
            link_url=st.text_input("링크 URL", value="#")
        )
    
    # 사내 행사 입력
    with st.expander("사내 주요 일정 입력"):
        st.write("최대 2개의 사내 일정을 입력할 수 있습니다.")
        internal_events = []
        
        for i in range(2):
            st.subheader(f"사내 일정 {i+1}")
            col1, col2 = st.columns(2)
            
            with col1:
                event_title = st.text_input(f"일정 제목", key=f"event_title_{i}")
                event_date = st.text_input(f"날짜/시간", key=f"event_date_{i}")
            
            with col2:
                event_location = st.text_input(f"장소/형식", key=f"event_location_{i}")
                event_description = st.text_input(f"내용", key=f"event_description_{i}")
            
            if all([event_title, event_date, event_location, event_description]):
                internal_events.append(InternalEvent(
                    title=event_title,
                    date_time=event_date,
                    location=event_location,
                    description=event_description
                ))
    
    # 뉴스레터 생성 버튼
    if st.button("뉴스레터 생성"):
        if not openai_api_key or not news_api_key:
            st.error("OpenAI API 키와 News API 키를 모두 입력하세요.")
        else:
            with st.spinner("뉴스레터 생성 중... (약 1-2분 소요될 수 있습니다)"):
                try:
                    html_content = generate_newsletter(
                        openai_api_key=openai_api_key,
                        news_api_key=news_api_key,
                        news_query=news_query,
                        language=language,
                        internal_events=internal_events if internal_events else None,
                        issue_num=issue_number,
                        highlight_settings=highlight_settings
                    )
                    
                    filename = f"중부_ATDT_Weekly-제{issue_number}호.html"
                    
                    st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                    st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                    
                    # 미리보기 표시
                    st.subheader("생성된 뉴스레터 미리보기")
                    st.components.v1.html(html_content, height=800)
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()