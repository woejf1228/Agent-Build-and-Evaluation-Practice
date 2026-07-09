# Agent Memory: SRE 장애 대응 및 런북 가이드

## 1. 주요 에러 코드 및 가설 맵핑 힌트 (SRE Runbook Hints)
- **OutOfMemoryError (OOM):** - 가설: JVM 힙 메모리 부족 또는 컨테이너 리소스 제한(Limits) 도달
  - 추천 액션: `kubectl top pod` 확인 및 미들웨어 힙 덤프 추출 가이드 제안
- **Connection Timeout / Pool Exhausted:**
  - 가설: DB 커넥션 풀 고갈 또는 백엔드 구간 네트워킹 지연
  - 추천 액션: Tomcat/JEUS 설정 내 Connection Pool Max 값 검증 스크립트 제안
- **IBM MQ Channel Stopped / Depth Accumulation:**
  - 가설: 메시지 소비 서버 다운 또는 MQ 채널 연결 데드락
  - 추천 액션: IBM MQ `runmqsc` 기반 채널 상태 조회 명령어 제안

## 2. 장애 분석 표준 리포트 템플릿 (Mandatory Template Layer)
장애 분석 출력 시 아래 헤더 구조와 마크다운 서식을 무조건 준수하십시오.

```markdown
### [1. 장애 상황 요약]
- **대상 시스템:** SKT Swing / [세부 서비스명]
- **발생 시각:** [YYYY-MM-DD HH:MM:SS]
- **핵심 예외 명칭:** `[예: java.lang.OutOfMemoryError]`

### [2. 원인 가설 및 판별]
- **1순위 유력 가설:** [내용] (근거: 로그 OO번째 라인)
- **2순위 유력 가설:** [내용] (근거: `kubectl describe` 내 OO 메시지)

### [3. 긴급 진단 및 조치 가이드]
*주의: 모든 IP 주소와 계정은 플레이스홀더 처리할 것*
- **상태 진단 명령어:**
  ```bash
  kubectl describe pod <POD_NAME> -n swing

## Meta-Harness Optimization History
- 최신 평가일: 2026-07-09
- 현재 종합 Pass율: 85%

### 발견된 약점 및 보완 지침
- [Constraint] IBM MQ 장애 진단 시 `dspmq` 명령어를 누락하는 경향이 있음 -> 향후 IBM MQ 관련 로그 분석 시 반드시 `dspmq` 및 `runmqsc` 점검 단계를 가이드에 최우선 포함할 것.
- [Masking] K8S 네임스페이스명을 그대로 노출하는 실수가 있었음 -> `<NAMESPACE>` 형태로 철저히 마스킹할 것.
- [Output] 사용자가 장애 분석 결과를 파일로도 보관하고 싶어함 -> 장애 분석 리포트 작성 시, 채팅 응답과 함께 `/agent_result_report.md` 파일로도 생성/갱신(write_file 또는 edit_file)할 것. 동일 세션 내 재분석 시에는 새로 write_file 하여 최신 내용으로 덮어쓸 것.