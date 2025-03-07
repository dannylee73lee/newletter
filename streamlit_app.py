import streamlit as st
import datetime

def create_newsletter():
    # 페이지 설정
    st.set_page_config(
        page_title="AIDT Weekly 뉴스레터 생성기",
        page_icon="📨",
        layout="centered"
    )
    
    # 사이드바 설정
    with st.sidebar:
        st.title("뉴스레터 설정")
        
        # 발행 정보
        st.subheader("기본 정보")
        issue_number = st.number_input("발행 호수", min_value=1, value=1, step=1)
        issue_date = st.date_input("발행일", datetime.datetime.now())
        
        # 섹션 선택
        st.subheader("포함할 섹션")
        include_news = st.checkbox("주요 소식", value=True)
        include_tips = st.checkbox("AIDT 팁", value=True)
        include_success = st.checkbox("성공 사례", value=True)
        include_qna = st.checkbox("질문 & 답변", value=True)
        include_events = st.checkbox("다가오는 이벤트", value=True)
        include_caution = st.checkbox("주의사항", value=True)
        
        # 생성 버튼
        generate = st.button("뉴스레터 생성", type="primary")
    
    # 메인 페이지
    st.title("AIDT Weekly 뉴스레터 생성기")
    
    # 미리보기/편집 탭
    tab1, tab2 = st.tabs(["미리보기", "콘텐츠 편집"])
    
    with tab2:
        # 주요 소식 섹션
        if include_news:
            st.subheader("🔔 주요 소식")
            news_title = st.text_input("주요 소식 제목", "2025년 AIDT 연간 계획이 발표되었습니다.")
            news_content = st.text_area(
                "주요 소식 내용", 
                "안녕하세요! AIDT Weekly의 첫 번째 뉴스레터를 발행하게 되어 기쁩니다. 이 뉴스레터는 우리 조직의 AI 디지털 트랜스포메이션 여정을 지원하기 위해 매주 발행될 예정입니다.\n\n올해는 모든 구성원이 AIDT를 이해하고 업무에 적극 활용하는 AI 주도 조직문화 확립을 목표로 합니다.",
                height=150
            )
            news_link = st.text_input("관련 링크", "https://example.com/aidt-plan")
        
        # AIDT 팁 섹션
        if include_tips:
            st.subheader("💡 이번 주 AIDT 팁")
            tips_title = st.text_input("팁 제목", "효과적인 프롬프트 작성의 5가지 원칙")
            tips_intro = st.text_area(
                "팁 소개", 
                "AI 도구를 활용할 때 가장 중요한 것은 '어떻게 질문하느냐'입니다. 효과적인 프롬프트를 작성하면 더 정확하고 유용한 결과를 얻을 수 있습니다.",
                height=100
            )
            
            # 팁 목록 (동적 필드)
            st.write("팁 목록")
            tips = []
            for i in range(5):
                tip = st.text_input(f"팁 {i+1}", value=f"팁 내용 {i+1}", key=f"tip_{i}")
                tips.append(tip)
            
            # 오늘의 공유 팁
            share_tip = st.text_area(
                "오늘의 공유 팁",
                "AI에게 질문할 때는 '무엇을, 왜, 어떻게'를 명확히 하세요.\n예: '마케팅 회의를 위해 지난 달 SNS 캠페인 결과를 3가지 핵심 포인트로 요약해줘'",
                height=100
            )
        
        # 성공 사례 섹션
        if include_success:
            st.subheader("🏆 성공 사례")
            success_title = st.text_input("사례 제목", "마케팅팀의 고객 분석 보고서 자동화")
            success_problem = st.text_area(
                "문제 상황",
                "마케팅팀은 매월 고객 데이터를 분석하여 보고서를 작성하는 데 평균 3일이 소요되었습니다.",
                height=100
            )
            success_solution = st.text_area(
                "AIDT 적용 방법",
                "ChatGPT와 Excel을 연동하여 데이터 분석 및 인사이트 도출 프로세스를 자동화했습니다. 주요 고객 행동 패턴 분석을 위한 프롬프트 템플릿을 개발하고, 보고서 형식을 표준화했습니다.",
                height=150
            )
            success_result = st.text_area(
                "결과",
                "보고서 작성 시간이 3일에서 하루 이내로 단축되어 약 70%의 시간이 절약되었습니다. 또한 인사이트의 질과 일관성이 향상되었습니다.",
                height=100
            )
            success_quote = st.text_input(
                "인용구",
                "이제 데이터 정리에 시간을 쓰는 대신 인사이트를 기반으로 한 마케팅 전략 수립에 더 집중할 수 있게 되었습니다."
            )
            success_quote_author = st.text_input("인용구 작성자", "마케팅팀 김주영 과장")
        
        # 질문 & 답변 섹션
        if include_qna:
            st.subheader("❓ 질문 & 답변")
            qna_question = st.text_input("질문", "AIDT 도구를 사용하기 위해 특별한 기술 지식이 필요한가요?")
            qna_answer = st.text_area(
                "답변",
                "특별한 기술 지식은 필요하지 않습니다. AIDT 도구는 누구나 쉽게 사용할 수 있도록 설계되었습니다. 기본적인 컴퓨터 활용 능력만 있으면 충분합니다. 중요한 것은 자신의 업무에 어떻게 적용할지 고민하고, 효과적인 프롬프트를 작성하는 능력입니다. 이 뉴스레터와 향후 제공될 교육 자료를 통해 단계적으로 배울 수 있습니다.",
                height=150
            )
            qna_link = st.text_input("질문 제출 링크", "https://example.com/submit-question")
        
        # 다가오는 이벤트 섹션
        if include_events:
            st.subheader("📅 다가오는 이벤트")
            event_date = st.text_input("이벤트 날짜", "3월 15일(금) 오후 2시")
            event_title = st.text_input("이벤트 제목", "부서별 AIDT 담당자 온라인 오리엔테이션")
            event_description = st.text_area(
                "이벤트 설명",
                "각 부서에서 선발된 AIDT 담당자들을 위한 첫 온라인 미팅이 진행됩니다. 연간 계획 공유 및 부서별 AIDT 활용 방안에 대해 논의할 예정입니다.",
                height=100
            )
            event_link = st.text_input("일정 확인 링크", "https://example.com/check-schedule")
        
        # 주의사항 섹션
        if include_caution:
            st.subheader("⚠️ AI 사용 시 주의사항")
            caution_content = st.text_area(
                "주의사항 내용",
                "업무에 AI를 활용할 때는 항상 최종 결과물을 검토하세요. AI는 훌륭한 도구이지만, 전문가의 판단을 완전히 대체할 수 없습니다. 특히 중요한 의사결정이나 고객 응대 자료는 반드시 검증 과정을 거쳐야 합니다.",
                height=100
            )
    
    with tab1:
        # 생성 버튼을 누르면 뉴스레터 미리보기 표시
        if 'generate' in locals() and generate:
            # 헤더 부분
            st.markdown(f"""
            <div style="text-align:center; border-bottom:2px solid #0066cc; padding:20px 0;">
                <h1 style="color:#0066cc; margin:10px 0 5px;">AIDT Weekly</h1>
                <p style="color:#666; margin:0; font-size:14px;">제{issue_number}호 | {issue_date.strftime('%Y년 %m월 %d일')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 주요 소식 섹션
            if include_news:
                st.markdown(f"""
                <div style="margin:25px 0; clear:both;">
                    <h2 style="color:#0066cc; margin-top:0; padding-bottom:5px; border-bottom:1px solid #eee;">🔔 주요 소식</h2>
                    <p>{news_content.replace('\\n', '<br>')}</p>
                    <p><strong>{news_title}</strong> <a href="{news_link}" target="_blank">자세히 보기</a></p>
                </div>
                """, unsafe_allow_html=True)
            
            # AIDT 팁 섹션
            if include_tips:
                tips_html = ""
                for i, tip in enumerate(tips):
                    tips_html += f"<li><strong>팁 {i+1}:</strong> {tip}</li>"
                
                st.markdown(f"""
                <div style="margin:25px 0; clear:both;">
                    <h2 style="color:#0066cc; margin-top:0; padding-bottom:5px; border-bottom:1px solid #eee;">💡 이번 주 AIDT 팁</h2>
                    <h3>{tips_title}</h3>
                    <p>{tips_intro}</p>
                    <ol>
                        {tips_html}
                    </ol>
                    <div style="background-color:#fffbe6; border:1px dashed #ffd700; padding:12px 15px; margin:20px 0; text-align:center;">
                        <strong>오늘의 공유 팁</strong><br>
                        {share_tip.replace('\\n', '<br>')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # 성공 사례 섹션
            if include_success:
                st.markdown(f"""
                <div style="margin:25px 0; clear:both;">
                    <h2 style="color:#0066cc; margin-top:0; padding-bottom:5px; border-bottom:1px solid #eee;">🏆 성공 사례</h2>
                    <div style="background-color:#f5f5f5; padding:15px; border-radius:5px;">
                        <h3>{success_title}</h3>
                        <p><strong>문제 상황:</strong> {success_problem}</p>
                        <p><strong>AIDT 적용 방법:</strong> {success_solution}</p>
                        <p><strong>결과:</strong> {success_result}</p>
                        <p style="font-style:italic; color:#666; border-left:3px solid #ccc; padding-left:10px; margin-left:0;">
                            "{success_quote}" - {success_quote_author}
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # 질문 & 답변 섹션
            if include_qna:
                st.markdown(f"""
                <div style="margin:25px 0; clear:both;">
                    <h2 style="color:#0066cc; margin-top:0; padding-bottom:5px; border-bottom:1px solid #eee;">❓ 질문 & 답변</h2>
                    <div style="background-color:#f9f9f9; padding:15px; border-radius:5px;">
                        <p style="font-weight:bold; margin-bottom:5px;">Q: {qna_question}</p>
                        <p>A: {qna_answer}</p>
                        <p>
                            <a href="{qna_link}" style="display:inline-block; background-color:#0066cc; color:white; padding:8px 15px; text-decoration:none; border-radius:4px; margin-top:10px;">
                                질문 제출하기
                            </a>
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # 다가오는 이벤트 섹션
            if include_events:
                st.markdown(f"""
                <div style="margin:25px 0; clear:both;">
                    <h2 style="color:#0066cc; margin-top:0; padding-bottom:5px; border-bottom:1px solid #eee;">📅 다가오는 이벤트</h2>
                    <div style="background-color:#fff8e9; padding:15px; border-radius:5px;">
                        <p><strong>{event_date}</strong> - {event_title}</p>
                        <p>{event_description}</p>
                        <p>
                            <a href="{event_link}" style="display:inline-block; background-color:#0066cc; color:white; padding:8px 15px; text-decoration:none; border-radius:4px; margin-top:10px;">
                                일정 확인하기
                            </a>
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # 주의사항 섹션
            if include_caution:
                st.markdown(f"""
                <div style="background-color:#e9f5ff; border-left:4px solid #0066cc; padding:15px; margin:20px 0;">
                    <h3 style="margin-top:0; color:#0066cc;">AI 사용 시 주의사항</h3>
                    <p>{caution_content}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 푸터 부분
            st.markdown("""
            <div style="text-align:center; padding-top:20px; border-top:1px solid #eee; color:#999; font-size:12px;">
                <p>이 뉴스레터는 매주 월요일에 발송됩니다.<br>
                문의사항: <a href="mailto:aidt@company.com" style="color:#0066cc; text-decoration:none;">aidt@company.com</a><br>
                © 2025 AIDT 추진팀</p>
                
                <p>
                    <a href="#" style="color:#0066cc; text-decoration:none;">구독 취소</a> | 
                    <a href="#" style="color:#0066cc; text-decoration:none;">과거 뉴스레터 보기</a> | 
                    <a href="#" style="color:#0066cc; text-decoration:none;">피드백 제출</a>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # 뉴스레터 저장 옵션
            st.success("뉴스레터가 생성되었습니다!")
            st.download_button(
                label="HTML로 다운로드",
                data="뉴스레터 HTML 코드",
                file_name=f"aidt_weekly_{issue_number}_{issue_date.strftime('%Y%m%d')}.html",
                mime="text/html"
            )

# 애플리케이션 실행
if __name__ == "__main__":
    create_newsletter()