import streamlit as st
from openai import OpenAI
from datetime import datetime, timedelta
import base64
import os
import re
import requests

def convert_markdown_to_html(text):
    """마크다운 텍스트를 HTML로 변환합니다."""
    # AT/DT 팁 섹션 특별 처리
    if "이번 주 팁:" in text or "핵심 프롬프트 예시" in text:
        # "이번 주 팁:" 제목을 특별 클래스로 처리
        text = re.sub(r'^## 이번 주 팁: (.*?)$', r'<div class="tip-title">이번 주 팁: \1</div>', text, flags=re.MULTILINE)
        
        # "핵심 프롬프트 예시:" 부분을 특별 클래스로 처리
        text = re.sub(r'\*\*핵심 프롬프트 예시:\*\*', r'<div class="prompt-examples-title">핵심 프롬프트 예시:</div>', text)
        
        # 프롬프트 템플릿 처리 (Chain of Thought/Chain of Draft 등)
        # 각 템플릿은 제목(색상 강조), 예시, 내용으로 구성됨
        
        # 첫 번째 템플릿 (Chain of Thought)
        text = re.sub(
            r'- (첫 번째 프롬프트 템플릿 \(Chain of Thought 활용\):)(.*?)(?=- 두 번째 프롬프트|$)',
            r'<div class="prompt-template">'
            r'<div class="template-title">\1</div>'
            r'<div class="template-content">\2</div>'
            r'</div>',
            text, 
            flags=re.DOTALL
        )
        
        # 두 번째 템플릿 (Chain of Draft)
        text = re.sub(
            r'- (두 번째 프롬프트 템플릿 \(Chain of Draft 활용\):)(.*?)(?=- 세 번째 프롬프트|$)',
            r'<div class="prompt-template">'
            r'<div class="template-title">\1</div>'
            r'<div class="template-content">\2</div>'
            r'</div>',
            text, 
            flags=re.DOTALL
        )
        
        # 세 번째 템플릿 (Chain of Thought와 Chain of Draft 결합)
        text = re.sub(
            r'- (세 번째 프롬프트 템플릿 \(Chain of Thought와 Chain of Draft 결합\):)(.*?)(?=이 팁을|$)',
            r'<div class="prompt-template">'
            r'<div class="template-title">\1</div>'
            r'<div class="template-content">\2</div>'
            r'</div>',
            text, 
            flags=re.DOTALL
        )
        
        # 각 템플릿 내에서 예시와 프롬프트 순서 바꾸기
        # 예시: 로 시작하는 부분을 <div class="example-label">예시:</div><div class="example-content">내용</div> 로 변환
        text = re.sub(
            r'<div class="template-content">(.*?)예시:(.*?)프롬프트:(.*?)</div>',
            r'<div class="template-content"><div class="example-label">예시:</div><div class="example-content">\2</div><div class="prompt-label">프롬프트:</div><div class="prompt-content">\3</div></div>',
            text,
            flags=re.DOTALL
        )
        
        # 마지막 문장 스타일 적용 (약간의 여백과 이탤릭체)
        if "다음 주에는" in text:
            text = re.sub(r'(다음 주에는.*?\.)', r'<div class="tip-footer">\1</div>', text)
    
    # 제목 변환 (# 제목)
    text = re.sub(r'^# (.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    
    # 굵은 텍스트 (**텍스트**)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # 기울임 텍스트 (*텍스트*)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # 링크 변환 ([텍스트](URL))
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    
    # 일반적인 글머리 기호 (- 항목) 처리 (이미 처리된 AT/DT 팁 예시는 제외)
    if "prompt-template" not in text:
        text = re.sub(r'^\- (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # 색상 표시 강조 - 주요 소식에서 사용할 수 있는 색상 강조 기능
    text = re.sub(r'\[강조\](.*?)\[\/강조\]', r'<span style="color:#e74c3c; font-weight:bold;">\1</span>', text)
    
    # 줄바꿈을 <br>과 <p>로 변환
    paragraphs = text.split('\n\n')
    for i, paragraph in enumerate(paragraphs):
        if not paragraph.startswith('<h') and not paragraph.startswith('<li') and not paragraph.startswith('<div'):
            # 이미 HTML 태그가 아닌 경우만 <p> 태그로 감싸기
            if '<li>' in paragraph:
                # 리스트 항목이 있는 경우 <ul> 태그로 감싸기
                paragraph = f'<ul>{paragraph}</ul>'
            else:
                paragraph = f'<p>{paragraph}</p>'
        paragraphs[i] = paragraph.replace('\n', '<br>')
    
    return ''.join(paragraphs)

# NewsAPI를 사용하여 실시간 뉴스를 가져오는 함수
def fetch_real_time_news(api_key, query="AI digital transformation", days=7, language="en"):
    """
    NewsAPI를 사용하여 실시간 뉴스를 가져옵니다.
    무료 플랜은 최근 1개월(실제로는 더 짧을 수 있음) 데이터만 접근 가능합니다.
    """
    # 날짜 범위 계산 (API 제한으로 인해 기간을 줄임)
    end_date = datetime.now()
    # 무료 플랜 제한을 고려하여 기간을 줄임
    start_date = end_date - timedelta(days=min(days, 7))  # 최대 7일로 제한
    
    # NewsAPI 요청
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

# 네이버 API를 사용하여 뉴스를 가져오는 함수
def fetch_naver_news(client_id, client_secret, query, display=5, days=7):
    """
    네이버 검색 API를 사용하여 뉴스를 가져옵니다.
    최근 지정된 일수(기본 7일) 이내의 뉴스만 필터링합니다.
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": query,
        "display": 100,  # 더 많은 데이터를 가져와서 필터링 (최대 100개)
        "sort": "date"  # 최신순으로 정렬
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        result = response.json()
        
        # 최근 days일 내의 뉴스만 필터링
        filtered_items = []
        current_date = datetime.now()
        cutoff_date = current_date - timedelta(days=days)
        
        for item in result['items']:
            # 네이버 뉴스 API는 pubDate를 제공하지만 형식이 RFC 822 형식
            try:
                pub_date_str = item.get('pubDate')
                if pub_date_str:
                    pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                    pub_date = pub_date.replace(tzinfo=None)
                    
                    if pub_date >= cutoff_date:
                        filtered_items.append(item)
            except Exception:
                # 날짜 파싱에 실패하면 일단 포함시킴
                filtered_items.append(item)
        
        # display 개수만큼만 반환
        return filtered_items[:display]
    else:
        raise Exception(f"네이버 뉴스 가져오기 실패: {response.status_code} - {response.text}")

def fetch_ai_use_cases(naver_client_id, naver_client_secret, query="AI 활용사례", display=3, days=30):
    """
    네이버 검색 API를 사용하여 AI 활용사례를 가져옵니다.
    """
    url = "https://openapi.naver.com/v1/search/blog.json"  # 블로그 검색으로 변경
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    
    # 여러 소스에서 검색하기 위한 쿼리 구성
    search_queries = [
        f"{query} YouTube",
        f"{query} 기업",
        f"{query} 프롬프트"
    ]
    
    all_items = []
    
    for search_query in search_queries:
        params = {
            "query": search_query,
            "display": display,
            "sort": "date"  # 최신순으로 정렬
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                all_items.extend(result['items'])
            else:
                print(f"API 오류: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"검색 중 오류 발생: {str(e)}")
    
    # 중복 제거 (title 기준)
    unique_items = []
    unique_titles = set()
    
    for item in all_items:
        clean_title = item['title'].replace("<b>", "").replace("</b>", "")
        if clean_title not in unique_titles:
            unique_titles.add(clean_title)
            unique_items.append(item)
    
    # 최대 display 개수만큼만 반환
    return unique_items[:display]

def generate_ai_use_case_content(openai_api_key, use_case_data):
    """
    OpenAI를 사용하여 AI 활용사례 콘텐츠를 생성합니다.
    '사례 확인해보기→' 링크를 포함합니다.
    SOURCE_URL과 SOURCE_NAME 제거됨
    """
    if not openai_api_key or not use_case_data:
        # OpenAI API가 없거나 검색 결과가 없는 경우 기본 콘텐츠 반환
        return """
        <h2>ChatGPT를 활용한 코드 리팩토링 사례</h2>
        
        <p><strong>요약:</strong> 소프트웨어 개발팀이 레거시 코드를 현대화하는 과정에서 ChatGPT를 활용하여 코드 리팩토링 시간을 단축했습니다. 복잡한 코드를 분석하고 개선하는 작업에 AI의 도움을 받아 생산성이 크게 향상되었습니다.</p>
        
        <p><strong>단계별 방법:</strong></p>
        <ol>
          <li>레거시 코드를 ChatGPT에 제시하고 코드 구조와 문제점 분석 요청</li>
          <li>개선된 코드 구조와 디자인 패턴 제안받기</li>
          <li>코드 품질 향상을 위한 리팩토링 수행 (중복 제거, 모듈화 등)</li>
          <li>테스트 케이스 생성 및 디버깅 지원 요청</li>
        </ol>
        
        <p><strong>추천 프롬프트:</strong> "다음 코드를 분석하고 문제점을 찾아주세요. 그 후 모던 자바스크립트 관행과 디자인 패턴을 적용하여 리팩토링된 버전을 제공해주세요. 코드의 각 부분이 하는 일을 주석으로 설명하고, 리팩토링의 이유도 함께 설명해주세요."</p>
        
        <p style="text-align: right; margin-top: 15px;"><a href="https://github.com/features/copilot" target="_blank" style="color: #ff5722; text-decoration: none; font-weight: bold;">사례 확인해보기 →</a></p>
        <p style="font-size: 8pt; text-align: right; color: #666;">출처: GitHub Copilot</p>
        """
    
    # 선택된 활용사례 링크와 출처를 저장할 변수
    selected_source = ""
    selected_link = ""
    
    # 검색 데이터를 기반으로 OpenAI 프롬프트 구성
    use_case_info = "AI 활용사례 검색 결과:\n\n"
    
    for i, item in enumerate(use_case_data):
        # HTML 태그 제거
        title = item['title'].replace("<b>", "").replace("</b>", "")
        description = item['description'].replace("<b>", "").replace("</b>", "")
        
        use_case_info += f"{i+1}. 제목: {title}\n"
        use_case_info += f"   설명: {description}\n"
        use_case_info += f"   링크: {item['link']}\n"
        use_case_info += f"   블로그명: {item.get('bloggername', '알 수 없음')}\n\n"
    
    client = OpenAI(api_key=openai_api_key)
    
    try:
        prompt = f"""
        AIDT Weekly 뉴스레터의 'AI 활용사례' 섹션을 생성해주세요.
        아래는 검색된 실제 AI 활용사례 정보입니다:
        
        {use_case_info}
        
        위 검색 결과 중에서 가장 유용하고 구체적인 활용사례를 선택하여 다음 형식으로 내용을 작성해주세요:
        
        ## [활용사례 제목] - 제목은 1줄로 명확하게
        
        **요약:** 배경과 중요성을 2-3문장으로 간결하게 설명해주세요.
        
        **단계별 방법:** AI 솔루션을 상세히 설명합니다. 어떤 기술을 사용했는지, 어떻게 구현했는지, 특별한 접근 방식은 무엇이었는지 등을 포함하여 3~4줄로 작성해주세요.
        
        **추천 프롬프트:** 이 활용사례를 더 효과적으로 활용하기 위한 구체적이고 명확한 프롬프트 예시를 작성해주세요.
        
        모든 내용은 반드시 제공된 검색 결과에서만 추출해야 합니다. 가상의 정보나 사실이 아닌 내용은 절대 포함하지 마세요.
        내용은 마크다운 형식으로 작성해주세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "AI 디지털 트랜스포메이션 활용사례 콘텐츠 생성 전문가. 정확하고 구체적인 정보만 포함합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # 링크가 없는 경우 첫 번째 항목의 링크 사용
        if not selected_link and use_case_data:
            selected_link = use_case_data[0]['link']
            
        # 출처가 없는 경우 첫 번째 항목의 블로그명 사용
        if not selected_source and use_case_data:
            selected_source = use_case_data[0].get('bloggername', '출처 정보 없음')
        
        # 출처 표시와 링크 추가
        content_html = convert_markdown_to_html(content)
        content_html += f"""
        <p style="text-align: right; margin-top: 15px;"><a href="{selected_link}" target="_blank" style="color: #ff5722; text-decoration: none; font-weight: bold;">사례 확인해보기 →</a></p>
        <p style="font-size: 8pt; text-align: right; color: #666;">출처: {selected_source}</p>
        """
        
        return content_html
    except Exception as e:
        print(f"OpenAI API 오류: {str(e)}")
        # 오류 발생 시 기본 콘텐츠 반환
        return """
        <h2>AI를 활용한 고객 서비스 개선 사례</h2>
        
        <p><strong>요약:</strong> 고객 문의량이 많은 기업에서 AI 챗봇을 도입하여 상담원의 업무 부담을 줄이고 24시간 고객 지원을 가능하게 한 사례입니다. 반복적인 질문에 자동 응답하여 상담원이 복잡한 문의에 집중할 수 있게 되었습니다.</p>
        
        <p><strong>단계별 방법:</strong></p>
        <ol>
          <li>자주 묻는 질문(FAQ)과 기존 상담 데이터 수집 및 분석</li>
          <li>AI 모델 학습 및 챗봇 시스템 구축</li>
          <li>사용자 피드백을 통한 지속적인 개선</li>
          <li>복잡한 문의는 인간 상담원에게 자동 전달되는 시스템 구현</li>
        </ol>
        
        <p><strong>추천 프롬프트:</strong> "고객 서비스용 AI 챗봇을 만들기 위해, 우리 회사의 자주 묻는 질문 목록을 분석하고 효과적인 응답 템플릿을 제안해주세요. 각 질문 유형별로 챗봇이 어떻게 응답해야 할지 예시를 포함해주세요."</p>
        
        <p style="text-align: right; margin-top: 15px;"><a href="https://www.ibm.com/watson/ai-customer-service" target="_blank" style="color: #ff5722; text-decoration: none; font-weight: bold;">사례 확인해보기 →</a></p>
        <p style="font-size: 8pt; text-align: right; color: #666;">출처: IBM Watson</p>
        """

# 통합된 뉴스레터 생성 함수
def generate_combined_newsletter(openai_api_key, news_api_key, naver_client_id, naver_client_secret, 
                             news_query_en, news_query_ko, language="en", custom_success_story=None, 
                             issue_num=1, highlight_settings=None):
    """OpenAI, NewsAPI, 네이버 API를 모두 사용하여 통합된 뉴스레터를 생성합니다.
    사용 가능한 API만 활용합니다."""
    
    date = datetime.now().strftime('%Y년 %m월 %d일')
    issue_number = issue_num
    
    # 뉴스레터 콘텐츠를 저장할 딕셔너리
    newsletter_content = {}
    
    # OpenAI API 관련 작업
    if openai_api_key:
        try:
            # OpenAI 클라이언트 초기화
            os.environ["OPENAI_API_KEY"] = openai_api_key
            client = OpenAI(api_key=openai_api_key)
            
            # 현재 주차 계산 (이슈 번호를 주차로 사용)
            current_week = issue_num
            
            # AI 팁 주제 데이터베이스 - 여러 주제를 순환하여 제공
            ai_tip_topics = [
                "효과적인 프롬프트 작성의 기본 원칙 (Chain of Thought, Chain of Draft)",
                "특정 업무별 최적의 프롬프트 템플릿",
                "AI를 활용한 데이터 분석 프롬프트 기법",
                "창의적 작업을 위한 AI 프롬프트 전략",
                "AI와 협업하여 문제 해결하기",
                "다양한 AI 도구 활용법 비교",
                "업무 자동화를 위한 AI 프롬프트 설계",
                "AI를 활용한 의사결정 지원 기법"
            ]
            
            # 현재 주차에 해당하는 주제 선택 (순환)
            current_topic = ai_tip_topics[(current_week - 1) % len(ai_tip_topics)]
            
            # NewsAPI로 뉴스 가져오기 (있는 경우에만)
            news_info = ""
            openai_news_info = ""
            
            if news_api_key:
                try:
                    # 일반 뉴스 가져오기
                    news_articles = fetch_real_time_news(news_api_key, query=news_query_en, days=7, language=language)
                    top_news = news_articles[:5]
                    
                    news_info = "최근 7일 내 수집된 실제 뉴스 기사:\n\n"
                    for i, article in enumerate(top_news):
                        pub_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')).strftime('%Y년 %m월 %d일')
                        news_info += f"{i+1}. 제목: {article['title']}\n"
                        news_info += f"   날짜: {pub_date}\n"
                        news_info += f"   요약: {article['description']}\n"
                        news_info += f"   출처: {article['source']['name']}\n"
                        news_info += f"   URL: {article['url']}\n\n"
                    
                    # OpenAI 관련 뉴스 가져오기
                    openai_articles = fetch_real_time_news(news_api_key, query="OpenAI", days=7, language=language)
                    top_openai_news = openai_articles[:3]
                    
                    openai_news_info = "최근 7일 내 수집된 OpenAI 관련 뉴스 기사:\n\n"
                    for i, article in enumerate(top_openai_news):
                        pub_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')).strftime('%Y년 %m월 %d일')
                        openai_news_info += f"{i+1}. 제목: {article['title']}\n"
                        openai_news_info += f"   날짜: {pub_date}\n"
                        openai_news_info += f"   요약: {article['description']}\n"
                        openai_news_info += f"   출처: {article['source']['name']}\n"
                        openai_news_info += f"   URL: {article['url']}\n\n"
                except Exception as e:
                    st.error(f"News API 오류: {str(e)}")
                    news_info = "NewsAPI에서 뉴스를 가져오는데 실패했습니다."
                    openai_news_info = "NewsAPI에서 OpenAI 관련 뉴스를 가져오는데 실패했습니다."
            
            # OpenAI를 사용하여 콘텐츠 생성
            prompts = {
                'main_news': f"""
                AIDT Weekly 뉴스레터의 '주요 소식' 섹션을 생성해주세요.
                오늘 날짜는 {date}입니다. 아래는 두 종류의 뉴스 기사입니다:
                
                === OpenAI 관련 뉴스 ===
                {openai_news_info}
                
                === 일반 뉴스 ===
                {news_info}
                
                총 2개의 주요 소식을 다음 형식으로 작성해주세요:
                
                1. 먼저 OpenAI 관련 뉴스에서 가장 중요하고 관련성 높은 1개의 소식을 선택하여 작성하세요.
                2. 그 다음 일반 뉴스에서 가장 중요하고 관련성 높은 1개의 소식을 선택하여 작성하세요.
                
                각 소식은 다음 형식으로 작성해주세요:
                ## [주제]의 [핵심 강점/특징]은 [주목할만합니다/확인됐습니다/중요합니다].
                
                간략한 내용을 1-2문장으로 작성하세요. 내용은 특정 기술이나 서비스, 기업의 최신 소식을 다루고, 
                핵심 내용만 포함해주세요. 그리고 왜 중요한지를 강조해주세요.
                
                구체적인 수치나 인용구가 있다면 추가해주세요.
                
                각 소식의 마지막에는 뉴스 기사의 발행일과 출처를 반드시 "[출처 제목](출처 URL)" 형식으로 포함하세요.
                
                모든 주제는 반드시 제공된 실제 뉴스 기사에서만 추출해야 합니다. 가상의 정보나 사실이 아닌 내용은 절대 포함하지 마세요.
                각 소식 사이에 충분한 공백을 두어 가독성을 높여주세요.
                """ if news_api_key else "뉴스 API 키가 제공되지 않아 글로벌 뉴스를 가져올 수 없습니다.",

                'aidt_tips': f"""
                AIDT Weekly 뉴스레터의 '이번 주 AT/DT 팁' 섹션을 생성해주세요.
                
                이번 주 팁 주제는 "{current_topic}"입니다.
                
                이 주제에 대해 다음 형식으로 실용적인 팁을 작성해주세요:
                
                ## 이번 주 팁: [주제에 맞는 구체적인 팁 제목]
                
                팁에 대한 배경과 중요성을 2-3문장으로 간결하게 설명해주세요. AI 기본기와 관련된 내용을 포함하세요.
                특히, 영어 용어는 한글로 번역하지 말고 그대로 사용해주세요 (예: "Chain of Thought", "Chain of Draft").
                
                **핵심 프롬프트 예시:**
                - 첫 번째 프롬프트 템플릿 (Chain of Thought 활용):
                  예시: [이 문제/작업에 대한 실제 예시를 제시하세요]
                  프롬프트: [구체적인 Chain of Thought 프롬프트 템플릿을 작성하세요]
                
                - 두 번째 프롬프트 템플릿 (Chain of Draft 활용):
                  예시: [이 문제/작업에 대한 실제 예시를 제시하세요]
                  프롬프트: [구체적인 Chain of Draft 프롬프트 템플릿을 작성하세요]
                
                - 세 번째 프롬프트 템플릿 (Chain of Thought와 Chain of Draft 결합):
                  예시: [이 문제/작업에 대한 실제 예시를 제시하세요]
                  프롬프트: [두 기법을 결합한 프롬프트 템플릿을 작성하세요]
                
                이 팁을 활용했을 때의 업무 효율성 향상이나 결과물 품질 개선 등 구체적인 이점을 한 문장으로 작성해주세요.
                
                다음 주에는 다른 AI 기본기 팁을 알려드리겠습니다.
                """,

                'success_story': """
                AIDT Weekly 뉴스레터의 '성공 사례' 섹션을 생성해주세요.
                한국 기업 사례 1개와 외국 기업 사례 1개를 생성해야 합니다.
                각 사례는 제목과 3개의 단락으로 구성되어야 합니다.
                각 단락은 3~4줄로 구성하고, 구체적인 내용과 핵심 정보를 포함해야 합니다.
                단락 사이에는 한 줄을 띄워서 가독성을 높여주세요.
                
                형식:
                
                ## [한국 기업명]의 AI 혁신 사례
                
                첫 번째 단락에서는 기업이 직면한 문제와 배경을 상세히 설명합니다. 구체적인 수치나 상황을 포함하여 3~4줄로 작성해주세요. 이 부분에서는 독자가 왜 이 기업이 AI 솔루션을 필요로 했는지 이해할 수 있도록 해주세요.
                
                두 번째 단락에서는 기업이 도입한 AI 솔루션을 상세히 설명합니다. 어떤 기술을 사용했는지, 어떻게 구현했는지, 특별한 접근 방식은 무엇이었는지 등을 포함하여 3~4줄로 작성해주세요.
                
                세 번째 단락에서는 AI 도입 후 얻은 구체적인 성과와 결과를 설명합니다. 가능한 한 정량적인 수치(비용 절감, 효율성 증가, 고객 만족도 향상 등)를 포함하여 3~4줄로 작성해주세요.
                
                ## [외국 기업명]의 AI 혁신 사례
                
                첫 번째 단락에서는 기업이 직면한 문제와 배경을 상세히 설명합니다. 구체적인 수치나 상황을 포함하여 3~4줄로 작성해주세요. 이 부분에서는 독자가 왜 이 기업이 AI 솔루션을 필요로 했는지 이해할 수 있도록 해주세요.
                
                두 번째 단락에서는 기업이 도입한 AI 솔루션을 상세히 설명합니다. 어떤 기술을 사용했는지, 어떻게 구현했는지, 특별한 접근 방식은 무엇이었는지 등을 포함하여 3~4줄로 작성해주세요.
                
                세 번째 단락에서는 AI 도입 후 얻은 구체적인 성과와 결과를 설명합니다. 가능한 한 정량적인 수치(비용 절감, 효율성 증가, 고객 만족도 향상 등)를 포함하여 3~4줄로 작성해주세요.
                """
            }
            
            # OpenAI를 사용하여 콘텐츠 생성
            for section, prompt in prompts.items():
                try:
                    # 사용자가 입력한 성공 사례가 있으면 생성 건너뛰기
                    if section == 'success_story' and custom_success_story:
                        newsletter_content[section] = convert_markdown_to_html(custom_success_story)
                        continue
                    
                    # 전역 뉴스가 없는 경우 생성하지 않음
                    if section == 'main_news' and not news_api_key:
                        newsletter_content[section] = f"<p>News API 키가 제공되지 않아 글로벌 뉴스를 가져올 수 없습니다.</p>"
                        continue
                        
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
        except Exception as e:
            st.error(f"OpenAI API 오류: {str(e)}")
            # OpenAI API 실패했을 때 기본 내용 추가
            newsletter_content['aidt_tips'] = get_default_tips_content()
            newsletter_content['success_story'] = get_default_success_story()
    else:
        # OpenAI API 키가 없는 경우 기본 콘텐츠 사용
        newsletter_content['aidt_tips'] = get_default_tips_content()
        newsletter_content['success_story'] = get_default_success_story()
    
    # 네이버 API 관련 작업
    if naver_client_id and naver_client_secret:
        try:
            # 네이버 뉴스 가져오기 - 일반 AI 뉴스
            ai_news_items = fetch_naver_news(naver_client_id, naver_client_secret, news_query_ko, display=2, days=7)
            
            # 네이버 뉴스 섹션 콘텐츠 생성
            naver_news_content = "<h2>국내 AI 주요 소식</h2>"
            
            if not ai_news_items:
                naver_news_content += "<p>최근 7일 이내의 관련 뉴스가 없습니다.</p>"
            else:
                for i, article in enumerate(ai_news_items):
                    # HTML 태그 제거
                    title = article['title'].replace("<b>", "").replace("</b>", "")
                    description = article['description'].replace("<b>", "").replace("</b>", "")
                    
                    # 날짜 표시 추가
                    pub_date_str = article.get('pubDate', '')
                    pub_date_display = ""
                    try:
                        if pub_date_str:
                            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                            pub_date_display = pub_date.strftime('%Y년 %m월 %d일')
                    except Exception:
                        pub_date_display = "날짜 정보 없음"
                    
                    naver_news_content += f"<h3>{title}</h3>"
                    naver_news_content += f"<p><small>게시일: {pub_date_display}</small></p>"
                    naver_news_content += f"<p>{description}</p>"
                    naver_news_content += f"<p><a href='{article['link']}' target='_blank'>원문 보기</a> | 출처: {article.get('originallink', article['link'])}</p>"
                    
                    if i < len(ai_news_items) - 1:  # 마지막 뉴스가 아닌 경우 구분선 추가
                        naver_news_content += "<hr>"
            
            newsletter_content['naver_news'] = naver_news_content
            
            # 네이버 AI 트렌드 뉴스 가져오기
            trend_news_items = fetch_naver_news(naver_client_id, naver_client_secret, "AI 트렌드", display=2, days=7)
            
            # AI 트렌드 섹션 콘텐츠 생성
            trend_news_content = "<h2>국내 AI 트렌드 소식</h2>"
            
            if not trend_news_items:
                trend_news_content += "<p>최근 7일 이내의 AI 트렌드 관련 뉴스가 없습니다.</p>"
            else:
                for i, article in enumerate(trend_news_items):
                    # HTML 태그 제거
                    title = article['title'].replace("<b>", "").replace("</b>", "")
                    description = article['description'].replace("<b>", "").replace("</b>", "")
                    
                    # 날짜 표시 추가
                    pub_date_str = article.get('pubDate', '')
                    pub_date_display = ""
                    try:
                        if pub_date_str:
                            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                            pub_date_display = pub_date.strftime('%Y년 %m월 %d일')
                    except Exception:
                        pub_date_display = "날짜 정보 없음"
                    
                    trend_news_content += f"<h3>{title}</h3>"
                    trend_news_content += f"<p><small>게시일: {pub_date_display}</small></p>"
                    trend_news_content += f"<p>{description}</p>"
                    trend_news_content += f"<p><a href='{article['link']}' target='_blank'>원문 보기</a> | 출처: {article.get('originallink', article['link'])}</p>"
                    
                    if i < len(trend_news_items) - 1:  # 마지막 뉴스가 아닌 경우 구분선 추가
                        trend_news_content += "<hr>"
            
            newsletter_content['naver_trends'] = trend_news_content
            
            # AI 활용사례 가져오기
            try:
                # AI 활용사례 검색
                ai_use_cases = fetch_ai_use_cases(naver_client_id, naver_client_secret, "AI 활용사례", display=3, days=30)
                
                # AI 활용사례 콘텐츠 생성
                ai_use_case_content = generate_ai_use_case_content(openai_api_key, ai_use_cases)
                
                newsletter_content['ai_use_case'] = ai_use_case_content
            except Exception as e:
                st.error(f"AI 활용사례 가져오기 오류: {str(e)}")
                newsletter_content['ai_use_case'] = get_default_ai_use_case()
            
        except Exception as e:
            st.error(f"네이버 API 오류: {str(e)}")
            newsletter_content['naver_news'] = f"<p>네이버 뉴스를 가져오는 중 오류가 발생했습니다: {str(e)}</p>"
            newsletter_content['naver_trends'] = f"<p>네이버 AI 트렌드 뉴스를 가져오는 중 오류가 발생했습니다: {str(e)}</p>"
    else:
        # 네이버 API가 없는 경우 AI 활용사례 기본 콘텐츠 추가
        newsletter_content['ai_use_case'] = get_default_ai_use_case()
    
    # 하이라이트 설정 기본값
    if highlight_settings is None:
        highlight_settings = {
            "title": "중부Infra AT/DT 뉴스레터 개시",
            "subtitle": "AI, 어떻게 시작할지 막막하다면?",
            "link_text": "AT/DT 추진방향 →",
            "link_url": "#"
        }
    
    # HTML 템플릿 생성
    html_content = generate_combined_html_template(newsletter_content, issue_number, date, highlight_settings)
    return html_content

# 기본 콘텐츠를 위한 헬퍼 함수들
def get_default_tips_content():
    """기본 AT/DT 팁 콘텐츠 반환"""
    return """
    <div class="tip-title">이번 주 팁: 효과적인 프롬프트 작성의 기본 원칙</div>
    
    <p>AI를 더 효과적으로 활용하기 위해서는 명확하고 구체적인 프롬프트를 작성하는 것이 중요합니다. Chain of Thought와 Chain of Draft 기법을 활용하면 더 정확한 결과를 얻을 수 있습니다.</p>
    
    <div class="prompt-examples-title">핵심 프롬프트 예시:</div>
    
    <div class="prompt-template">
    <div class="template-title">- 첫 번째 프롬프트 템플릿 (Chain of Thought 활용):</div>
    <div class="template-content">
    <div class="example-label">예시:</div>
    <div class="example-content">이 보고서를 요약해주세요.</div>
    <div class="prompt-label">프롬프트:</div>
    <div class="prompt-content">이 보고서의 핵심 주제와 중요한 발견 사항을 파악하고, 주요 결론을 도출해주세요. 단계별로 생각하며 요약해주세요.</div>
    </div>
    </div>
    
    <div class="prompt-template">
    <div class="template-title">- 두 번째 프롬프트 템플릿 (Chain of Draft 활용):</div>
    <div class="template-content">
    <div class="example-label">예시:</div>
    <div class="example-content">이메일을 작성해주세요.</div>
    <div class="prompt-label">프롬프트:</div>
    <div class="prompt-content">고객에게 보낼 이메일을 작성해주세요. 먼저 초안을 작성하고, 그 다음 더 공손하고 전문적인 어조로 다듬어주세요.</div>
    </div>
    </div>
    
    <div class="tip-footer">다음 주에는 특정 업무별 최적의 프롬프트 템플릿에 대해 알려드리겠습니다.</div>
    """

def get_default_success_story():
    """기본 성공 사례 콘텐츠 반환"""
    return """
    <h2>삼성전자의 AI 혁신 사례</h2>
    
    <p>삼성전자는 생산 라인의 불량품 검출률을 높이기 위해 AI 비전 시스템 도입을 결정했습니다. 기존의 수동 검사 방식으로는 약 92%의 정확도를 보였으며, 검사 시간이 길어 생산성 저하의 원인이 되었습니다. 특히 미세한 결함을 감지하는 데 어려움이 있었습니다.</p>
    
    <p>삼성전자는 딥러닝 기반의 컴퓨터 비전 시스템을 구축하고, 수십만 장의 정상 및 불량 제품 이미지로 AI 모델을 학습시켰습니다. 이 시스템은 실시간으로 제품을 스캔하고 결함을 자동으로 식별하며, 결함의 유형과 심각성까지 분류할 수 있도록 설계되었습니다.</p>
    
    <p>AI 시스템 도입 후 불량품 검출 정확도가 92%에서 98.5%로 향상되었으며, 검사 시간은 60% 단축되었습니다. 이로 인해 연간 약 150억 원의 비용 절감 효과를 얻었으며, 제품 품질 향상으로 고객 반품률도 15% 감소했습니다.</p>
    
    <h2>Google의 AI 혁신 사례</h2>
    
    <p>Google은 데이터 센터의 에너지 효율성을 개선하기 위해 DeepMind AI 시스템을 도입했습니다. 데이터 센터는 전 세계 전력 소비의 상당 부분을 차지하며, 냉각 시스템이 특히 많은 에너지를 소비합니다. 기존의 냉각 시스템은 수동 설정과 기본 알고리즘에 의존하여 최적화가 어려웠습니다.</p>
    
    <p>Google은 DeepMind의 강화학습 AI 시스템을 활용하여 수천 개의 센서 데이터를 분석하고 냉각 시스템을 자동으로 최적화하는 솔루션을 개발했습니다. 이 AI는 외부 온도, 서버 부하, 전력 사용량 등 다양한 변수를 고려하여 실시간으로 냉각 시스템을 조정합니다.</p>
    
    <p>AI 시스템 도입 결과, Google 데이터 센터의 냉각 에너지 소비가 약 40% 감소했으며, 전체 PUE(전력 사용 효율성)가 15% 개선되었습니다. 이는 연간 수백만 달러의 비용 절감과 탄소 배출량 감소로 이어졌으며, 다른 데이터 센터에도 적용 가능한 모델을 제시했습니다.</p>
    """

def get_default_ai_use_case():
    """기본 AI 활용사례 콘텐츠 반환"""
    return """
    <h2>AI를 활용한 문서 요약 및 번역 사례</h2>
    
    <p><strong>요약:</strong> 다국적 기업에서 여러 언어로 된 보고서와 문서를 효율적으로 처리하기 위해 AI 요약 및 번역 시스템을 도입했습니다. 이를 통해 문서 처리 시간을 80% 단축하고 국가 간 정보 공유를 원활하게 개선했습니다.</p>
    
    <p><strong>단계별 방법:</strong></p>
    <ol>
      <li>GPT 기반 문서 요약 시스템 구축으로 긴 문서의 핵심 내용 추출</li>
      <li>다국어 번역 모델을 통합하여 10개 이상 언어 간 번역 지원</li>
      <li>전문 용어 사전을 구축하여 산업 특화 번역 정확도 향상</li>
      <li>문서 형식을 유지하며 요약 및 번역 결과를 원본과 함께 제공</li>
    </ol>
    
    <p><strong>추천 프롬프트:</strong> "다음 기술 보고서를 3가지 핵심 포인트로 요약하고, 각 포인트에 대한 간략한 설명을 추가해주세요. 그 후 요약된 내용을 [대상 언어]로 번역해주세요. 산업 용어는 정확하게 번역하고, 번역된 용어 옆에 영어 원문을 괄호 안에 표기해주세요."</p>
    
    <p style="text-align: right; margin-top: 15px;"><a href="https://www.deepl.com" target="_blank" style="color: #ff5722; text-decoration: none; font-weight: bold;">사례 확인해보기 →</a></p>
    <p style="font-size: 8pt; text-align: right; color: #666;">출처: DeepL 사례연구</p>
    """        

# 통합된 뉴스레터를 위한 HTML 템플릿 생성 함수
def generate_combined_html_template(newsletter_content, issue_number, date, highlight_settings):
    """세 가지 API를 모두 사용한 뉴스레터 HTML 템플릿을 생성합니다."""
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
                line-height: 1.5;
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
                background-color: #333333;
                color: white;
                padding: 15px 20px;
                text-align: left;
            }}
            .title {{
                margin: 0;
                font-size: 20px;
                font-weight: bold;
            }}
            .issue-date {{
                margin-top: 5px;
                font-size: 10pt;
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
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
                background-color: #3e3e3e;
                padding: 8px 10px;
                border-radius: 4px;
            }}
            .section-icon {{
                margin-right: 8px;
            }}
            h2, h3 {{
                font-size: 14px;
                margin-bottom: 5px;
                color: #333333;
            }}
            .main-news h2 {{
                color: #ff5722;
                font-size: 14px;
                margin-top: 15px;
                margin-bottom: 5px;
                border-bottom: none;
                padding-bottom: 0;
            }}
            .main-news a {{
                color: #ff5722;
                text-decoration: none;
            }}
            .main-news a:hover {{
                text-decoration: underline;
            }}
            .main-news p, .success-case p, p, li {{
                font-size: 10pt;
                margin: 0 0 8px;
            }}
            ul {{
                padding-left: 20px;
                margin-top: 5px;
                margin-bottom: 8px;
            }}
            li {{
                margin-bottom: 3px;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 10px;
                text-align: center;
                font-size: 9pt;
                color: #666;
            }}
            .section-container {{
                padding: 0 15px;
            }}
            .highlight-box {{
                background-color: #fff9f5;
                border: 1px solid #ffe0cc;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0;
            }}
            .highlight-title {{
                color: #ff5722;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
                text-align: center;
            }}
            .highlight-subtitle {{
                color: #666;
                font-size: 12px;
                text-align: center;
                margin-bottom: 15px;
            }}
            
            /* AT/DT 팁 섹션 스타일 */
            .aidt-tips {{
                font-size: 10pt;
            }}

            .tip-title {{
                background-color: #f2f2f2;
                padding: 8px 10px;
                margin-bottom: 10px;
                border-radius: 4px;
                font-weight: bold;
            }}

            .prompt-examples-title {{
                background-color: #f2f2f2;
                padding: 8px 10px;
                margin: 15px 0 10px 0;
                border-radius: 4px;
                font-weight: bold;
            }}

            /* 프롬프트 템플릿 스타일 */
            .prompt-template {{
                margin-bottom: 20px; /* 템플릿 간 간격 */
            }}

            .template-title {{
                color: #ff5722; /* 제목 색상 - 오렌지 계열 */
                font-weight: bold;
                margin-bottom: 0; /* 제목과 내용 사이 간격 없음 */
                padding: 0;
            }}

            .template-content {{
                margin-left: 15px;
                margin-bottom: 10px; /* 내용 아래 여백 추가 */
            }}

            /* 예시와 프롬프트 스타일 */
            .example-label, .prompt-label {{
                font-weight: bold;
                margin-top: 5px;
                color: #333; /* 이미지와 일치하는 색상 */
            }}

            .example-content, .prompt-content {{
                margin-left: 15px;
                line-height: 1.3; /* 내용 줄간격 약간 줄임 */
                margin-bottom: 8px; /* 내용 하단 여백 증가 */
                color: #333; /* 이미지와 일치하는 색상 */
            }}

            .tip-footer {{
                margin-top: 15px;
                font-style: italic;
                color: #666; /* 이미지와 일치하는 색상 */
            }}
            
            /* 네이버 API 섹션 스타일 - 검은색으로 변경 */
            .naver-section {{
                background-color: #f8f8ff; /* 연한 파란색 배경 */
                border-radius: 4px;
                padding: 10px;
                margin-bottom: 15px;
            }}
            
            .naver-section h2, .naver-section h3 {{
                color: #333333; /* 검은색으로 변경 */
            }}
            
            /* AI 활용사례 섹션 스타일 */
            .section ol {{
                margin-left: 20px;
                padding-left: 0;
            }}
            .section ol li {{
                margin-bottom: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">중부Infra AT/DT Weekly</div>
                <div class="issue-info">제{issue_number}호 | {date}</div>
            </div>
            
            <div class="content">
                <div class="newsletter-intro">
                    <p>중부Infra AT/DT 뉴스레터는 모두가 AI발전 속도에 뒤쳐지지 않고 업무에 적용할 수 있도록 가장 흥미로운 AI 활용법을 전합니다.</p>
                </div>
                
                <div class="highlight-box">
                    <div class="highlight-title">{highlight_settings['title']}</div>
                    <div class="highlight-subtitle">{highlight_settings['subtitle']}</div>
                    <p style="text-align: right; margin-top: 5px; font-size: 9pt;"><a href="{highlight_settings['link_url']}" style="color: #ff5722;">{highlight_settings['link_text']}</a></p>
                </div>
                
                <!-- 글로벌 AI 뉴스 (OpenAI + NewsAPI) 섹션 -->
                {f'''
                <div class="section">
                    <div class="section-title">글로벌 AI 뉴스</div>
                    <div class="section-container main-news">
                        {newsletter_content.get('main_news', '<p>글로벌 AI 뉴스를 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                ''' if 'main_news' in newsletter_content else ""}
                
                <!-- 네이버 API 섹션 (색상 변경) -->
                {f'''
                <div class="section">
                    <div class="section-title">국내 AI 뉴스</div>
                    <div class="section-container main-news naver-section">
                        {newsletter_content.get('naver_news', '<p>국내 AI 뉴스를 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                ''' if 'naver_news' in newsletter_content else ""}
                
                <div class="section">
                    <div class="section-title">이번 주 AT/DT 팁</div>
                    <div class="section-container aidt-tips">
                        {newsletter_content.get('aidt_tips', '<p>AT/DT 팁을 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                
                <!-- AI 활용사례 섹션 (새로 추가) -->
                <div class="section">
                    <div class="section-title">AI 활용사례</div>
                    <div class="section-container">
                        {newsletter_content.get('ai_use_case', '<p>AI 활용사례를 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                
                <div class="section success-case">
                    <div class="section-title">성공 사례</div>
                    <div class="section-container">
                        {newsletter_content.get('success_story', '<p>성공 사례를 불러올 수 없습니다.</p>')}
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} 중부Infra All rights reserved. | 뉴스레터 구독에 감사드립니다.</p>
                <p>문의사항이나 제안이 있으시면 언제든지 연락해 주세요^^.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

def create_download_link(html_content, filename):
    """HTML 콘텐츠를 다운로드할 수 있는 링크를 생성합니다."""
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #ff5722; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'
    return href

def main():
    st.title("중부Infra AT/DT 뉴스레터 생성기")
    st.write("OpenAI, NewsAPI, 네이버 API를 활용하여 AI 디지털 트랜스포메이션 관련 뉴스레터를 자동으로 생성합니다.")
    
    # API 키 입력
    with st.expander("API 키 설정", expanded=True):
        st.info("모든 API의 키 정보를 입력하세요. 사용 가능한 API만 결과에 포함됩니다.")
        col1, col2 = st.columns(2)
        with col1:
            openai_api_key = st.text_input("OpenAI API 키 입력", type="password")
            news_api_key = st.text_input("News API 키 입력", type="password")
        with col2:
            naver_client_id = st.text_input("네이버 Client ID 입력", type="password")
            naver_client_secret = st.text_input("네이버 Client Secret 입력", type="password")
    
    # 뉴스레터 기본 설정
    with st.expander("뉴스레터 기본 설정", expanded=True):
        issue_number = st.number_input("뉴스레터 호수", min_value=1, value=1, step=1)
        
        # 뉴스 검색 설정
        news_query_en = st.text_input(
            "NewsAPI 검색어 (영어)", 
            value="Telecommunication AND AI digital transformation AND artificial intelligence",
            help="뉴스 API 검색어를 입력하세요. OR, AND 등의 연산자를 사용할 수 있습니다."
        )
        
        language = st.selectbox(
            "NewsAPI 뉴스 언어", 
            options=["en", "ko", "ja", "zh", "fr", "de"],
            format_func=lambda x: {"en": "영어", "ko": "한국어", "ja": "일본어", "zh": "중국어", "fr": "프랑스어", "de": "독일어"}[x],
            help="뉴스 검색 결과의 언어를 선택하세요."
        )
        
        st.info("⚠️ 참고: NewsAPI 무료 플랜은 약 7일 이내의 최신 뉴스만 조회할 수 있습니다.")
        
        news_query_ko = st.text_input(
            "네이버 검색어 (한글)", 
            value="AI 인공지능 디지털 트랜스포메이션",
            help="네이버 API 검색어를 입력하세요. 여러 키워드는 공백으로 구분됩니다."
        )
    
    # 하이라이트 박스 설정
    with st.expander("하이라이트 박스 설정"):
        highlight_title = st.text_input("하이라이트 제목", value="중부Infra AT/DT 뉴스레터 개시")
        highlight_subtitle = st.text_input("하이라이트 부제목", value="AI, 어떻게 시작할지 막막하다면?")
        highlight_link_text = st.text_input("링크 텍스트", value="AT/DT 추진방향 →")
        highlight_link_url = st.text_input("링크 URL", value="#")
    
    # 성공 사례 사용자 입력 옵션
    with st.expander("성공 사례 직접 입력"):
        use_custom_success = st.checkbox("성공 사례를 직접 입력하시겠습니까?")
        
        custom_success_story = None
        if use_custom_success:
            st.write("아래에 성공 사례를 마크다운 형식으로 입력하세요. 한국 기업과 외국 기업 사례 각 1개씩 포함해주세요.")
            st.write("각 사례는 3개의 단락으로 구성하고, 단락당 3-4줄로 작성해주세요.")
            st.write("예시 형식:")
            st.code("""
## 삼성전자의 AI 혁신 사례

첫 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

두 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

세 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

## Google의 AI 혁신 사례

첫 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

두 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.

세 번째 단락 내용을 여기에 작성하세요. 3-4줄로 구성하세요.
            """)
            
            custom_success_story = st.text_area("성공 사례 직접 입력", height=400)
    
    # 뉴스레터 생성 버튼
    if st.button("뉴스레터 생성"):
        # 필요한 API 키 확인
        if not openai_api_key and (not naver_client_id or not naver_client_secret):
            st.error("최소한 OpenAI API 키 또는 네이버 API 키(Client ID + Client Secret) 중 하나는 입력해야 합니다.")
            return
        
        if not openai_api_key:
            st.warning("OpenAI API 키가 제공되지 않아 OpenAI 생성 기능이 제한됩니다.")
        
        if not news_api_key:
            st.warning("News API 키가 제공되지 않아 글로벌 뉴스 검색 기능이 제한됩니다.")
            
        if not naver_client_id or not naver_client_secret:
            st.warning("네이버 API 키가 제공되지 않아 국내 뉴스 검색 기능이 제한됩니다.")
        
        with st.spinner("뉴스레터 생성 중... (약 1-2분 소요될 수 있습니다)"):
            try:
                # 하이라이트 설정 딕셔너리 생성
                highlight_settings = {
                    "title": highlight_title,
                    "subtitle": highlight_subtitle,
                    "link_text": highlight_link_text,
                    "link_url": highlight_link_url
                }
                
                # 사용 가능한 API로 뉴스레터 생성
                html_content = generate_combined_newsletter(
                    openai_api_key,
                    news_api_key,
                    naver_client_id,
                    naver_client_secret,
                    news_query_en,
                    news_query_ko,
                    language,
                    custom_success_story,
                    issue_number,
                    highlight_settings
                )
                
                filename = f"중부 ATDT Weekly-제{issue_number}호.html"
                
                st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()