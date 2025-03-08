import streamlit as st
from datetime import datetime, timedelta
import time
import base64
import os
import re
import requests
# import json  # 필요한 경우 추가

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

def fetch_naver_news(client_id, client_secret, query, display=5, days=7):
    """
    네이버 검색 API를 사용하여 뉴스를 가져옵니다.
    최근 지정된 일수(기본 7일) 이내의 뉴스만 필터링합니다.
    
    Parameters:
    client_id (str): 네이버 개발자 센터에서 발급받은 Client ID
    client_secret (str): 네이버 개발자 센터에서 발급받은 Client Secret
    query (str): 검색할 키워드
    display (int): 가져올 뉴스 수 (최대 100)
    days (int): 최근 몇 일 이내의 뉴스를 가져올지 지정
    
    Returns:
    list: 뉴스 기사 목록
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
            # 예: "Mon, 06 Mar 2023 10:30:00 +0900"
            try:
                pub_date_str = item.get('pubDate')
                if pub_date_str:
                    # RFC 822 형식 파싱
                    # 참고: %z는 Python 3.6+ 에서만 작동
                    pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                    # UTC 기준으로 비교하려면 tzinfo를 None으로 설정 (타임존 제거)
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

def generate_newsletter_naver_only(naver_client_id, naver_client_secret, news_query="AI 인공지능", issue_num=1, highlight_settings=None):
    """네이버 API만 사용하여 뉴스레터를 생성합니다."""
    
    date = datetime.now().strftime('%Y년 %m월 %d일')
    issue_number = issue_num
    
    # 하이라이트 설정 기본값
    if highlight_settings is None:
        highlight_settings = {
            "title": "중부Infra AT/DT 뉴스레터 개시",
            "subtitle": "AI, 어떻게 시작할지 막막하다면?",
            "link_text": "AT/DT 추진방향 →",
            "link_url": "#"
        }
    
    # 뉴스레터 콘텐츠를 저장할 딕셔너리
    newsletter_content = {}
    
    # 네이버 뉴스 가져오기 - 일반 AI 뉴스 (최근 7일 이내, 최신 2개)
    try:
        ai_news_items = fetch_naver_news(naver_client_id, naver_client_secret, news_query, display=2, days=7)
        
        # 주요 소식 섹션 콘텐츠 생성
        main_news_content = "<h2>이번 주 AI 주요 소식</h2>"
        
        if not ai_news_items:
            main_news_content += "<p>최근 7일 이내의 관련 뉴스가 없습니다.</p>"
        else:
            for i, article in enumerate(ai_news_items):  # 최신 2개 뉴스만 사용
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
                
                main_news_content += f"<h3>{title}</h3>"
                main_news_content += f"<p><small>게시일: {pub_date_display}</small></p>"
                main_news_content += f"<p>{description}</p>"
                main_news_content += f"<p><a href='{article['link']}' target='_blank'>원문 보기</a> | 출처: {article.get('originallink', article['link'])}</p>"
                
                if i < len(ai_news_items) - 1:  # 마지막 뉴스가 아닌 경우 구분선 추가
                    main_news_content += "<hr>"
        
        newsletter_content['main_news'] = main_news_content
        
    except Exception as e:
        newsletter_content['main_news'] = f"<p>뉴스를 가져오는 중 오류가 발생했습니다: {str(e)}</p>"
        st.error(f"네이버 API 오류: {str(e)}")
    
    # 네이버 AI 트렌드 뉴스 가져오기 (최근 7일 이내, 최신 2개)
    try:
        trend_news_items = fetch_naver_news(naver_client_id, naver_client_secret, "AI 트렌드", display=2, days=7)
        
        # AI 트렌드 섹션 콘텐츠 생성
        trend_news_content = "<h2>AI 트렌드 소식</h2>"
        
        if not trend_news_items:
            trend_news_content += "<p>최근 7일 이내의 AI 트렌드 관련 뉴스가 없습니다.</p>"
        else:
            for i, article in enumerate(trend_news_items):  # 최신 2개 뉴스만 사용
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
        
        newsletter_content['ai_trends'] = trend_news_content
        
    except Exception as e:
        newsletter_content['ai_trends'] = f"<p>AI 트렌드 뉴스를 가져오는 중 오류가 발생했습니다: {str(e)}</p>"
        st.error(f"네이버 API 오류: {str(e)}")
    
    # AT/DT 팁 섹션 (간단한 정적 콘텐츠로 대체)
    at_dt_tips_content = """
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
    
    newsletter_content['aidt_tips'] = at_dt_tips_content
    
    # 성공 사례 섹션 (간단한 정적 콘텐츠로 대체)
    success_story_content = """
    <h2>삼성전자의 AI 혁신 사례</h2>
    
    <p>삼성전자는 생산 라인의 불량품 검출률을 높이기 위해 AI 비전 시스템 도입을 결정했습니다. 기존의 수동 검사 방식으로는 약 92%의 정확도를 보였으며, 검사 시간이 길어 생산성 저하의 원인이 되었습니다. 특히 미세한 결함을 감지하는 데 어려움이 있었습니다.</p>
    
    <p>삼성전자는 딥러닝 기반의 컴퓨터 비전 시스템을 구축하고, 수십만 장의 정상 및 불량 제품 이미지로 AI 모델을 학습시켰습니다. 이 시스템은 실시간으로 제품을 스캔하고 결함을 자동으로 식별하며, 결함의 유형과 심각성까지 분류할 수 있도록 설계되었습니다.</p>
    
    <p>AI 시스템 도입 후 불량품 검출 정확도가 92%에서 98.5%로 향상되었으며, 검사 시간은 60% 단축되었습니다. 이로 인해 연간 약 150억 원의 비용 절감 효과를 얻었으며, 제품 품질 향상으로 고객 반품률도 15% 감소했습니다.</p>
    
    <h2>Google의 AI 혁신 사례</h2>
    
    <p>Google은 데이터 센터의 에너지 효율성을 개선하기 위해 DeepMind AI 시스템을 도입했습니다. 데이터 센터는 전 세계 전력 소비의 상당 부분을 차지하며, 냉각 시스템이 특히 많은 에너지를 소비합니다. 기존의 냉각 시스템은 수동 설정과 기본 알고리즘에 의존하여 최적화가 어려웠습니다.</p>
    
    <p>Google은 DeepMind의 강화학습 AI 시스템을 활용하여 수천 개의 센서 데이터를 분석하고 냉각 시스템을 자동으로 최적화하는 솔루션을 개발했습니다. 이 AI는 외부 온도, 서버 부하, 전력 사용량 등 다양한 변수를 고려하여 실시간으로 냉각 시스템을 조정합니다.</p>
    
    <p>AI 시스템 도입 결과, Google 데이터 센터의 냉각 에너지 소비가 약 40% 감소했으며, 전체 PUE(전력 사용 효율성)가 15% 개선되었습니다. 이는 연간 수백만 달러의 비용 절감과 탄소 배출량 감소로 이어졌으며, 다른 데이터 센터에도 적용 가능한 모델을 제시했습니다.</p>
    """
    
    newsletter_content['success_story'] = success_story_content
    
    # 다가오는 이벤트 섹션 (간단한 정적 콘텐츠로 대체)
    events_content = """
    <h2>AI 컨퍼런스 2025</h2>
    <ul>
      <li>날짜/시간: 2025년 4월 15-16일</li>
      <li>장소/형식: 서울 코엑스 / 오프라인 컨퍼런스</li>
      <li>내용: 최신 AI 기술 트렌드와 기업 적용 사례 공유</li>
    </ul>
    
    <h2>디지털 트랜스포메이션 웨비나</h2>
    <ul>
      <li>날짜/시간: 2025년 3월 25일 오후 2시</li>
      <li>장소/형식: 온라인 (Zoom)</li>
      <li>내용: 디지털 트랜스포메이션을 위한 실용적인 로드맵과 전략</li>
    </ul>
    """
    
    newsletter_content['events'] = events_content
    
    # Q&A 섹션 (간단한 정적 콘텐츠로 대체)
    qa_content = """
    <h2>우리 회사에 AI를 도입하려면 어떻게 시작해야 하나요?</h2>
    
    <p>AI 도입은 명확한 문제 정의부터 시작하세요. 먼저 AI로 해결할 수 있는 구체적인 비즈니스 문제를 파악하고, 작은 파일럿 프로젝트로 시작하는 것이 좋습니다. 내부 역량을 평가하고 필요한 경우 외부 전문가의 도움을 받으세요.</p>
    """
    
    newsletter_content['qa'] = qa_content

    # CSS 스타일과 HTML 템플릿
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
            }}

            /* 예시와 프롬프트 스타일 */
            .example-label, .prompt-label {{
                font-weight: bold;
                margin-top: 5px;
            }}

            .example-content, .prompt-content {{
                margin-left: 15px;
                line-height: 1.3; /* 내용 줄간격 약간 줄임 */
                margin-bottom: 5px;
            }}

            .tip-footer {{
                margin-top: 15px;
                font-style: italic;
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
                
                <div class="section">
                    <div class="section-title">주요 소식</div>
                    <div class="section-container main-news">
                        {newsletter_content['main_news']}
                    </div>
                </div>
                
                <!-- AI 트렌드 섹션 삭제 -->
                <!-- <div class="section">
                    <div class="section-title">AI 트렌드</div>
                    <div class="section-container main-news">
                        {newsletter_content['ai_trends']}
                    </div>
                </div> -->
                
                <div class="section">
                    <div class="section-title">이번 주 AT/DT 팁</div>
                    <div class="section-container aidt-tips">
                        {newsletter_content['aidt_tips']}
                    </div>
                </div>
                
                <div class="section success-case">
                    <div class="section-title">성공 사례</div>
                    <div class="section-container">
                        {newsletter_content['success_story']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">다가오는 이벤트</div>
                    <div class="section-container">
                        {newsletter_content['events']}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">질문 & 답변</div>
                    <div class="section-container">
                        {newsletter_content['qa']}
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

def create_download_link(html_content, filename):
    """HTML 콘텐츠를 다운로드할 수 있는 링크를 생성합니다."""
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #ff5722; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'
    return href

def main():
    st.title("AIDT 뉴스레터 생성기 (네이버 API 테스트 버전)")
    st.write("네이버 API를 활용하여 AI 디지털 트랜스포메이션 관련 뉴스레터를 자동으로 생성합니다.")
    
    # API 키 입력
    with st.expander("API 키 설정", expanded=True):
        st.info("네이버 개발자 센터에서 Client ID와 Client Secret을 발급받을 수 있습니다. (https://developers.naver.com)")
        
        # OpenAI API 키는 주석 처리
        # openai_api_key = st.text_input("OpenAI API 키 입력", type="password")
        # news_api_key = st.text_input("News API 키 입력", type="password")
        
        # 네이버 API 관련 입력 필드
        naver_client_id = st.text_input("네이버 Client ID 입력", type="password")
        naver_client_secret = st.text_input("네이버 Client Secret 입력", type="password")
    
    # 뉴스레터 기본 설정
    with st.expander("뉴스레터 기본 설정", expanded=True):
        issue_number = st.number_input("뉴스레터 호수", min_value=1, value=1, step=1)
        
        # 뉴스 검색 설정
        news_query = st.text_input(
            "뉴스 검색어", 
            value="AI 인공지능 디지털 트랜스포메이션",
            help="네이버 API 검색어를 입력하세요. 여러 키워드는 공백으로 구분됩니다."
        )
    
    # 하이라이트 박스 설정
    with st.expander("하이라이트 박스 설정"):
        highlight_title = st.text_input("하이라이트 제목", value="중부Infra AT/DT 뉴스레터 개시")
        highlight_subtitle = st.text_input("하이라이트 부제목", value="AI, 어떻게 시작할지 막막하다면?")
        highlight_link_text = st.text_input("링크 텍스트", value="AT/DT 추진방향 →")
        highlight_link_url = st.text_input("링크 URL", value="#")
    
    # 성공 사례 사용자 입력 옵션은 현재 비활성화 (정적 콘텐츠 사용)
    # with st.expander("성공 사례 직접 입력"):
    #     use_custom_success = st.checkbox("성공 사례를 직접 입력하시겠습니까?")
    #     
    #     custom_success_story = None
    #     if use_custom_success:
    #         st.write("아래에 성공 사례를 마크다운 형식으로 입력하세요.")
    #         custom_success_story = st.text_area("성공 사례 직접 입력", height=400)
    
    # 뉴스레터 생성 버튼
    if st.button("뉴스레터 생성"):
        if not naver_client_id or not naver_client_secret:
            st.error("네이버 Client ID와 Client Secret을 모두 입력하세요.")
        else:
            with st.spinner("뉴스레터 생성 중... (약 30초 소요될 수 있습니다)"):
                try:
                    # 하이라이트 설정 딕셔너리 생성
                    highlight_settings = {
                        "title": highlight_title,
                        "subtitle": highlight_subtitle,
                        "link_text": highlight_link_text,
                        "link_url": highlight_link_url
                    }
                    
                    html_content = generate_newsletter_naver_only(
                        naver_client_id, 
                        naver_client_secret,
                        news_query,
                        issue_number,
                        highlight_settings
                    )
                    filename = f"중부 ATDT Weekly-제{issue_number}호.html"
                    
                    st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                    st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                    
                    # 미리보기 제거 - 아래 코드 주석 처리
                    # st.subheader("생성된 뉴스레터")
                    # 
                    # # HTML 특수 문자 처리와 Content-Security-Policy 추가
                    # safe_html = html_content.replace('"', '\\"')
                    # iframe_html = f"""
                    # <iframe 
                    #     srcdoc="{safe_html}" 
                    #     width="100%" 
                    #     height="600" 
                    #     frameborder="0"
                    #     sandbox="allow-scripts"
                    # ></iframe>
                    # """
                    # st.markdown(iframe_html, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()