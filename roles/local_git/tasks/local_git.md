# 🗂 로컬 작업 저장소 부트스트랩 (Ansible)
- Airflow 코드(`data_layer_airflow`)를 담는 **클라이언트 쪽 git 저장소를 한 번 만들어 준다**
- `git init` → `.gitignore` → `remote add origin` → 최초 커밋 → 최초 push 까지
- **커밋이 이미 있으면 아무것도 하지 않는다** — 이후의 수정→커밋→push 는 사람의 몫
---
<br>

## 🧩 왜 필요한가

Terraform `304-airflow` 의 Airflow 파드에는 **DAG·커스텀 패키지가 없다.** 이미지에서 걷어냈고,
파드마다 붙은 git-sync 사이드카가 저장소에서 받아 온다. 그 저장소는 두 조각이다.

| 조각 | 무엇 | 만드는 주체 |
|---|---|---|
| 서버 쪽 bare 저장소 (`/srv/git/airflow.git`) | 받아 주는 곳 | **Terraform `303-git`** 의 initContainer |
| 클라이언트 쪽 작업 저장소 (`.git` · origin) | 밀어 넣는 곳 | **이 롤** |

서버 쪽만 있으면 저장소는 비어 있고, 클라이언트 쪽만 있으면 밀어 넣을 곳이 없다.

---
<br>

## ⚙️ 선행 조건

1. **`303-git` apply 완료** (파드 Running) — 최초 push 를 받아 줄 대상이 있어야 한다
2. **`etc_hosts` 롤 적용** — `data-layer-git` 이름이 풀려야 한다
   (`data_layer_dns_names` 에 포함돼 있다)

둘 중 하나라도 빠지면 8번 태스크(최초 push)에서 연결 실패로 멈춘다.

---
<br>

## 🔒 .gitignore 가 막는 것

```yaml
local_git_ignore:
  - airflow.env          # ⚠ MinIO 비밀번호 · fernet 키 · JWT 시크릿
  - scripts/airflow.conf # ⚠ COLLECTOR_CRYPTO_KEY
  - logs/
  - __pycache__/
  - "*.pyc"
```

앞의 두 줄은 **반드시** 제외 대상이다. 저장소는 클러스터 안에서 인증 없이 clone 되므로
(`git daemon --export-all`) 여기 비밀값이 들어가면 그대로 노출된다.
런타임 값은 Secret `airflow-env` 에서 오므로 저장소에 없어도 동작에 지장이 없다.

---
<br>

## 🔁 멱등성 — 무엇을 건너뛰는가

| 태스크 | 두 번째 실행에서 |
|---|---|
| `git init` | `creates: .git` 로 건너뜀 |
| `.gitignore` | 내용이 같으면 `changed=0` |
| `git config user.*` | 항상 실행하되 `changed_when: false` |
| `remote add/set-url` | 주소가 이미 같으면 건너뜀 |
| **최초 커밋 / push** | **커밋이 하나라도 있으면 건너뜀** |

마지막 줄이 이 롤의 핵심 규칙이다. 그렇게 하지 않으면 Ansible 을 돌릴 때마다
**작업 중이던 변경분이 임의의 메시지로 커밋되어** 이력이 오염된다.

---
<br>

## 🔗 짝이 되는 값들 (어긋나면 조용히 깨진다)

| 이 롤 | 짝 | 어긋나면 |
|---|---|---|
| `local_git_branch: master` | `304-airflow` 의 `git_ref` | git-sync 가 ref 를 못 찾아 파드가 init 에서 멈춤 |
| `local_git_remote_url` (NodePort) | `304-airflow` 의 `git_repo` (ClusterIP FQDN) | 같은 저장소를 가리켜야 한다 — 바깥/안 주소만 다르다 |
| `local_git_repo_dir` | `git_repo` 경로 구조 | `DAGS_FOLDER=/git/repo/dags` 기준이라 저장소 루트가 `data_layer_airflow` 여야 한다 |

---
<br>

## ▶️ 실행

```bash
ansible-playbook -i host.yml local_git_ansible.yml
```

확인:

```bash
git ls-remote git://data-layer-git:30418/airflow.git
kubectl exec -n data-layer deploy/airflow-scheduler -c scheduler -- ls /git/repo/dags
```

이후 일상 작업:

```bash
cd /my_project/data_pipeline/data_layer_airflow
vi dags/collector_dag.py
git add -A && git commit -m "fix: ..." && git push   # 약 10초 뒤 파드에 반영
```
