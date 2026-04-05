## Autoreport v0.3.0 개발 일지

기준 날짜: `2026-03-29`

이번 `v0.3.0` 마무리에서 중요한 변화는 기능을 더 붙이는 일이 아니라, 이미 만든 표면을 실제 릴리즈 기준에 맞게 다시 정리한 일이었습니다. 특히 공개 웹 데모는 한동안 번들 스크린샷, 업로드 ref, 이미지 슬롯 설명까지 한 화면에 같이 얹으면서 제품 소개와 실험용 기능이 섞여 있었는데, 이번 정리에서는 그 범위를 분명하게 나눴습니다. 이제 public 웹은 text-first starter flow에 집중하고, 이미지가 필요한 경로는 debug 앱과 CLI로 남겨 두는 쪽으로 정리됐습니다.

## 이번 버전에서 다시 정리한 것

- CLI 흐름은 `inspect-template -> scaffold-payload -> compile-payload -> generate` 순서로 그대로 유지했습니다.
- `report_content`, `authoring_payload`, `report_payload`라는 세 공개 입력 구조는 계속 유지하되, public 웹에서는 text/metrics 중심 starter만 보여 주도록 바꿨습니다.
- 사용자용 웹 앱과 개발용 debug 앱의 역할을 더 분명하게 나눴습니다.
- 가이드, 릴리즈노트, 개발 일지, handoff 문구를 지금 구현 기준에 맞게 다시 정리했습니다.
- private `autorelease` 쪽 stable guide와 update 글도 같은 방향으로 다시 넘길 수 있게 소스를 정리했습니다.

## 왜 public 웹에서 이미지 기능을 뺐는가

이번에 뺀 것은 Autoreport 전체의 이미지 지원이 아니라, 공개 웹 첫 화면에 붙어 있던 이미지 업로드 경험입니다. 실제 코드에서는 업로드 manifest, built-in screenshot ref, 사용자 업로드 ref, `text_image` 패턴 설명이 한 흐름에 같이 얹혀 있었고, 그 상태는 릴리즈 문구로 소개하기에는 불안정했습니다.

그래서 이번 판단은 단순했습니다. public 웹은 누구나 바로 이해할 수 있는 starter flow만 남기고, 이미지가 필요한 경로는 debug 앱과 CLI로 돌리는 편이 더 솔직하고 더 안정적이었습니다. 제품이 할 수 있는 것과 공개 표면에서 지금 바로 추천하는 경로를 분리해 두는 쪽이 결과적으로 안내도 더 쉬웠습니다.

## 공개 안내 문서를 어떻게 다시 맞췄는가

문서 쪽에서도 예전 이미지 업로드 중심 설명을 그대로 두면 코드보다 과장된 안내가 되어 버립니다. 그래서 이번 수정에서는 다음 기준으로 다시 썼습니다.

- 가이드는 public 웹을 text-first starter flow로 설명합니다.
- 릴리즈노트는 이미지 지원 자체를 없앤 것이 아니라, public 웹 기본 경로에서만 뺐다는 점을 분명하게 적습니다.
- 개발 일지는 왜 이 결정을 했는지와, debug/CLI 쪽으로 역할을 어떻게 나눴는지를 설명합니다.
- `autorelease` handoff는 stable guide와 versioned update 글이 같은 기준을 따르도록 다시 돌립니다.

이번 정리의 핵심은 "무엇을 만들었는가"보다 "무엇을 public surface로 남길 것인가"를 다시 맞춘 일이었습니다.

## 현재 상태

이제 `v0.3.0` 기준 상태는 더 단순해졌습니다.

- semantic version은 여전히 `0.3.0`입니다.
- public 웹 앱은 text-first starter manual만 보여 줍니다.
- 이미지가 필요한 draft는 debug 앱이나 CLI로 넘기도록 안내합니다.
- README, release-readiness, architecture note, versioned post source가 현재 구현과 다시 맞춰졌습니다.

## 실제 검증 기준

이번 정리는 문구만 바꾼 것이 아니라, public 웹과 debug 웹의 역할 차이를 테스트로 다시 잠근 상태에서 진행했습니다.

```bash
.\venv\Scripts\python.exe -m unittest tests.test_web_app tests.test_web_debug_app tests.test_autorelease_handoff
```

위 검증 기준은 public 웹에서 이미지 흐름이 빠졌는지, debug 앱에서는 이미지 경로가 계속 살아 있는지, 그리고 handoff rewrite가 새 문구 기준으로 계속 맞는지를 함께 확인합니다.

## 다음 단계

다음 단계는 기능을 더 붙이는 일보다, 이번에 다시 맞춘 설명을 실제 공개 글과 페이지에 반영하는 일입니다.

- `autorelease` 쪽 guide, release note, devlog를 다시 handoff 하기
- 필요하면 public guide용 sample deck 링크를 나중에 별도로 붙이기
- 이미지 기반 홈페이지 흐름이 정말 다시 필요해질 때만, 더 단단한 계약과 테스트를 붙여서 돌아오게 하기

이번 `v0.3.0` 마무리는 새로운 기능을 과장해서 더하는 버전이 아니라, 지금 보여 줄 수 있는 경로를 더 정확하게 설명하는 버전이었습니다. 공개 웹에서 무엇을 감추고 무엇을 남길지를 정리한 덕분에, 이제 제품 설명과 실제 동작이 다시 같은 방향을 보게 됐습니다.
