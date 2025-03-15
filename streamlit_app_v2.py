import streamlit as st
from openai import OpenAI
from datetime import datetime, timedelta
import base64
import os
import re
import requests
import pandas as pd
import hashlib
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="AI 기반 학습 뉴스레터 생성기",
    page_icon="📚",
    layout="wide"
)

# 캐시 시간 설정 (24시간)
CACHE_EXPIRATION = 60 * 60 * 24

# 세션 상태 초기화
if 'naver_api_configured' not in st.session_state:
    st.session_state.naver_api_configured = False
if 'youtube_api_configured' not in st.session_state:
    st.session_state.youtube_api_configured = False
if 'openai_api_configured' not in st.session_state:
    st.session_state.openai_api_configured = False
if 'news_api_configured' not in st.session_state:
    st.session_state.news_api_configured = False
if 'cache' not in st.session_state:
    st.session_state.cache = {}
if 'cache_timestamp' not in st.session_state:
    st.session_state.cache_timestamp = {}
if 'selected_materials' not in st.session_state:
    st.session_state.selected_materials = {}

# 검색 소스 설정
SEARCH_SOURCES = {
    "naver_blog": {"name": "네이버 블로그", "icon": "📝", "weight": 0.9, "lang": "ko"},
    "naver_web": {"name": "웹문서", "icon": "🌐", "weight": 1.0, "lang": "ko"},
    "naver_news": {"name": "뉴스", "icon": "📰", "weight": 0.7, "lang": "ko"},
    "youtube": {"name": "유튜브", "icon": "▶️", "weight": 1.1, "lang": "both"}
}

# 캐시 키 생성 함수
def get_cache_key(query, source):
    return hashlib.md5(f"{query}_{source}".encode()).hexdigest()

# ------------------------------------------------------------
# API 호출 및 검색 기능
# ------------------------------------------------------------

