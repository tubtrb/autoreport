## Autoreport v0.4.2 개발 일지

Version: `v0.4.2`
Release date: `2026-04-11`
Status: `draft`

이번 `v0.4.2`는 새 제품 범위를 크게 넓힌 버전이라기보다, 이미 열어 둔 hosted manual flow를 실제 사용자 기준으로 덜 깨지게 만든 안정화 버전입니다. 수동 절차 starter를 다른 AI에 넘겨 초안을 받아오는 흐름은 분명 빨랐지만, 응답이 거의 맞아도 YAML 들여쓰기 하나만 무너지면 바로 막히는 지점이 있었습니다. 이번 작업은 그 불안정한 경계선을 줄이는 데 집중했습니다.

## Live service

As of `2026-04-11`, the public site and hosted demo are available at:

- Home: `http://auto-report.org/`
- Guide: `http://auto-report.org/guide/`
- Updates: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo: `http://3.36.96.47/`

## 이번 버전에서 왜 이 작업이 중요했는가

공개 흐름의 핵심은 이미 정해져 있었습니다. 사용자는 built-in manual starter를 열고, 그 brief를 다른 AI에 넣고, 돌아온 YAML을 붙여 넣은 다음, 필요한 스크린샷을 맞춰 업로드하고 PowerPoint를 내려받습니다. 문제는 이 경로가 기능적으로는 맞아도, 다른 AI가 반환한 YAML의 들여쓰기만 조금 무너지면 사용자가 바로 실패로 만나게 된다는 점이었습니다.

이건 기능이 없어서 생기는 불만이라기보다, 이미 있는 기능이 마지막 한 걸음에서 너무 쉽게 무너지는 문제에 가까웠습니다. 그래서 `v0.4.2`는 화면을 더 복잡하게 늘리기보다, 이미 공개한 manual authoring 흐름을 더 안정적으로 유지하는 쪽을 선택했습니다.

## 이번 버전에서 공개 흐름이 어떻게 달라졌는가

- built-in manual starter의 AI brief를 더 엄격하게 다듬어 기대하는 응답 형태를 분명하게 안내합니다.
- `Check Draft`가 흔한 들여쓰기 붕괴를 먼저 복구한 뒤 구조를 점검할 수 있게 했습니다.
- 복구가 일어나면 수정된 YAML을 다시 편집기에 돌려주고, 사용자는 경고를 본 뒤 그대로 이어서 검토할 수 있습니다.
- `Refresh Preview`로 현재 YAML 기준 preview rail과 upload panel을 다시 맞출 수 있게 했습니다.
- public flow 안에서 `Slide Style Gallery`, `Add Slide`, `Delete`로 지원된 manual slide만 가볍게 추가하거나 제거할 수 있게 했습니다.
- screenshot upload는 계속 matching preview row에 맞춰 붙고, 다운로드 이름도 계속 `autoreport_demo.pptx`입니다.
- 결과적으로 "거의 맞는 초안이 사소한 포맷 문제 때문에 바로 버려지는" 상황이 줄어들었습니다.

이번 변화는 사용자가 새로운 개념을 배워야 하는 변화가 아닙니다. 같은 starter, 같은 draft editor, 같은 screenshot step, 같은 PPTX download 흐름 안에서 실패 확률을 줄이는 변화입니다. 모바일이나 휴대폰 지원 범위를 이번 릴리스에서 새로 확정한 것도 아닙니다. 공개 서비스에서는 이런 성격의 개선이 오히려 더 중요할 때가 많습니다.

## 공개 서비스와 문서 흐름을 다시 맞춘 이유

이번 작업에서는 기능 수정만으로 끝내지 않고, 그 흐름을 설명하는 release note, guide, 개발 일지도 함께 `v0.4.2` 기준으로 맞췄습니다. public site에서 읽는 문서는 hosted demo 사용자가 실제로 따라갈 수 있는 설명이어야 하고, 개발자용 운영 정보나 디버그 설명은 GitHub 쪽 문서로 남겨야 합니다.

그래서 이번 묶음에서는 public guide는 hosted demo 사용자 중심으로 유지하고, 서버 운영과 proof 절차는 별도의 handover 문서에서 계속 다루는 방향을 분명하게 했습니다. 공개 문서는 사용자에게 가까워지고, 운영 문서는 운영자에게 가까워지는 쪽이 더 건강한 구조라고 봤습니다.

## 현재 상태

- public site와 hosted demo 엔드포인트는 `2026-04-11` 기준으로 응답을 확인했습니다.
- `v0.4.2` 문서는 release note, guide, development log까지 한 세트로 준비했습니다.
- 이 글은 `v0.4.2` 후보 기준 정리이며, 공개 사이트 서사가 아직 `v0.4.1` 기준일 수 있다는 점을 전제로 둡니다.
- 공개 서비스가 이미 `v0.4.2`로 완전히 넘어갔다고 가정하지는 않습니다.

## 다음 단계

다음 단계는 분명합니다. `v0.4.2` 문서를 `autorelease`로 넘겨 public publishing 흐름을 맞추고, publish 서버에는 같은 버전의 hosted flow가 실제로 올라가도록 handover를 정리하면 됩니다. 이번 버전은 기능을 과하게 넓히기보다, 지금 공개한 흐름을 믿고 사용할 수 있게 만드는 데 의미가 있습니다.
