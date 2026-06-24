# planner.py — [DEPRECATED] 이 파일의 build_plan()은 사용되지 않습니다.
#
# [대체 위치]
#   leader.py — LeaderAgent.run() 내부에서 concept 탐지·라우팅·플랜 생성을 직접 수행한다.
#   leader.py가 planner.py 보다 기능이 우수하다:
#     - 온톨로지 관계 확장 (_expand_via_relations) 포함
#     - 의도(intent) 분석 결과를 concept 검색에 활용
#     - Short Memory(Redis 이전 대화)를 컨텍스트에 포함
#
# [이 파일을 참조하는 곳]
#   없음. ai_gateway.py → LeaderAgent → 내부 처리.
#
# [삭제 조건]
#   이 파일은 다음 조건이 모두 충족되면 삭제한다:
#     1. leader.py 의 플래닝 로직이 안정화됨
#     2. build_plan()을 직접 호출하는 외부 코드가 없음을 확인