# 네이버 API 호출 함수
def call_naver_api(query, api_type, display=5, sort="sim"):
    """네이버 API를 호출하여 결과를 반환하는 함수"""
    st.write(f"네이버 API 호출: {api_type} - 쿼리: {query}")  # 디버깅용

    """네이버 API를 호출하여 결과를 반환하는 함수"""
    if not st.session_state.get('naver_api_configured', False):
        return {"error": "네이버 API 키가 설정되지 않았습니다."}
    
    # 캐시 확인
    cache_key = get_cache_key(query, f"naver_{api_type}")
    if cache_key in st.session_state.cache:
        timestamp = st.session_state.cache_timestamp.get(cache_key, 0)
        if time.time() - timestamp < CACHE_EXPIRATION:
            return st.session_state.cache[cache_key]
    
    # API 엔드포인트 설정
    endpoints = {
        "blog": "https://openapi.naver.com/v1/search/blog.json",
        "web": "https://openapi.naver.com/v1/search/webkr.json",
        "news": "https://openapi.naver.com/v1/search/news.json"
    }
    
    if api_type not in endpoints:
        return {"error": f"지원하지 않는 API 타입: {api_type}"}
    
    url = endpoints[api_type]
    headers = {
        "X-Naver-Client-Id": st.session_state.naver_client_id,
        "X-Naver-Client-Secret": st.session_state.naver_client_secret
    }
    params = {
        "query": query,
        "display": display,
        "sort": sort
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()
        
        # 검색 소스 정보 추가
        for item in result.get("items", []):
            item["source_type"] = f"naver_{api_type}"
        
        # 캐시에 저장
        st.session_state.cache[cache_key] = result
        st.session_state.cache_timestamp[cache_key] = time.time()
        
        return result
    except Exception as e:
        logger.error(f"네이버 API 호출 오류: {api_type} - {str(e)}")
        return {"error": f"API 호출 중 오류 발생: {str(e)}"}

# 유튜브 API 호출 함수
def call_youtube_api(query, max_results=5, lang=None):
    """유튜브 API를 호출하여 결과를 반환하는 함수"""
    if not st.session_state.get('youtube_api_configured', False):
        return {"error": "유튜브 API 키가 설정되지 않았습니다."}
    
    # 캐시 확인
    cache_key = get_cache_key(query, "youtube")
    if cache_key in st.session_state.cache:
        timestamp = st.session_state.cache_timestamp.get(cache_key, 0)
        if time.time() - timestamp < CACHE_EXPIRATION:
            return st.session_state.cache[cache_key]
    
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": st.session_state.youtube_api_key,
        "q": query,
        "part": "snippet",
        "maxResults": max_results,
        "type": "video",
        "videoEmbeddable": "true",
        "relevanceLanguage": lang if lang else "en"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        
        # 결과 형식 변환
        items = []
        for item in result.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
            items.append({
                "title": snippet["title"],
                "description": snippet["description"],
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": snippet["thumbnails"]["medium"]["url"],
                "publishedAt": snippet["publishedAt"],
                "channelTitle": snippet["channelTitle"],
                "source_type": "youtube"
            })
        
        formatted_result = {
            "items": items,
            "total": len(items)
        }
        
        # 캐시에 저장
        st.session_state.cache[cache_key] = formatted_result
        st.session_state.cache_timestamp[cache_key] = time.time()
        
        return formatted_result
    except Exception as e:
        logger.error(f"유튜브 API 호출 오류: {str(e)}")
        return {"error": f"유튜브 API 호출 중 오류 발생: {str(e)}"}

# NewsAPI를 사용하여 실시간 뉴스를 가져오는 함수
def fetch_real_time_news(api_key, query="AI digital transformation", days=7, language="en"):
    """
    NewsAPI를 사용하여 실시간 뉴스를 가져옵니다.
    무료 플랜은 최근 1개월(실제로는 더 짧을 수 있음) 데이터만 접근 가능합니다.
    """
    if not st.session_state.get('news_api_configured', False):
        return {"error": "News API 키가 설정되지 않았습니다."}
        
    # 캐시 확인
    cache_key = get_cache_key(query, "news_api")
    if cache_key in st.session_state.cache:
        timestamp = st.session_state.cache_timestamp.get(cache_key, 0)
        if time.time() - timestamp < CACHE_EXPIRATION:
            return st.session_state.cache[cache_key]
    
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
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json()
        
        # 캐시에 저장
        st.session_state.cache[cache_key] = news_data["articles"]
        st.session_state.cache_timestamp[cache_key] = time.time()
        
        return news_data["articles"]
    except Exception as e:
        logger.error(f"News API 호출 오류: {str(e)}")
        return {"error": f"News API 호출 중 오류 발생: {str(e)}"}

# HTML 태그 제거 함수
def remove_html_tags(text):
    if not text:
        return ""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # HTML 엔티티 처리
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
    return text

# 병렬 검색 함수
def parallel_search(query, sources=None, korean_query=None):
    """여러 검색 소스를 병렬로 호출하는 함수"""
    if sources is None:
        sources = ["naver_blog", "naver_web", "youtube"]
    
    all_results = {}
    errors = []
    
    # 영어 쿼리와 한국어 쿼리 처리
    if not korean_query:
        korean_query = query
    english_query = f"Streamlit {query}"  # 영어 쿼리는 항상 Streamlit을 포함
    
    def search_source(source):
        try:
            if source == "naver_blog":
                # 쿼리 단순화 - "스트림릿"만 검색
                return source, call_naver_api(f"스트림릿", "blog", display=8)
            elif source == "naver_web":
                # 쿼리 단순화 - "스트림릿"만 검색
                return source, call_naver_api(f"스트림릿", "web", display=8)
            elif source == "naver_news":
                return source, call_naver_api(f"스트림릿", "news", display=5)
            elif source == "youtube":
                # 간단한 쿼리로 변경, 더 많은 결과 요청
                kr_results = call_youtube_api(f"스트림릿", max_results=4, lang="ko")
                en_results = call_youtube_api("streamlit", max_results=4, lang="en")
                
                # 결과 합치기
                combined_items = []
                if "items" in kr_results and not "error" in kr_results:
                    combined_items.extend(kr_results["items"])
                if "items" in en_results and not "error" in en_results:
                    combined_items.extend(en_results["items"])
                
                return source, {"items": combined_items, "total": len(combined_items)}
        except Exception as e:
            return source, {"error": str(e)}
    
    # 병렬로 검색
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = [executor.submit(search_source, source) for source in sources]
        for future in futures:
            source, result = future.result()
            if "error" in result:
                errors.append(f"{source}: {result['error']}")
            else:
                all_results[source] = result
    
    # 오류가 있으면 로깅
    if errors:
        logger.warning(f"검색 오류: {errors}")
    
    return all_results

# ------------------------------------------------------------
# 교육적 가치 평가 및 콘텐츠 선별
# ------------------------------------------------------------

# 교육 관련 키워드
EDUCATION_KEYWORDS = {
    "high": [
        "tutorial", "튜토리얼", "guide", "가이드", "example", "예제", "how to", "사용법",
        "streamlit tutorial", "스트림릿 튜토리얼", "learn streamlit", "스트림릿 배우기"
    ],
    "medium": [
        "course", "강좌", "lesson", "레슨", "class", "교실", "training", "트레이닝",
        "step by step", "단계별", "beginner", "초보자", "quickstart", "빠른 시작"
    ],
    "low": [
        "tips", "팁", "tricks", "트릭", "best practices", "모범 사례",
        "documentation", "문서", "reference", "참조"
    ]
}

# 주제별 특화 키워드
TOPIC_KEYWORDS = {
    "기본 소개": ["introduction", "시작하기", "설치", "기본", "basic", "install"],
    "데이터프레임": ["dataframe", "데이터프레임", "pandas", "table", "테이블"],
    "차트": ["chart", "차트", "plot", "그래프", "visualization", "시각화", "matplotlib", "plotly"],
    "위젯": ["widget", "위젯", "input", "입력", "button", "버튼", "form", "폼"],
    "레이아웃": ["layout", "레이아웃", "column", "컬럼", "sidebar", "사이드바", "container", "컨테이너"],
    "상태 관리": ["state", "상태", "session", "세션", "cache", "캐시", "memory", "메모리"],
    "배포": ["deploy", "배포", "share", "공유", "cloud", "클라우드", "docker", "도커"]
}

# 교육적 가치 평가 함수
# 교육적 가치 평가 함수 수정 - 필터링 조건 완화
def evaluate_educational_value(item, topic=None):
    """검색 결과의 교육적 가치를 평가하는 함수 - 완화된 버전"""
    score = 10  # 기본 점수를 더 높게 시작 (원래 0에서 시작)
    title = item.get("title", "").lower()
    description = item.get("description", "").lower()
    source_type = item.get("source_type", "")
    
    # HTML 태그 제거
    title = remove_html_tags(title)
    description = remove_html_tags(description)
    
    # 전체 텍스트
    full_text = f"{title} {description}".lower()
    
    # 1. 교육 관련 키워드 점수 (점수 증가)
    for keyword in EDUCATION_KEYWORDS["high"]:
        if keyword.lower() in full_text:
            score += 6  # 8 -> 6으로 감소 (이미 기본 점수가 높아짐)
        elif keyword.lower() in title:
            score += 8  # 10 -> 8로 감소
    
    for keyword in EDUCATION_KEYWORDS["medium"]:
        if keyword.lower() in full_text:
            score += 4  # 5 -> 4로 감소
    
    for keyword in EDUCATION_KEYWORDS["low"]:
        if keyword.lower() in full_text:
            score += 2  # 3 -> 2로 감소
    
    # 2. 주제별 키워드 점수 (점수 유지)
    if topic:
        topic_lower = topic.lower()
        # 주제와 정확히 일치하면 점수 추가
        if topic_lower in full_text:
            score += 8  # 10 -> 8로 감소
        
        # 주제 관련 키워드 확인
        for key, keywords in TOPIC_KEYWORDS.items():
            if key.lower() in topic_lower or topic_lower in key.lower():
                for keyword in keywords:
                    if keyword.lower() in full_text:
                        score += 5  # 7 -> 5로 감소
    
    # 3. 스트림릿 언급 점수 (필수 항목이므로 점수 유지)
    for keyword in ["streamlit", "스트림릿"]:
        if keyword in title.lower():
            score += 10  # 12 -> 10으로 감소
        elif keyword in description.lower():
            score += 5  # 6 -> 5로 감소
    
    # 4. 소스 유형별 가중치 (약간 완화)
    if source_type == "youtube":
        score *= 1.1  # 1.2 -> 1.1로 감소
    elif source_type == "naver_blog":
        score *= 1.0  # 변경 없음
    elif source_type == "naver_web":
        score *= 1.05  # 1.1 -> 1.05로 감소
    
    # 5. 부정적 요소 감점 (감점 완화)
    negative_patterns = [
        r"\?", "궁금", "문제", "에러", "오류", "해결", "질문", "안되", "않아", 
        "실패", "이슈", "버그", "도와", "조언", "help", "error", "issue", "bug", "problem"
    ]
    
    for pattern in negative_patterns:
        if re.search(pattern, title):
            score -= 2  # 5 -> 2로 감소
    
    # 6. 설명 길이 평가 (감점 완화)
    if len(description) < 30:
        score -= 2  # 5 -> 2로 감소
    elif len(description) > 200:
        score += 3  # 변경 없음
    
    return score

# 최적의 교육 자료 선별 함수 수정 - 필터링 기준 완화
def select_best_materials(search_results, topic=None, max_total=4):
    """검색 결과에서 최적의 교육 자료를 선별하는 함수 - 완화된 버전"""
    if not search_results:
        logger.warning(f"검색 결과가 없습니다: {topic}")
        return []
    
    all_scored_items = []
    
    # 각 소스별 결과 평가
    for source, result in search_results.items():
        if "items" not in result or "error" in result:
            logger.warning(f"소스 {source}에 유효한 결과가 없습니다: {result.get('error', '알 수 없는 오류')}")
            continue
        
        if len(result.get("items", [])) == 0:
            logger.warning(f"소스 {source}의 검색 결과가 비어 있습니다.")
            continue
        
        for item in result.get("items", []):
            score = evaluate_educational_value(item, topic)
            logger.info(f"항목 평가: '{remove_html_tags(item.get('title', '제목 없음'))[:30]}...' - 점수: {score}")
            all_scored_items.append((score, item))
    
    # 결과가 있는지 확인
    if not all_scored_items:
        logger.warning(f"주제 '{topic}'에 대한 평가된 항목이 없습니다.")
        return []
    
    # 점수에 따라 정렬
    all_scored_items.sort(reverse=True)
    
    # 소스별 제한 설정 (제한 완화)
    source_limits = {
        "youtube": 3,     # 2 -> 3으로 증가
        "naver_blog": 2,  # 1 -> 2로 증가
        "naver_web": 2,   # 1 -> 2로 증가
        "naver_news": 1   # 0 -> 1로 증가
    }
    
    source_counters = {}
    selected_items = []
    
    # 각 소스의 제한을 지키면서 선택
    for score, item in all_scored_items:
        source_type = item.get("source_type", "unknown")
        
        # 해당 소스에서 이미 충분히 선택했으면 스킵
        if source_counters.get(source_type, 0) >= source_limits.get(source_type, 0):
            continue
        
        # 점수가 너무 낮은 항목은 필터링 (점수 기준 완화)
        if score < 5:  # 원래 기준보다 더 낮게 설정
            logger.info(f"낮은 점수로 제외: {remove_html_tags(item.get('title', '제목 없음'))[:30]}... - 점수: {score}")
            continue
        
        # 선택된 아이템에 추가
        selected_items.append(item)
        source_counters[source_type] = source_counters.get(source_type, 0) + 1
        
        # 최대 개수에 도달하면 종료
        if len(selected_items) >= max_total:
            break
    
    # 선택된 항목이 없거나 너무 적으면 점수 기준을 무시하고 최상위 항목 선택
    if len(selected_items) < 2 and all_scored_items:
        logger.warning(f"선택된 항목이 너무 적습니다. 점수 기준을 무시하고 상위 항목을 선택합니다.")
        add_count = min(2 - len(selected_items), len(all_scored_items))
        
        # 이미 선택된 항목을 제외하고 추가
        already_selected = set(item.get('link', '') for item in selected_items)
        for score, item in all_scored_items:
            if item.get('link', '') not in already_selected:
                selected_items.append(item)
                add_count -= 1
                if add_count <= 0:
                    break
    
    logger.info(f"주제 '{topic}'에 대해 총 {len(selected_items)}개 항목 선택됨")
    return selected_items

# 주제에 대한 최적의 학습 자료 검색
def get_best_learning_materials(topic, korean_topic=None):
    """주제에 대한 최적의 학습 자료를 검색하는 함수 - 수정됨"""
    # 검색 소스 결정
    sources = ["naver_blog", "naver_web", "youtube"]
    
    # 병렬 검색 실행
    search_results = parallel_search(topic, sources, korean_topic)
    
    # 최적의 교육 자료 선별
    materials = select_best_materials(search_results, topic, max_total=4)
    
    # 자료가 없으면 더미 데이터 반환
    if not materials:
        logger.warning(f"주제 '{topic}'에 대한 학습 자료를 찾을 수 없어 더미 데이터를 사용합니다.")
        return get_dummy_materials()
    
    return materials

# 여러 주제에 대한 학습 자료 검색
def get_learning_materials_for_topics(topics):
    """여러 주제에 대한 학습 자료를 검색하는 함수"""
    all_materials = {}
    
    for topic_dict in topics:
        topic = topic_dict["name"]
        with st.spinner(f"'{topic}' 관련 학습 자료 검색 중..."):
            # 영어와 한국어 주제 설정
            korean_topic = topic_dict.get("korean_name", topic)  # 한국어 이름이 있으면 사용
            
            materials = get_best_learning_materials(topic, korean_topic)
            all_materials[topic] = materials
    
    return all_materials

# ------------------------------------------------------------
# 학습 커리큘럼 및 주차별 계획
# ------------------------------------------------------------

# 주차별 학습 계획 (간결한 버전)
WEEKLY_CURRICULUM = {
    "1": {
        "level": "초급",
        "title": "스트림릿 첫 시작",
        "topics": [
            {"name": "Installation", "korean_name": "설치 및 환경 설정", 
             "description": "스트림릿 설치 및 기본 환경 구성"},
            {"name": "First App", "korean_name": "첫 번째 앱 만들기", 
             "description": "Hello World 앱 만들고 실행하기"},
            {"name": "Basic Elements", "korean_name": "기본 요소", 
             "description": "텍스트, 이미지 등 기본 UI 요소 사용법"}
        ]
    },
    # 나머지 주차별 커리큘럼은 원본과 동일하게 유지
}

# 현재 주차 계산 함수
def get_current_week_number():
    """현재 날짜를 기준으로 학습 주차 계산 (1-8 범위)"""
    # 기준 시작일 (예: 2025년 1월 1일)
    start_date = datetime(2025, 1, 1)
    today = datetime.now()
    
    # 시작일로부터 현재까지의 주차 계산
    week_diff = ((today - start_date).days // 7) % 8
    return str(week_diff + 1)  # 1-8 범위의 주차 반환 (문자열)

# 주차별 학습 내용 가져오기
def get_weekly_content(week_number):
    """주차 번호에 따른 학습 내용 가져오기"""
    if week_number in WEEKLY_CURRICULUM:
        return WEEKLY_CURRICULUM[week_number]
    else:
        return WEEKLY_CURRICULUM["1"]  # 기본값

# ------------------------------------------------------------
# OpenAI 통합 기능
# ------------------------------------------------------------

# 마크다운 텍스트를 HTML로 변환하는 함수
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

# OpenAI를 사용하여 스트림릿 학습 팁 생성
def generate_streamlit_learning_tip(openai_api_key, topic, level):
    """OpenAI를 사용하여 주제별 스트림릿 학습 팁 생성 - 포맷 수정"""
    if not openai_api_key:
        return "OpenAI API 키가 설정되지 않았습니다."
    
    try:
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=openai_api_key)
        
        prompt = f"""
        스트림릿 학습 뉴스레터의 '이번 주 학습 팁' 섹션을 생성해주세요.
        
        이번 주 팁 주제는 "{topic}" ({level} 레벨)입니다.
        
        이 주제에 대해 다음 형식으로 실용적인 팁을 작성해주세요:
        
        ## 이번 주 팁: [주제에 맞는 구체적인 팁 제목]
        
        팁에 대한 배경과 중요성을 2-3문장으로 간결하게 설명해주세요. 스트림릿 학습과 관련된 내용을 포함하세요.
        
        **핵심 학습 포인트:**
        
        1. 첫 번째 학습 포인트: 이 주제에 대한 핵심 개념 설명
          예시: [2-3줄의 실제 코드 예시를 제시하세요]
          설명: [코드 예시에 대한 짧은 설명]
        
        2. 두 번째 학습 포인트: 주제와 관련된 중요 기법이나 패턴
          예시: [2-3줄의 실제 코드 예시를 제시하세요]
          설명: [코드 예시에 대한 짧은 설명]
        
        3. 세 번째 학습 포인트: 효율적인 개발을 위한 팁이나 트릭
          예시: [2-3줄의 실제 코드 예시를 제시하세요]
          설명: [코드 예시에 대한 짧은 설명]
        
        이 팁을 활용했을 때의 개발 효율성 향상이나 결과물 품질 개선 등 구체적인 이점을 한 문장으로 작성해주세요.
        
        다음 주에는 다른 스트림릿 학습 팁을 알려드리겠습니다.
        
        참고: 모든 텍스트는 간결하게 작성하고, 각 포인트 사이에 적절한 줄바꿈을 포함해주세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "스트림릿 교육 콘텐츠 생성 전문가. 간결하고 실용적인 학습 팁을 제공합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API 오류: {str(e)}")
        return f"팁 생성 중 오류가 발생했습니다: {str(e)}"

# OpenAI로 학습 프로젝트 아이디어 생성
def generate_project_ideas(openai_api_key, topics, level):
    """OpenAI를 사용하여 주제별 학습 프로젝트 아이디어 생성 - 단일 예시만 생성하도록 수정"""
    if not openai_api_key:
        return "OpenAI API 키가 설정되지 않았습니다."
    
    topics_str = ", ".join([f"{t['korean_name']} ({t['name']})" for t in topics])
    
    try:
        client = OpenAI(api_key=openai_api_key)
        
        prompt = f"""
        스트림릿 학습 뉴스레터의 '실습 프로젝트 아이디어' 섹션을 생성해주세요.
        
        이번 주 학습 주제는 다음과 같습니다: {topics_str}
        난이도 수준: {level}
        
        이 주제들을 활용하여 1가지 실습 프로젝트 아이디어를 제안해주세요. 아이디어는 다음 형식으로 작성해주세요:
        
        ### 프로젝트: [프로젝트 제목]
        
        **목표:** 프로젝트의 목표와 완성했을 때 기대할 수 있는 결과 (1-2문장으로 간결하게)
        
        **필요한 학습 요소:**
        - 이번 주 학습 주제 중 활용되는 요소
        - 관련된 추가 라이브러리나 기술
        
        **구현 단계:**
        1. 첫 번째 단계 설명 (1문장)
        2. 두 번째 단계 설명 (1문장)
        3. 세 번째 단계 설명 (1문장)
        
        **도전 과제:** 기본 구현 이후 더 발전시킬 수 있는 아이디어 (1-2문장)
        
        프로젝트는 실제로 구현 가능하고, 이번 주 학습 내용을 강화할 수 있는 것이어야 합니다.
        난이도는 {level} 수준에 적합해야 하며, 모든 내용은 간결하게 작성해주세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "스트림릿 교육 콘텐츠 생성 전문가. 실용적이고 간결한 프로젝트 아이디어를 제공합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API 오류: {str(e)}")
        return f"프로젝트 아이디어 생성 중 오류가 발생했습니다: {str(e)}"

