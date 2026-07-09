import re
import json

def extract_critical_exception(raw_log_text):
    """
    방대한 톰캣/제우스 로그 스트링에서 Exception 명칭과 
    'Caused by'로 시작하는 핵심 유발 라인, 그리고 핵심 에러 라인을 추출합니다.
    """
    result = {
        "primary_exception": "UnknownException",
        "critical_lines": [],
        "status": "PARSED"
    }
    
    if not raw_log_text:
        return json.dumps(result)
        
    lines = raw_log_text.split('\n')
    
    # 톰캣 및 제우스에서 자주 발생하는 주요 예외 패턴 정의
    exception_pattern = re.compile(r"([a-zA-Z0-9.]+Exception|[a-zA-Z0-9.]+Error)")
    
    for idx, line in enumerate(lines):
        # ERROR, FATAL 키워드가 있거나 Caused by 구문이 있는 라인 수집
        if "ERROR" in line or "FATAL" in line or "Caused by:" in line:
            # 내부 IP나 유저 정보 유출 방지를 위한 정규식 마스킹 처리 예시
            clean_line = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "<TARGET_IP>", line)
            result["critical_lines"].append(f"[Line {idx+1}] {clean_line.strip()}")
            
            # 최초로 매칭되는 주요 예외명을 대표 예외로 지정
            if result["primary_exception"] == "UnknownException":
                match = exception_pattern.search(line)
                if match:
                    result["primary_exception"] = match.group(1)
                    
    # 토큰 절약을 위해 상위 크리티컬 라인 15개만 슬라이싱
    result["critical_lines"] = result["critical_lines"][:15]
    
    return json.dumps(result, ensure_ascii=False, indent=2)