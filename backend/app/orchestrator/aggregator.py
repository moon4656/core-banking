# aggregator.py — [DEPRECATED] 이 파일의 aggregate()는 사용되지 않습니다.
#
# [대체 위치]
#   leader.py — LeaderAgent._summarize() 가 더 발전된 요약을 수행한다.
#   _summarize()가 aggregate() 보다 기능이 우수하다:
#     - 의도(intent)별 답변 스타일 지침 적용 (INQUIRY/COMPARISON/APPLICATION 등)
#     - Short Memory(Redis 이전 대화 최대 4턴)를 LLM 프롬프트에 포함
#     - Re-ranking된 결과를 우선 반영
#
# [이 파일을 참조하는 곳]
#   없음. executor.py 는 Tool 호출만 담당하고 요약은 leader.py 에 위임한다.
#
# [삭제 조건]
#   이 파일은 다음 조건이 모두 충족되면 삭제한다:
#     1. leader.py._summarize() 가 안정화됨
#     2. aggregate()를 직접 호출하는 외부 코드가 없음을 확인