# 스트림릿 관련 최신 소식 생성
def generate_streamlit_news(openai_api_key, news_api_key):
    """OpenAI와 News API를 사용해 스트림릿 관련 최신 소식 생성"""
    if not openai_api_key or not news_api_key:
        return "API 키가 설정되지 않았습니다."
    
    try:
        # 스트림릿 관련 뉴스 가져오기
        news_articles = fetch_real_time_news(news_api_key, query="Streamlit data science", days=7, language="en")
        
        if isinstance(news_articles, dict) and "error" in news_articles:
            return f"뉴스 가져오기 실패: {news_articles['error']}"
        
        if not news_articles:
            return "스트림릿 관련 최신 뉴스를 찾을 수 없습니다."
        
        # 최신 뉴스 5개만 선택
        top_news = news_articles[:5]
        
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=openai_api_key)
        
        # 뉴스 정보 준비
        news_info = "최근 7일 내 수집된 실제 스트림릿 관련 뉴스 기사:\n\n"
        for i, article in enumerate(top_news):
            pub_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')).strftime('%Y년 %m월 %d일')
            news_info += f"{i+1}. 제목: {article['title']}\n"
            news_info += f"   날짜: {pub_date}\n"
            news_info += f"   요약: {article['description']}\n"
            news_info += f"   출처: {article['source']['name']}\n"
            news_info += f"   URL: {article['url']}\n\n"
        
        prompt = f"""
        스트림릿 학습 뉴스레터의 '최신 스트림릿 소식' 섹션을 생성해주세요.
        
        아래는 수집된 스트림릿 관련 뉴스 기사입니다:
        
        {news_info}
        
        이 중에서 가장 중요하고 교육적 가치가 높은 2개의 소식을 선택하여 다음 형식으로 작성해주세요:
        
        ## 최신 스트림릿 소식
        
        ### [첫 번째 소식 제목]
        
        간략한 내용을 2-3문장으로 작성하세요. 특히 스트림릿 학습에 어떤 도움이 되는지 강조해주세요.
        
        [출처: 출처명](URL 링크)
        
        ### [두 번째 소식 제목]
        
        간략한 내용을 2-3문장으로 작성하세요. 특히 스트림릿 학습에 어떤 도움이 되는지 강조해주세요.
        
        [출처: 출처명](URL 링크)
        
        모든 소식은 반드시 제공된 실제 뉴스 기사에서만 추출해야 합니다. 가상의 정보나 사실이 아닌 내용은 절대 포함하지 마세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "스트림릿 교육 콘텐츠 생성 전문가. 최신 소식을 교육적 관점에서 분석합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"최신 소식 생성 오류: {str(e)}")
        return f"최신 소식 생성 중 오류가 발생했습니다: {str(e)}"

# ------------------------------------------------------------
# 뉴스레터 콘텐츠 생성
# ------------------------------------------------------------

# 학습 뉴스레터 생성 함수
def generate_learning_newsletter(week_number, openai_api_key=None, news_api_key=None, selected_topics=None):
    """스트림릿 학습 뉴스레터 콘텐츠 생성 함수"""
    # 주차 정보 가져오기
    week_content = get_weekly_content(week_number)
    level = week_content["level"]
    title = week_content["title"]
    
    # 주제 선택
    if selected_topics is None:
        topics = week_content["topics"]
    else:
        topics = selected_topics
    
    # 뉴스레터 콘텐츠를 저장할 딕셔너리
    newsletter_content = {}
    
    # 1. 학습 자료 검색
    materials = get_learning_materials_for_topics(topics)
    
    # 2. OpenAI로 학습 팁 생성 (API 키가 있는 경우)
    if openai_api_key:
        try:
            # 첫 번째 주제에 대한 팁 생성
            main_topic = topics[0]["name"]
            korean_topic = topics[0].get("korean_name", main_topic)
            learning_tip = generate_streamlit_learning_tip(openai_api_key, korean_topic, level)
            newsletter_content['learning_tip'] = convert_markdown_to_html(learning_tip)
            
            # 프로젝트 아이디어 생성
            project_ideas = generate_project_ideas(openai_api_key, topics, level)
            newsletter_content['project_ideas'] = convert_markdown_to_html(project_ideas)
            
            # 최신 소식 생성 (News API가 있는 경우)
            if news_api_key:
                streamlit_news = generate_streamlit_news(openai_api_key, news_api_key)
                newsletter_content['streamlit_news'] = convert_markdown_to_html(streamlit_news)
        except Exception as e:
            st.error(f"OpenAI API 오류: {str(e)}")
            newsletter_content['learning_tip'] = "<p>학습 팁을 생성하지 못했습니다.</p>"
            newsletter_content['project_ideas'] = "<p>프로젝트 아이디어를 생성하지 못했습니다.</p>"
    else:
        newsletter_content['learning_tip'] = "<p>OpenAI API 키가 설정되지 않았습니다.</p>"
        newsletter_content['project_ideas'] = "<p>OpenAI API 키가 설정되지 않았습니다.</p>"
    
    # 학습 자료 마크다운 생성
    study_materials_html = ""
    for topic in topics:
        topic_name = topic["name"]
        korean_name = topic.get("korean_name", topic_name)
        description = topic.get("description", "")
        
        study_materials_html += f"<h3>{korean_name} ({topic_name})</h3>"
        study_materials_html += f"<p>{description}</p>"
        
        if topic_name in materials and materials[topic_name]:
            topic_materials = materials[topic_name]
            
            # 유튜브와 문서로 구분
            videos = [m for m in topic_materials if m["source_type"] == "youtube"]
            docs = [m for m in topic_materials if m["source_type"] != "youtube"]
            
            # 자료 목록 생성
            study_materials_html += "<div class='materials-grid'>"
            
            # 비디오 섹션
            if videos:
                for video in videos[:2]:  # 최대 2개만 표시
                    title = remove_html_tags(video["title"])
                    description = remove_html_tags(video["description"])
                    if len(description) > 150:
                        description = description[:150] + "..."
                    
                    study_materials_html += f"""
                    <div class='material-card video-card'>
                        <div class='card-header'>
                            <span class='card-icon'>▶️</span>
                            <span class='card-type'>동영상 튜토리얼</span>
                        </div>
                        <h4 class='card-title'><a href='{video['link']}' target='_blank'>{title}</a></h4>
                        <p class='card-description'>{description}</p>
                        <div class='card-footer'>
                            <span class='card-source'>{video.get('channelTitle', '유튜브')}</span>
                        </div>
                    </div>
                    """
            
            # 문서 섹션
            if docs:
                for doc in docs[:2]:  # 최대 2개만 표시
                    title = remove_html_tags(doc["title"])
                    description = remove_html_tags(doc["description"])
                    if len(description) > 150:
                        description = description[:150] + "..."
                    
                    source_type = "블로그" if doc["source_type"] == "naver_blog" else "웹문서"
                    source_icon = "📝" if doc["source_type"] == "naver_blog" else "🌐"
                    
                    study_materials_html += f"""
                    <div class='material-card doc-card'>
                        <div class='card-header'>
                            <span class='card-icon'>{source_icon}</span>
                            <span class='card-type'>{source_type}</span>
                        </div>
                        <h4 class='card-title'><a href='{doc['link']}' target='_blank'>{title}</a></h4>
                        <p class='card-description'>{description}</p>
                        <div class='card-footer'>
                            <span class='card-source'>{doc.get('bloggername', source_type)}</span>
                        </div>
                    </div>
                    """
            
            study_materials_html += "</div>"
        else:
            study_materials_html += "<p>이 주제에 대한 학습 자료를 찾을 수 없습니다.</p>"
    
    newsletter_content['study_materials'] = study_materials_html
    
    # 현재 날짜
    date = datetime.now().strftime('%Y년 %m월 %d일')
    
    # HTML 템플릿 생성
    html_content = generate_learning_newsletter_html(newsletter_content, week_number, date, title, level, topics)
    return html_content

# 학습 뉴스레터 HTML 템플릿 생성 함수
def generate_learning_newsletter_html(newsletter_content, week_number, date, title, level, topics):
    """스트림릿 학습 뉴스레터 HTML 템플릿을 생성합니다 - 스타일 수정"""
    # 주제 목록 생성
    topic_list = ""
    for topic in topics:
        korean_name = topic.get("korean_name", topic["name"])
        topic_list += f"<li>{korean_name} ({topic['name']})</li>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>스트림릿 학습 뉴스레터 - 제{week_number}주차</title>
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
                max-width: 800px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .content {{
                padding: 20px;
            }}
            .header {{
                background-color: #F63366;
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
                background-color: #F63366;
                padding: 8px 10px;
                border-radius: 4px;
            }}
            .section-icon {{
                margin-right: 8px;
            }}
            h2, h3 {{
                font-size: 16px;
                margin-bottom: 10px;
                color: #F63366;
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
            }}
            h4 {{
                font-size: 14px;
                margin-bottom: 5px;
                color: #333;
            }}
            /* 모든 글자 크기 10pt로 통일 */
            p, li, .card-description, .card-title, .project-content, .learning-tip-content {{
                font-size: 10pt !important;
                margin: 0 0 8px;
            }}
            ul {{
                padding-left: 20px;
                margin-top: 5px;
                margin-bottom: 15px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            a {{
                color: #F63366;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 10px;
                text-align: center;
                font-size: 10pt;
                color: #666;
            }}
            .level-badge {{
                display: inline-block;
                background-color: #F63366;
                color: white;
                font-size: 10pt;
                padding: 3px 8px;
                border-radius: 10px;
                margin-left: 8px;
            }}
            
            /* 학습 팁 섹션 스타일 - 수정됨 */
            .tip-title {{
                background-color: #f2f2f2;
                padding: 8px 10px;
                margin-bottom: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10pt;
            }}
            .learning-point {{
                margin-bottom: 15px; /* 포인트 사이 간격 */
            }}
            .learning-point-title {{
                font-weight: bold;
                margin-bottom: 5px;
                font-size: 10pt;
            }}
            .example-label, .prompt-label {{
                font-weight: bold;
                margin-top: 5px;
                color: #333;
                font-size: 10pt;
            }}
            .example-content, .prompt-content {{
                margin-left: 15px;
                line-height: 1.3;
                margin-bottom: 0; /* 내부 간격 제거 */
                color: #333;
                background-color: #f9f9f9;
                padding: 8px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 10pt;
            }}
            .explanation {{
                margin-top: 5px;
                margin-bottom: 0; /* 내부 간격 제거 */
                font-size: 10pt;
            }}
            
            /* 학습 자료 카드 스타일 */
            .materials-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 15px;
                margin-bottom: 20px;
            }}
            .material-card {{
                border: 1px solid #eee;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .material-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .video-card {{
                border-left: 4px solid #ff0000;
            }}
            .doc-card {{
                border-left: 4px solid #4285f4;
            }}
            .card-header {{
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }}
            .card-icon {{
                margin-right: 8px;
                font-size: 10pt;
            }}
            .card-type {{
                font-size: 9pt;
                color: #666;
                background-color: #f1f1f1;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            .card-title {{
                font-size: 10pt !important;
                margin: 0 0 10px 0;
                line-height: 1.3;
            }}
            .card-description {{
                font-size: 10pt !important;
                color: #555;
                margin-bottom: 15px;
                line-height: 1.4;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }}
            .card-footer {{
                font-size: 9pt;
                color: #666;
                border-top: 1px solid #eee;
                padding-top: 8px;
            }}
            .card-source {{
                font-style: italic;
            }}
            
            /* 프로젝트 아이디어 스타일 - 수정됨 */
            .project-idea {{
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                font-size: 10pt;
            }}
            .project-idea h3 {{
                color: #F63366;
                border-bottom: 1px solid #ddd;
                padding-bottom: 8px;
                font-size: 12pt;
            }}
            .project-goal {{
                font-weight: bold;
                margin-top: 10px;
                font-size: 10pt;
            }}
            .project-steps {{
                background-color: #fff;
                padding: 10px;
                border-radius: 4px;
                border-left: 3px solid #F63366;
                margin: 10px 0;
                font-size: 10pt;
            }}
            .project-content p, .project-content li {{
                font-size: 10pt !important;
                margin-bottom: 5px;
            }}
            
            /* 최신 소식 스타일 */
            .news-item {{
                border-bottom: 1px solid #eee;
                padding-bottom: 15px;
                margin-bottom: 15px;
            }}
            .news-item:last-child {{
                border-bottom: none;
            }}
            .news-source {{
                font-size: 9pt;
                color: #666;
                text-align: right;
                font-style: italic;
            }}
            
            /* 커리큘럼 개요 스타일 */
            .curriculum-overview {{
                background-color: #f5f5ff;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }}
            .curriculum-overview ul {{
                margin-bottom: 0;
            }}
            
            /* 기본 더미 자료 스타일 */
            .dummy-material {{
                background-color: #f5f5f5;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 15px;
                border-left: 4px solid #F63366;
            }}
            .dummy-title {{
                font-weight: bold;
                margin-bottom: 5px;
                font-size: 10pt;
            }}
            .dummy-description {{
                color: #555;
                margin-bottom: 8px;
                font-size: 10pt;
            }}
            .dummy-source {{
                font-size: 9pt;
                color: #666;
                text-align: right;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">스트림릿 학습 뉴스레터</div>
                <div class="issue-info">제{week_number}주차 | {date}</div>
            </div>
            
            <div class="content">
                <div class="newsletter-intro">
                    <h2>{title} <span class="level-badge">{level}</span></h2>
                    <p>안녕하세요! 이번 주 스트림릿 학습 뉴스레터에서는 <strong>{title}</strong>에 대해 다루고 있습니다. 
                    주요 학습 주제와 유용한 자료들을 모아 보내드립니다.</p>
                    
                    <div class="curriculum-overview">
                        <h3>이번 주 학습 주제</h3>
                        <ul>
                            {topic_list}
                        </ul>
                    </div>
                </div>
                
                <!-- 추천 학습 자료 섹션 -->
                <div class="section">
                    <div class="section-title"><span class="section-icon">📚</span>추천 학습 자료</div>
                    <div class="section-container">
                        {newsletter_content.get('study_materials', '<p>학습 자료를 찾을 수 없습니다.</p>')}
                    </div>
                </div>
                
                <!-- 이번 주 학습 팁 섹션 -->
                <div class="section">
                    <div class="section-title"><span class="section-icon">💡</span>이번 주 학습 팁</div>
                    <div class="section-container learning-tip-content">
                        {newsletter_content.get('learning_tip', '<p>학습 팁을 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                
                <!-- 실습 프로젝트 아이디어 섹션 -->
                <div class="section">
                    <div class="section-title"><span class="section-icon">🔨</span>실습 프로젝트 아이디어</div>
                    <div class="section-container project-content">
                        {newsletter_content.get('project_ideas', '<p>프로젝트 아이디어를 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                
                <!-- 최신 스트림릿 소식 섹션 -->
                {f'''
                <div class="section">
                    <div class="section-title"><span class="section-icon">📰</span>최신 스트림릿 소식</div>
                    <div class="section-container">
                        {newsletter_content.get('streamlit_news', '<p>최신 소식을 불러올 수 없습니다.</p>')}
                    </div>
                </div>
                ''' if 'streamlit_news' in newsletter_content else ""}
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} 스트림릿 학습 뉴스레터 | 이 뉴스레터는 자동 생성되었습니다.</p>
                <p>구독을 원하지 않으시면 답장으로 알려주세요. | 문의사항: example@example.com</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# 더미 학습 자료 반환 함수 추가
def get_dummy_materials():
    """API 호출 실패시 반환할 더미 학습 자료"""
    return [
        {
            "title": "스트림릿(Streamlit) 기초: 데이터 애플리케이션 쉽게 만들기",
            "description": "파이썬으로 데이터 애플리케이션을 쉽게 만들 수 있는 Streamlit의 기본 사용법을 알아봅니다. 설치부터 첫 앱 만들기까지 단계별로 설명합니다.",
            "link": "https://streamlit.io/docs/get-started",
            "source_type": "naver_blog",
            "bloggername": "파이썬 개발자 블로그"
        },
        {
            "title": "Streamlit Tutorial: Creating Interactive Web Apps",
            "description": "Learn how to build interactive web applications with Streamlit in Python. This tutorial covers the basics of using widgets, layouts, and data visualization.",
            "link": "https://www.youtube.com/watch?v=B2iAodr0fOo",
            "source_type": "youtube",
            "channelTitle": "Streamlit Official"
        },
        {
            "title": "데이터 과학자를 위한 스트림릿 대시보드 만들기",
            "description": "판다스, 맷플롯립, 플로틀리 등을 활용하여 데이터 분석 결과를 스트림릿으로 시각화하는 방법을 배웁니다.",
            "link": "https://docs.streamlit.io/library/api-reference",
            "source_type": "naver_web",
            "bloggername": "데이터 사이언스 포털"
        }
    ]


# 다운로드 링크 생성 함수
def create_download_link(html_content, filename):
    """HTML 콘텐츠를 다운로드할 수 있는 링크를 생성합니다."""
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #F63366; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">뉴스레터 다운로드</a>'
    return href

# ------------------------------------------------------------
# 메인 앱 인터페이스
# ------------------------------------------------------------

def main():
    st.title("AI 기반 학습 뉴스레터 생성기")
    st.write("AI와 다양한 API를 활용하여 맞춤형 스트림릿 학습 뉴스레터를 생성합니다.")
    
    # 탭 설정
    tab1, tab2, tab3 = st.tabs(["📚 학습 뉴스레터", "🔍 API 설정", "ℹ️ 정보"])
    
    with tab1:
        st.header("스트림릿 학습 뉴스레터 생성")
        
        # 주차 선택

        col1, col2 = st.columns([1, 2])
        with col1:
            current_week = get_current_week_number()
            # 유효한 인덱스 계산
            try:
                current_week_int = int(current_week)
                available_weeks = list(WEEKLY_CURRICULUM.keys())
                # 유효한 인덱스 범위 확인
                if current_week_int < 1 or current_week_int > len(available_weeks):
                    default_index = 0  # 기본값으로 첫 번째 항목 선택
                else:
                    default_index = current_week_int - 1
            except:
                default_index = 0  # 변환 오류 시 첫 번째 항목 선택
            
            week_number = st.selectbox(
                "주차 선택", 
                options=list(WEEKLY_CURRICULUM.keys()),
                index=default_index,
                format_func=lambda x: f"{x}주차: {WEEKLY_CURRICULUM[x]['title']} ({WEEKLY_CURRICULUM[x]['level']})",
                help="생성할 뉴스레터의 주차를 선택하세요."
            )
        
        with col2:
            # 선택된 주차 내용 미리보기
            week_content = get_weekly_content(week_number)
            st.write(f"**선택된 주제:** {week_content['title']} ({week_content['level']})")
            
            topic_names = [f"{t['korean_name']} ({t['name']})" for t in week_content['topics']]
            st.write("**학습 주제:**")
            for topic in topic_names:
                st.write(f"- {topic}")
        
        # 뉴스레터 생성 버튼
        if st.button("뉴스레터 생성", type="primary"):
            # API 키 확인
            if not st.session_state.get('naver_api_configured', False) and not st.session_state.get('youtube_api_configured', False):
                st.error("네이버 API 또는 유튜브 API 중 최소한 하나는 설정해야 합니다.")
            else:
                with st.spinner("AI 기반 학습 뉴스레터 생성 중... (약 30-60초 소요)"):
                    try:
                        # 뉴스레터 생성
                        html_content = generate_learning_newsletter(
                            week_number,
                            st.session_state.get('openai_api_key', None),
                            st.session_state.get('news_api_key', None)
                        )
                        
                        # 다운로드 링크 생성
                        filename = f"스트림릿_학습_뉴스레터_제{week_number}주차.html"
                        st.success("✅ 뉴스레터가 성공적으로 생성되었습니다!")
                        st.markdown(create_download_link(html_content, filename), unsafe_allow_html=True)
                        
                        # 미리보기
                        with st.expander("뉴스레터 미리보기", expanded=True):
                            st.components.v1.html(html_content, height=600, scrolling=True)
                        
                    except Exception as e:
                        st.error(f"뉴스레터 생성 중 오류가 발생했습니다: {str(e)}")
    
    with tab2:
        st.header("API 설정")
        st.info("다양한 API를 사용하여 더 풍부한 뉴스레터를 생성할 수 있습니다. 최소 하나 이상의 API 키를 설정하세요.")
        
        # API 키 입력
        with st.expander("네이버 API 설정", expanded=not st.session_state.get('naver_api_configured', False)):
            naver_client_id = st.text_input("네이버 Client ID", type="password")
            naver_client_secret = st.text_input("네이버 Client Secret", type="password")
            
            if st.button("네이버 API 설정 저장"):
                if naver_client_id and naver_client_secret:
                    st.session_state.naver_client_id = naver_client_id
                    st.session_state.naver_client_secret = naver_client_secret
                    st.session_state.naver_api_configured = True
                    st.success("네이버 API 설정이 저장되었습니다!")
                else:
                    st.error("Client ID와 Client Secret을 모두 입력하세요.")
        
        with st.expander("유튜브 API 설정", expanded=not st.session_state.get('youtube_api_configured', False)):
            youtube_api_key = st.text_input("유튜브 API 키", type="password")
            
            if st.button("유튜브 API 설정 저장"):
                if youtube_api_key:
                    st.session_state.youtube_api_key = youtube_api_key
                    st.session_state.youtube_api_configured = True
                    st.success("유튜브 API 설정이 저장되었습니다!")
                else:
                    st.error("API 키를 입력하세요.")
        
        with st.expander("OpenAI API 설정", expanded=not st.session_state.get('openai_api_configured', False)):
            openai_api_key = st.text_input("OpenAI API 키", type="password")
            
            if st.button("OpenAI API 설정 저장"):
                if openai_api_key:
                    st.session_state.openai_api_key = openai_api_key
                    st.session_state.openai_api_configured = True
                    st.success("OpenAI API 설정이 저장되었습니다!")
                else:
                    st.error("API 키를 입력하세요.")
        
        with st.expander("News API 설정", expanded=not st.session_state.get('news_api_configured', False)):
            news_api_key = st.text_input("News API 키", type="password")
            
            if st.button("News API 설정 저장"):
                if news_api_key:
                    st.session_state.news_api_key = news_api_key
                    st.session_state.news_api_configured = True
                    st.success("News API 설정이 저장되었습니다!")
                else:
                    st.error("API 키를 입력하세요.")
    
    with tab3:
        st.header("정보")
        st.markdown("""
        ## AI 기반 학습 뉴스레터 생성기
        
        이 애플리케이션은 다양한 API를 활용하여 스트림릿 학습 뉴스레터를 자동으로 생성합니다.
        
        ### 주요 기능
        - 주차별 맞춤형 학습 콘텐츠 제공
        - 네이버와 유튜브 API를 통한 최적의 학습 자료 검색
        - OpenAI API를 활용한 학습 팁 및 프로젝트 아이디어 생성
        - News API를 통한 최신 스트림릿 소식 제공
        
        ### 필요한 API 키
        - 네이버 API (Client ID, Client Secret): 블로그, 웹문서 검색
        - 유튜브 API: 동영상 튜토리얼 검색
        - OpenAI API: 학습 팁, 프로젝트 아이디어 생성
        - News API: 최신 스트림릿 관련 뉴스 검색
        
        각 API는 선택적으로 사용할 수 있으며, 최소 하나 이상의 API를 설정해야 합니다.
        """)

if __name__ == "__main__":
    main()