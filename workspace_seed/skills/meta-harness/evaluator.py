import datetime
import json
import os
import sys
from pathlib import Path
import dotenv
import httpx
from langchain.chat_models import init_chat_model

# 1. 환경 구성 및 경로 정의
dotenv.load_dotenv()
WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "workspace")).expanduser().resolve()
EVAL_FILE = WORKSPACE / "eval_dataset.json"
REPORT_FILE = WORKSPACE / "agent_result_report.md"
AGENTS_MD = WORKSPACE / "AGENTS.md"

api_key = os.getenv("OPENAI_API_KEY")
base_url = "https://openrouter.ai/api/v1"

if not api_key:
    print("[오류] OPENAI_API_KEY가 존재하지 않습니다. .env 파일을 확인하세요.", file=sys.stderr)
    sys.exit(1)

# 2. 안전한 HTTP 클라이언트 구성 (타임아웃 넉넉히 설정)
insecure_client = httpx.Client(verify=False, timeout=90.0)
insecure_async_client = httpx.AsyncClient(verify=False, timeout=90.0)

# 3. 평가용 베이스 모델 선언
print("[Meta-Harness] OpenRouter를 통해 Claude Sonnet 5 추론 모델 가동 중...")
model = init_chat_model(
    model="anthropic/claude-sonnet-5",
    model_provider="openai",
    api_key=api_key,
    base_url=base_url,
    http_client=insecure_client,
    http_async_client=insecure_async_client,
)

def load_system_prompt() -> str:
    """AGENTS.md 및 시스템 기본 컨텍스트를 결합하여 프롬프트를 생성합니다."""
    base_prompt = (
        "당신은 10년 경력의 베테랑 SRE 전문가입니다. RHEL 8.5, 128GB RAM, Tomcat, JEUS, IBM MQ, Vanilla K8S 환경을 다룹니다.\n"
        "실제 IP는 <TARGET_IP>, 계정명은 <USER_NAME>으로 반드시 마스킹해야 합니다.\n"
        "최하단에는 항상 휴먼 인 더 루프 경고문을 포함하십시오.\n"
    )
    if AGENTS_MD.is_file():
        try:
            base_prompt += "\n[추가 장기 기억 지침]\n" + AGENTS_MD.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[경고] AGENTS.md 로드 실패: {e}", file=sys.stderr)
    return base_prompt

def run_self_evaluation():
    if not EVAL_FILE.exists():
        print(f"[오류] 평가셋 파일({EVAL_FILE})을 찾을 수 없습니다.", file=sys.stderr)
        return

    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    system_prompt = load_system_prompt()
    results = []
    total_checks_all = 0
    total_passed_all = 0

    print(f"\n===== 자가 진단 시작 (총 {len(cases)}개 케이스) =====")
    
    for case in cases:
        case_id = case["id"]
        desc = case["description"]
        query = case["input_query"]
        criteria = case["eval_criteria"]

        print(f"-> [{case_id}] {desc} 테스트 진행 중...")
        
        # LLM 호출 및 응답 획득
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        try:
            response_msg = model.invoke(messages)
            response_text = response_msg.content
        except Exception as e:
            print(f"   🔴 [{case_id}] API 호출 실패: {e}", file=sys.stderr)
            continue

        # 채점 로직 구동
        case_score = 0
        case_total = 0
        failed_reasons = []

        for word in criteria.get("must_contain", []):
            case_total += 1
            if word in response_text:
                case_score += 1
            else:
                failed_reasons.append(f"필수 표현 누락: '{word}'")

        for word in criteria.get("must_not_contain", []):
            case_total += 1
            if word not in response_text:
                case_score += 1
            else:
                failed_reasons.append(f"보안/위배 단어 노출: '{word}'")

        for step in criteria.get("required_steps", []):
            case_total += 1
            if step in response_text:
                case_score += 1
            else:
                failed_reasons.append(f"필수 가이드 단계 누락: '{step}'")

        case_pass_rate = (case_score / case_total) * 100 if case_total > 0 else 100
        total_checks_all += case_total
        total_passed_all += case_score

        results.append({
            "id": case_id,
            "desc": desc,
            "pass_rate": case_pass_rate,
            "failed_reasons": failed_reasons,
            "is_passed": "🟢 PASS" if case_pass_rate == 100 else "🔴 FAIL",
            "snippet": response_text[:120].replace("\n", " ") + "..."
        })

    # 4. agent_result_report.md 파일 빌드 및 물리 디스크 쓰기
    overall_percentage = (total_passed_all / total_checks_all) * 100 if total_checks_all > 0 else 100
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_md = f"""# 📊 SRE 에이전트 자가 진단 평가 보고서 (Agent Self-Evaluation Report)

- **평가 수행 일시**: {current_time}
- **평가 대상 모델**: anthropic/claude-sonnet-5 (OpenRouter)
- **종합 Pass율**: {total_passed_all}/{total_checks_all} ({overall_percentage:.1f}%)

---

## 1. 종합 총평
> 이번 자동 자가 진단을 통해 에이전트 인프라 환경 스택(RHEL 8.5 / 128GB) 내에서의 프롬프트 준수 능력을 점검했습니다. 종합 Pass율은 {overall_percentage:.1f}%이며, 누락되거나 보안상 취약할 수 있는 마스킹 실패 요소를 아래와 같이 정량화하여 보고합니다.

---

## 2. 테스트 케이스별 상세 결과
"""

    for r in results:
        reasons_str = "\n".join([f"  - {reason}" for reason in r["failed_reasons"]]) if r["failed_reasons"] else "  - 없음"
        report_md += f"""
### [{r["id"]}] {r["desc"]}
- **결과**: {r["is_passed"]} (통과율: {r["pass_rate"]:.1f}%)
- **발견된 문제점/누락 항목**:
{reasons_str}
- **출력 요약 (Snippet)**:
  ```text
  {r["snippet"]}