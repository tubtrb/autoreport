## Autoreport v0.3.1 개발 일지

기준 일자: `2026-04-04`

이번 `v0.3.1`은 큰 기능을 더 붙이는 버전이 아니라, 이미 공개한 `v0.3` 라인을 태그 기준으로 다시 단단하게 고정하는 버전이었습니다. `v0.3.0` 이후 브랜치 위에는 공개 홈페이지 동선 정리, 배포 정보 정합성, private `autorelease` handoff 보완 같은 후속 작업이 쌓였는데, 이 상태를 그냥 흘려보내기보다 `v0.3` 안정선으로 다시 묶어 두는 편이 더 명확하다고 판단했습니다.

특히 이번 정리에서 중요했던 점은 브랜치 이름이 아니라 공개 표면 자체를 다시 확인하는 일이었습니다. public 웹은 여전히 text-first starter flow를 기본 경로로 유지하고, 이미지가 필요한 draft는 debug 앱이나 CLI로 보내는 쪽이 현재 제품 설명과 실제 동작을 가장 덜 왜곡하는 상태였습니다. 그래서 `v0.3.1`은 새로운 방향 전환이라기보다, 지금 보여 주는 경계를 더 분명하게 적는 패치 릴리즈에 가깝습니다.

## 이번 버전에서 정리한 것

- public 홈페이지가 text-first 흐름이라는 점을 release-facing 문서와 테스트 기준에 다시 맞췄습니다.
- image-backed draft는 계속 debug 앱과 CLI 경로에 남기고, public 앱에서는 그 경계를 더 분명하게 유지했습니다.
- live service 주소와 handoff 문구가 `autoreport`와 `autorelease`에서 같은 기준을 보도록 정리했습니다.
- `v0.3.0` 이후 누적된 공개면 보완을 `v0.3.1` 태그 기준으로 다시 고정할 수 있게 만들었습니다.

## 왜 패치 릴리즈로 묶었는가

이번 변경은 `v0.4`처럼 새로운 기능선을 여는 작업이 아니었습니다. CLI의 contract-first 흐름이나 debug 앱의 역할은 그대로 두고, public 홈페이지에서 무엇을 바로 지원한다고 말할 수 있는지만 더 엄격하게 다듬은 쪽에 가까웠습니다. 그래서 minor를 올리기보다 `v0.3.1`로 묶는 편이 실제 변화의 크기와 더 잘 맞았습니다.

또 하나의 이유는 관리 기준입니다. 이번에는 브랜치 이름을 늘리기보다, 이미 공개 가능한 상태로 확인된 선을 태그로 남기는 쪽이 더 낫다고 봤습니다. 그렇게 해야 이후 `v0.4` 작업이 들어와도 `v0.3` 안정선이 어디였는지 바로 설명할 수 있습니다.

## 현재 상태

이제 `v0.3.1` 기준 상태는 다음처럼 이해하면 됩니다.

- semantic version은 `0.3.1`입니다.
- public 웹은 text-first starter flow를 기본으로 유지합니다.
- image-backed draft와 더 깊은 inspection은 debug 앱과 CLI에서 계속 다룹니다.
- release-facing guide, release note, devlog, handoff 기준이 같은 서비스 정보 블록을 공유합니다.

## 실제 검증 기준

이번 패치 릴리즈 정리는 아래 검증 기준에 맞춰 확인했습니다.

```bash
.\venv\Scripts\python.exe -m unittest tests.test_web_app tests.test_web_debug_app tests.test_autorelease_handoff
```

이 검증은 public 앱이 image 경로를 기본 동선에서 계속 막고 있는지, debug 앱은 image-backed draft를 계속 허용하는지, 그리고 handoff rewrite가 현재 release-facing 문구와 서비스 정보 기준을 유지하는지를 함께 확인합니다.

## 다음 단계

- `v0.3.1` 태그와 handoff 결과를 기준으로 `v0.3` 안정선을 마무리하기
- public sample deck 같은 외부 배포 자산은 별도 릴리즈 자산으로 다루기
- 새로운 기능 확장은 `v0.4` 선으로 넘기고 `v0.3` 표면은 더 넓히지 않기

이번 `v0.3.1`은 기능을 과장해서 더하는 버전이 아니라, 이미 공개해 둔 제품 표면을 태그 기준으로 다시 고정하는 버전이었습니다. 덕분에 이제 `v0.3`는 어디까지가 안정선이고, 그 다음 변화는 어디서부터 시작되는지 더 선명하게 설명할 수 있게 됐습니다.
