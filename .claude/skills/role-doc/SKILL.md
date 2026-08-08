---
name: role-doc
description: Ansible 롤의 tasks/main.yml을 만들거나 수정하면 같은 디렉토리에 한국어 문서 tasks/<롤이름>.md를 하우스 양식으로 생성·갱신한다
---

# 롤 문서(.md) 생성

`roles/<롤이름>/tasks/main.yml`을 새로 만들거나 수정했으면, 같은 디렉토리에 `tasks/<롤이름>.md`를 아래 양식으로 생성(이미 있으면 main.yml 소스와 어긋난 부분을 갱신)한다. 기준 예시: [roles/bash_common/tasks/bash_common.md](../../roles/bash_common/tasks/bash_common.md)

## 작성 순서

1. `roles/<롤이름>/tasks/main.yml`을 읽는다. `handlers/`·`templates/`가 있으면 함께 읽는다.
2. 롤이 참조하는 변수를 `group_vars/<그룹>.yml`에서 찾아 해당 변수만 발췌한다 (그룹은 이 롤을 쓰는 플레이북의 `hosts:`로 판단).
3. 아래 템플릿대로 작성한다. 문서 전체 한국어.

## 템플릿

````markdown
# <이모지> <한국어 제목> (<영문 이름>)
- <이 롤이 하는 일과 목적, 2~4개 불릿>
- <변수로 무엇이 제어되는지 한 줄 — "롤은 범용, 인벤토리가 동작 결정" 식>
---
<br>

## 🧩 main.yml
```yaml
<tasks/main.yml 소스 전체를 주석 포함 그대로 복사>
```
---
<br>

## 📌 group_vars 예시        ← 변수를 참조하는 롤만. 참조 변수만 주석과 함께 발췌
```yaml
<group_vars/<그룹>.yml 발췌>
```
---
<br>

## 🛠 작업 내용
### 1️⃣ <단계 제목>            ← main.yml의 단계 구분(주석 구획)대로 2️⃣3️⃣… 반복, 단계 사이 ---
- <무엇을 하는지 + 왜 그렇게 하는지(멱등성 근거, 가드, 함정)>
---
<br>

## 🧩 handlers/main.yml       ← handlers가 있는 롤만. 소스 그대로 + 한 줄 설명
---
<br>

## ✅ 실행 결과 예시
```bash
<마지막 assert 태스크의 대표 출력 — "Good!.. |" 메시지 포함>
```
````

## 규칙

- `## 🧩 main.yml` 코드 블록은 요약하지 말고 소스 **전체**를 그대로 넣는다 — 문서가 곧 소스 사본이다.
- `🛠 작업 내용`은 코드를 다시 서술하지 말고 **왜** 그 방식인지(멱등 모듈 선택, `creates=` 가드, 함정)를 쓴다.
- 이후 main.yml을 수정하면 이 .md와 README.md의 롤 설명도 함께 갱신한다 (CLAUDE.md의 문서 동기화 규칙).
