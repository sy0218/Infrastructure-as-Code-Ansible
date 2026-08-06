# 🛠 Ansible 기반 서버 구성 자동화 플랫폼 (IaC)

**Ansible 기반 IaC로 인프라를 코드로 선언하고,
OS 및 실행 환경을 자동으로 구성하는 프로젝트 입니다.**

Infrastructure as Code(IaC) 기반으로 **인프라 환경을 코드로 정의하여 재현성을 확보**하고, **재사용성과 확장성**을 고려한 **표준화된 서버 구성 자동화**를 목표로 합니다.

---
</br>

## ✨ 주요 특징
- **Role 기반 모듈 구조** — 기능 단위로 분리된 38개 롤을 조합해 서버 구성
- **단계별 플레이북** — OS 기본 → K8s → 부가 도구 → 데이터 스토어까지 10개 플레이북으로 분리 실행
- **중앙 집중 변수** — 버전·경로·계정을 인벤토리(host.yml) 한 곳에서 관리 (롤에는 `defaults/`·`vars/` 없음)
- **멱등성 보장** — 재실행해도 안전, 변경이 필요한 항목만 적용
- **멀티서버 확장성** — 인벤토리에 서버만 추가하면 N대 동시 프로비저닝

---
</br>

## 📋 요구 사항
| 항목 | 내용 |
|------|------|
| OS | Ubuntu 24.04 |
| Control Node | 1대 (Ansible 설치 대상) |
| Managed Node | N대 (Control Node에서 SSH 접근 가능해야 함) |
| 계정 | 모든 서버에서 **sudo 사용 가능한 사용자 (필수)** |
| 노드 구성(기본) | ap(192.168.56.200) · s1(.201) · s2(.202) — 인벤토리 `Ubuntu_Servers` 기준 3대 |
| Ansible 컬렉션 | `ansible.posix`, `community.general` — K8s 플레이북 필수, **자동 설치되지 않음**<br>`ansible-galaxy collection install ansible.posix community.general` |

---
</br>

## 📂 디렉토리 구조
```bash
Infrastructure-as-Code-Ansible/
├── ansible.cfg           # Ansible 공통 설정
├── host.yml              # 인벤토리 (서버 목록/변수)
├── ubuntu_ansible.yml    # 메인 플레이북 (서버 프로비저닝)
├── k8s_ansible.yml       # K8s 클러스터 구성 플레이북
├── longhorn_ansible.yml  # Longhorn 노드 사전 준비 플레이북
├── local_git_ansible.yml # Airflow 코드 저장소 부트스트랩 플레이북
├── terraform_ansible.yml # Terraform 설치 플레이북
├── docker_ansible.yml    # Docker 설치 플레이북
├── kafka_ansible.yml     # Kafka 설치 플레이북 (KRaft 로컬 클러스터)
├── postgresql_ansible.yml # PostgreSQL 설치 플레이북 (TimescaleDB 내장, 로컬 이관)
├── minio_ansible.yml     # MinIO 설치 플레이북 (SNSD, 로컬 이관)
├── neo4j_ansible.yml     # Neo4j 설치 플레이북 (Community Edition, 로컬 이관)
├── bin/
│   ├── ansible_setup.sh       # Ansible 설치 (Control Node용)
│   ├── start_ansible.sh       # 메인 플레이북 실행
│   ├── start_kubernetes.sh    # K8s 플레이북 실행
│   ├── start_longhorn.sh      # Longhorn 플레이북 실행
│   ├── start_local_git.sh     # 코드 저장소 부트스트랩 실행
│   ├── start_terraform.sh     # Terraform 플레이북 실행
│   ├── start_docker.sh        # Docker 플레이북 실행
│   ├── start_kafka.sh         # Kafka 플레이북 실행
│   ├── start_postgresql.sh    # PostgreSQL 플레이북 실행
│   ├── start_minio.sh         # MinIO 플레이북 실행
│   └── start_neo4j.sh         # Neo4j 플레이북 실행
├── COMMIT_CONVENTION.md  # 커밋 메시지 규칙
└── roles/                # 기능별 롤 (38종)
    ├── control/
    ├── packages/
    ├── java/
    └── ...
```
> **roles/ 디렉토리는 기능별 모듈 구조로 구성되며, 각 role은 tasks/main.yml을 기준으로 실행됩니다.**

---
</br>

## ⚙️ Ansible 설치 (Control Node만)
> ⚠️ **Ansible은 Control Node에만 설치합니다.**
```bash
sudo /my_project/Infrastructure-as-Code-Ansible/bin/ansible_setup.sh
```

---
</br>

## 🚀 Ansible 실행
Ansible 프로젝트 홈 디렉토리의 **절대 경로**를 인자로 전달하여 실행합니다.

**실행 순서** — 앞 단계가 뒤 단계의 전제입니다.
> ① 서버 프로비저닝 → ② K8s 클러스터 → ③ Longhorn·Terraform·Docker → ④ Kafka·PostgreSQL·MinIO·Neo4j(로컬 데이터 스토어) → ⑤ 코드 저장소(**Terraform `303-git` 적용 후**)

```bash
# ① 서버 프로비저닝 (ubuntu_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_ansible.sh /my_project/Infrastructure-as-Code-Ansible

# ② K8s 클러스터 구성 (k8s_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_kubernetes.sh /my_project/Infrastructure-as-Code-Ansible

# ③ Longhorn 노드 사전 준비 (longhorn_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_longhorn.sh /my_project/Infrastructure-as-Code-Ansible

# ③ Terraform 설치 (terraform_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_terraform.sh /my_project/Infrastructure-as-Code-Ansible

# ③ Docker 설치 (docker_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_docker.sh /my_project/Infrastructure-as-Code-Ansible

# ④ Kafka 설치 (kafka_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_kafka.sh /my_project/Infrastructure-as-Code-Ansible

# ④ PostgreSQL 설치 (postgresql_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_postgresql.sh /my_project/Infrastructure-as-Code-Ansible

# ④ MinIO 설치 (minio_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_minio.sh /my_project/Infrastructure-as-Code-Ansible

# ④ Neo4j 설치 (neo4j_ansible.yml)
/my_project/Infrastructure-as-Code-Ansible/bin/start_neo4j.sh /my_project/Infrastructure-as-Code-Ansible

# ⑤ Airflow 코드 저장소 부트스트랩 (local_git_ansible.yml)
#    ⚠ Terraform 303-git apply 뒤, 304-airflow apply 앞에서만 실행
/my_project/Infrastructure-as-Code-Ansible/bin/start_local_git.sh /my_project/Infrastructure-as-Code-Ansible
```
> ⚠️ **반드시 Ansible 프로젝트의 절대 경로를 인자로 전달해서 실행하세요.**
> (`ansible.cfg`의 inventory·roles_path가 상대 경로라 프로젝트 루트에서 실행돼야 합니다 — `start_*.sh`가 `cd`를 대신 해줍니다.)

---
</br>

## 🔧 공통 설정 (ansible.cfg)
실행 옵션을 한 곳에 모아 CLI 옵션 없이 동일한 동작을 보장합니다.
- `inventory = host.yml` → 인벤토리 자동 지정 (`-i` 불필요)
- `roles_path = ./roles` → 롤 경로 (**상대 경로 — 프로젝트 루트에서 실행 필수**)
- `host_key_checking = False` → 최초 SSH 접속 시 호스트 키 확인 생략
- `pipelining = True` → SSH 파이프라이닝으로 실행 속도 향상
- `forks = 2` → 동시 실행 호스트 수 / `stdout_callback = yaml` → 출력 가독성

---
</br>

## 📑 인벤토리 (host.yml)
대상 서버 목록과 접속 정보, 롤에서 사용하는 변수를 정의합니다. **롤에는 `defaults/`·`vars/`가 없어 모든 변수가 여기 한 곳에 모여 있습니다.**
- **그룹 = 플레이북 단위** — 그룹에 서버를 추가/제거하는 것만으로 대상 확장
- 접속 계정, sudo 비밀번호, 설치 패키지 목록, 버전 핀, 포트, 계정·버킷 이름 등을 여기서 관리
- ⚠ **버전 핀·계정·포트는 Terraform 스택과의 계약이다** — 바꿀 때는 반드시 양쪽을 함께 고칠 것

| 그룹 | 대상 | 쓰는 플레이북 |
|------|------|----------------|
| `Ubuntu_Servers` | ap · s1 · s2 | ubuntu |
| `kubernetes` (`kubernetes_master`=ap / `kubernetes_workers`=s1·s2) | ap · s1 · s2 | k8s |
| `longhorn` / `docker` / `kafka` | ap · s1 · s2 | longhorn / docker / kafka |
| `postgres` / `minio` / `neo4j` | ap | postgresql / minio / neo4j |
| `terraform` / `local_git` | s2 | terraform / local_git |

---
</br>

## 📜 플레이북 (ubuntu_ansible.yml)
실행 흐름을 정의하는 메인 플레이북입니다.
- **Play 1** — Control Node 설정 (localhost, sshpass)
- **Play 2** — Ubuntu_Servers 그룹에 롤 20개 순차 적용
- **적용할 롤은 `roles:` 목록에서 선택**
- 순서 의존: `java` → `package_version_lock`(openjdk hold 대상) · `bash_common`(JAVA_HOME)
- ⚠ **스왑은 켠 채로 운영한다** — `disable_swap` 주석 / `enable_swap` 활성은 의도다(K8s LimitedSwap). 뒤집으면 K8s 플레이의 스왑 검증이 실패한다.
- `etc_hosts` 롤만 태그가 있어 단독 재실행 가능: `ansible-playbook ubuntu_ansible.yml --tags etc_hosts`

---
</br>

## 📜 K8s 플레이북 (k8s_ansible.yml)
K8s 클러스터(kubeadm + containerd + Calico) 구성 플레이북입니다.
- **Play 1** — 필수 Ansible 컬렉션 사전 검증 (Control Node)
- **Play 2** — kubernetes 그룹 공통 사전 준비 (k8s_prereq → containerd → k8s_packages), **`serial: 1` 로 한 대씩** — containerd 재시작이 그 노드의 컨테이너를 전부 흔들기 때문(s1은 docker도 containerd를 공유)
- **Play 3~4** — 컨트롤플레인 초기화(kubernetes_master) → 워커 조인(kubernetes_workers)
- 해체용 k8s_reset 플레이는 평소 **주석 상태** — 해체할 때만 위 K8s 롤을 주석 처리하고 이 플레이를 활성화
- ⚠ 컬렉션은 **검증만 하고 설치하지 않는다** — 없으면 `ansible-galaxy collection install ansible.posix community.general`
- ⚠ **kubeadm init/join 은 1회성이다** — `pod_subnet` 등을 바꿔도 재실행으로 반영되지 않는다(k8s_reset 으로 해체 후 재구축)

---
</br>

## 📜 Longhorn 플레이북 (longhorn_ansible.yml)
Longhorn(분산 블록 스토리지) 설치 전 노드 사전 준비 플레이북입니다.
- **Play 1** — longhorn 그룹 전 노드에 open-iscsi 설치 + multipathd 차단 + 데이터 경로 생성
- 버전과 데이터 경로는 인벤토리 `longhorn` 그룹에서 관리 (`open_iscsi_version`, `longhorn_data_path`)

---
</br>

## 📜 Terraform 플레이북 (terraform_ansible.yml)
Terraform 설치 플레이북입니다.
- **Play 1** — terraform 그룹에 HashiCorp 저장소 등록 + Terraform 설치/버전 고정
- 대상 호스트와 버전은 인벤토리 `terraform` 그룹에서 관리

---
</br>

## 📜 Docker 플레이북 (docker_ansible.yml)
Docker(docker.io + compose 플러그인) 설치 플레이북입니다.
- **Play 1** — docker 그룹에 docker.io/compose 설치·버전 고정 + 서비스 기동 + docker 그룹 추가
- 버전과 대상 계정은 인벤토리 `docker` 그룹에서 관리 (`docker_version`, `docker_compose_version`, `docker_users`)

---
</br>

## 📜 Kafka 플레이북 (kafka_ansible.yml)
Kafka(KRaft 3노드 로컬 클러스터) 설치 플레이북입니다 — ADR 0: 브로커는 K8s 가 아니라 로컬(systemd) 설치.
- **Play 1** — kafka 그룹 전 노드에 tarball 설치 + KRaft 구성 + systemd 기동 + JMX exporter
- **Play 2** — 한 노드(ap)에서 파이프라인 계약 토픽 생성(`--if-not-exists`)
- 버전·포트·토픽 목록은 인벤토리 `kafka` 그룹에서 관리 (`kafka_version`, `kafka_cluster_id`, `kafka_topic_list` 등)
- ⚠️ Kafka 4.0+ 브로커는 Java 17 필수 — java 롤(`java_version: "17"`) 선행 적용 필요

---
</br>

## 📜 PostgreSQL 플레이북 (postgresql_ansible.yml)
PostgreSQL(TimescaleDB 내장) 설치 플레이북입니다 — ADR 0(Kafka)의 판단을 데이터 스토어에도 적용, K8s 가 아니라 로컬(systemd) 설치.
- **Play 1** — `postgres` 그룹(ap)에 postgresql-16 + TimescaleDB 설치 → DB 3종(`airflow`/`data_layer`/`iceberg_catalog`) + `data_pipeline` 스키마 + 계보 하이퍼테이블 부트스트랩
- 버전·포트·계정·DB 목록은 인벤토리 `postgres` 그룹에서 관리
- 클러스터 파드가 노드 IP 로 직접 붙으므로 `listen_addresses='*'` + `pg_hba` 에 `pod_subnet`·`node_cidr` 을 함께 연다
- compose 의 `initdb.d/01·02·03` 을 이 플레이북이 대체한다 (이미지가 사라졌으므로 여기가 DDL 의 단일 원본)
- ⚠️ **계정 이름이 곧 계약이다** — `postgres_superuser` 는 Terraform `300-data-layer-base`·`304-airflow` 의 `secrets.auto.tfvars` 와 글자 그대로 같아야 한다. 갈리면 airflow init Job 이 `db check` 에서 5분씩 7회 재시도 후 죽는다.
- ⚠️ Terraform `304-airflow` 는 이 플레이북이 먼저 적용돼 있어야 init Job 이 통과한다.

---
</br>

## 📜 MinIO 플레이북 (minio_ansible.yml)
MinIO(SNSD) 설치 플레이북입니다 — ADR 0(Kafka)의 판단을 데이터 스토어에도 적용, K8s 가 아니라 로컬(systemd) 설치.
- **Play 1** — `minio` 그룹(ap)에 MinIO(SNSD) + mc 설치 → 버킷 3종(`config`/`warehouse`/`airflow-logs`) 생성 + config 버킷 시드 주입
- 버전·포트·계정·버킷 목록은 인벤토리 `minio` 그룹에서 관리
- compose 의 `minio-init` 서비스를 이 플레이북이 대체한다 (이미지가 사라졌으므로 여기가 버킷의 단일 원본)
- ⚠ **시드 원본은 Control Node 의 경로다** — `minio_seed_src`(`/my_project/data_pipeline`)의 `config/`·`schemas/`·`data_layer_debezium/connect_json/` 가 없으면 시드 주입 태스크에서 멈춘다
- ⚠ `airflow-logs` 버킷이 없으면 Airflow 태스크는 정상 종료해도 로그가 조용히 사라진다
- ⚠️ **계정·버킷 이름이 곧 계약이다** — `minio_root_user` 는 Terraform `300-data-layer-base`·`304-airflow` 의 `secrets.auto.tfvars` 와 글자 그대로 같아야 한다.
- ⚠️ MinIO 바이너리는 `latest` 가 아니라 `archive/<태그>` 를 받으므로, 핀을 올리기 전 해당 태그의 실존을 확인할 것.

---
</br>

## 📜 Neo4j 플레이북 (neo4j_ansible.yml)
Neo4j(Community Edition) 설치 플레이북입니다 — ADR 0(Kafka)의 판단을 데이터 스토어에도 적용, K8s 가 아니라 로컬(systemd) 설치.
- **Play 1** — `neo4j` 그룹(ap)에 Neo4j CE + cypher-shell 설치·버전 고정 → Bolt(7687)/HTTP(7474) 공개 + 초기 비밀번호 각인 + systemd 기동
- 버전·포트·계정·메모리는 인벤토리 `neo4j` 그룹에서 관리
- compose 의 `data_layer-graph` 서비스를 이 플레이북이 대체한다 (이미지가 사라졌으므로 여기가 그래프 서버의 단일 원본)
- **UNIQUE 제약 27종은 이 플레이북이 만들지 않는다** — 컨슈머(`cdm_consumer_graph/constraints.py`)가 기동 시 1회 생성한다
- ⚠️ **계정·비밀번호가 곧 계약이다** — `neo4j_user`/`neo4j_password` 는 Terraform `300-data-layer-base` 의 `secrets.auto.tfvars`(`platform_neo4j_user`/`platform_neo4j_password`)와 글자 그대로 같아야 한다. 갈리면 서버는 멀쩡한데 `cdm-consumer-graph` 만 조용히 인증 실패한다.
- ⚠️ **비밀번호는 최초 기동 전에 1회 각인된다** — 나중에 `host.yml` 값을 바꿔도 재실행으로는 반영되지 않는다(`cypher-shell` 로 `ALTER USER` 직접 실행).
- ⚠️ **버전 핀은 되돌릴 수 없다** — Neo4j 는 상위 버전이 연 스토어를 하위 버전으로 다시 열지 못한다.
- ⚠️ Neo4j 5 는 Java 17 이상 필수 — java 롤(`java_version: "17"`) 선행 적용 필요 (Kafka 와 같은 JDK)

---
</br>

## 📜 코드 저장소 플레이북 (local_git_ansible.yml)
Airflow 코드(`data_layer_airflow`)를 담는 **클라이언트 쪽 git 저장소**를 한 번 만들어 주는 플레이북입니다.
- **Play 1** — `local_git` 그룹(s2)에 `git init` → `.gitignore` → origin → 최초 커밋 → 최초 push
- ⚠️ **실행 시점이 다른 플레이북과 다르다** — 노드 준비 단계가 아니라 Terraform **`303-git` apply 뒤, `304-airflow` apply 앞**이다. push 대상이 클러스터 안 파드라서, 저장소가 비어 있으면 airflow 파드의 git-sync 가 init 에서 멈춘다.
- ⚠️ **부트스트랩 전용이다** — 커밋이 하나라도 있으면 최초 커밋·push 를 건너뛴다. 매 실행마다 작업 중이던 변경분을 임의 메시지로 커밋해 이력을 오염시키지 않기 위함이다.
- ⚠️ **`airflow.env`·`scripts/airflow.conf` 는 `.gitignore` 고정 대상** — 저장소는 클러스터 안에서 인증 없이 clone 되므로(`git daemon --export-all`) 비밀번호·fernet 키가 그대로 노출된다. 런타임 값은 Secret `airflow-env` 에서 온다.
- ⚠️ 선행 조건: `303-git` 파드 Running + `etc_hosts` 롤 적용(`data-layer-git` 이름 해석). 둘 중 하나라도 없으면 첫 태스크에서 원인을 알려주며 멈춘다.
- 이후 수정은 사람이 한다: `git add -A && git commit && git push` → 약 10초 뒤 파드에 반영

---
</br>

## 📚 Roles 설명
---
### 🔹 control → [`📂 control.md`](./roles/control/tasks/control.md)
- Control Node에서 password 기반 SSH 통신을 위해 sshpass 설치 및 검증 수행
---

### 🔹 root_password → [`📂 root_password.md`](./roles/root_password/tasks/root_password.md)
- root 계정 비밀번호 설정
---

### 🔹 packages → [`📂 packages.md`](./roles/packages/tasks/packages.md)
- 기본 패키지 일괄 설치 (인벤토리 `install_packages` 기준)
---

### 🔹 pip_packages → [`📂 pip_packages.md`](./roles/pip_packages/tasks/pip_packages.md)
- Python 패키지 설치 (인벤토리 `pip_packages` 기준)
---

### 🔹 nicname → [`📂 nicname.md`](./roles/nicname/tasks/nicname.md)
- 네트워크 인터페이스 이름을 `eth*` 로 고정 (GRUB `net.ifnames=0 biosdevname=0`, 재부팅 후 적용)
---

### 🔹 cloud_init → [`📂 cloud_init.md`](./roles/cloud_init/tasks/cloud_init.md)
- cloud-init 설정 (초기화 간섭 방지)
---

### 🔹 ufw → [`📂 ufw.md`](./roles/ufw/tasks/ufw.md)
- UFW 방화벽 비활성화 (서비스 중지 + 부팅 자동시작 해제)
---

### 🔹 locale_ko → [`📂 locale_ko.md`](./roles/locale_ko/tasks/locale_ko.md)
- 한국어 로케일 설정
---

### 🔹 ssh_root_login → [`📂 ssh_root_login.md`](./roles/ssh_root_login/tasks/ssh_root_login.md)
- root SSH 로그인 허용 (`PermitRootLogin yes`)
---

### 🔹 timezone → [`📂 timezone.md`](./roles/timezone/tasks/timezone.md)
- 타임존 설정 (Asia/Seoul)
---

### 🔹 ntp → [`📂 ntp.md`](./roles/ntp/tasks/ntp.md)
- NTP 시간 동기화 설정 (`0.kr.pool.ntp.org`)
---

### 🔹 open_files → [`📂 open_files.md`](./roles/open_files/tasks/open_files.md)
- open files(ulimit) 제한 설정
---

### 🔹 logrotate → [`📂 logrotate.md`](./roles/logrotate/tasks/logrotate.md)
- 로그 로테이션 설정
---

### 🔹 shell_default → [`📂 shell_default.md`](./roles/shell_default/tasks/shell_default.md)
- 기본 쉘 설정 (`/bin/sh` → bash)
---

### 🔹 java → [`📂 java.md`](./roles/java/tasks/java.md)
- OpenJDK 설치 (인벤토리 `java_version` 기준)
---

### 🔹 disable_swap → [`📂 disable_swap.md`](./roles/disable_swap/tasks/disable_swap.md)
- 스왑 비활성화 — ⚠ **평소 플레이북에서 주석 상태**. K8s 를 스왑 켠 채(LimitedSwap) 운영하므로 활성화하면 K8s 검증이 실패한다
---

### 🔹 enable_swap → [`📂 enable_swap.md`](./roles/enable_swap/tasks/enable_swap.md)
- 스왑 파일 생성 및 활성화 (인벤토리 `swap_file_path`, `swap_size_mb` 기준)
---

### 🔹 package_version_lock → [`📂 package_version_lock.md`](./roles/package_version_lock/tasks/package_version_lock.md)
- 커널·Java 패키지 버전 고정 (hold) — `java_version` 기준이라 java 롤 뒤에 와야 한다
---

### 🔹 package_update_lock → [`📂 package_update_lock.md`](./roles/package_update_lock/tasks/package_update_lock.md)
- 자동 업데이트 잠금
---

### 🔹 bash_common → [`📂 bash_common.md`](./roles/bash_common/tasks/bash_common.md)
- bash 공통 환경 설정 (환경변수 파일 + 탭 완성 + alias + 프롬프트)
---

### 🔹 ssh_keygen → [`📂 ssh_keygen.md`](./roles/ssh_keygen/tasks/ssh_keygen.md)
- Ed25519 키 생성 + 전 노드 공개키 상호 배포 (노드 간 비밀번호 없는 SSH)
---

### 🔹 etc_hosts → [`📂 etc_hosts.md`](./roles/etc_hosts/tasks/etc_hosts.md)
- /etc/hosts 호스트 등록 — **기준은 '장애 전환을 누가 하느냐'** 다
  - ① 노드 IP 계열(`data_layer_dns_names` — git·minio-console·neo4j, **노드당 1줄**):
    이름 하나가 노드 IP 를 전부 갖고 전환은 클라이언트가 한다(죽은 IP면 TCP 타임아웃 대기).
    git 은 Host 헤더가 없어 인그레스에 못 태우고, minio-console·neo4j 는 K8s 밖 서비스라 여기 남는다
  - ② VIP 계열(`data_layer_vip_dns_names` — harbor·kafka-ui·airflow·api·grafana·prometheus, **총 1줄**):
    전부 `ingress_vip` 하나를 가리키고 전환은 MetalLB 가 한다. 구분은 인그레스가 Host 헤더로 한다
- ⚠ **한 이름을 두 계열에 동시에 넣지 말 것** — 클라이언트가 아무 데나 붙어 증상이 매번 달라진다
  (검증 assert 도 기대 개수가 달라서 — 이름 수 × 노드 수 vs 이름 수 × 1 — 태스크가 분리돼 있다)
- 이 롤만 태그가 있어 단독 재실행이 가능하다: `ansible-playbook ubuntu_ansible.yml --tags etc_hosts`
- ⚠ **접속하는 PC 의 hosts 파일은 이 롤의 관리 대상이 아니다**(노드 3대만 대상) — 브라우저로
  Grafana·Airflow 등에 접속하려면 PC 의 hosts 에 아래를 직접 넣어야 한다
  ```text
  192.168.56.200 data-layer-git data-layer-minio-console data-layer-neo4j
  192.168.56.201 data-layer-git data-layer-minio-console data-layer-neo4j
  192.168.56.202 data-layer-git data-layer-minio-console data-layer-neo4j
  192.168.56.240 data-layer-harbor data-layer-kafka-ui data-layer-airflow data-layer-api data-layer-grafana data-layer-prometheus
  ```
---

### 🔹 collection_check → [`📂 collection_check.md`](./roles/collection_check/tasks/collection_check.md)
- k8s 롤에 필요한 Ansible 컬렉션 사전 검증 (인벤토리 `required_collections` 기준) — **검증만 하고 설치하지 않는다**(없으면 `ansible-galaxy collection install`)
---

### 🔹 k8s_prereq → [`📂 k8s_prereq.md`](./roles/k8s_prereq/tasks/k8s_prereq.md)
- K8s 사전 준비 — 커널 모듈(overlay/br_netfilter) + sysctl + cgroup v2 검증
---

### 🔹 containerd → [`📂 containerd.md`](./roles/containerd/tasks/containerd.md)
- 컨테이너 런타임 containerd + runc 설치·버전 고정 + SystemdCgroup 활성화 + HTTP 사설 레지스트리 허용(certs.d) + 파드 샌드박스(pause) 이미지 사전 확보 (인벤토리 `containerd_version`, `runc_version`, `containerd_insecure_registries`, `sandbox_image` 기준)
- ⚠ containerd/runc 는 짝이 맞아야 한다 — 어긋나면 AppArmor 가 종료 신호를 막아 파드가 `Terminating` 에서 멈춘다(Ubuntu 버그 #2065423). 버전 변경 후 노드 재부팅 필요
---

### 🔹 k8s_packages → [`📂 k8s_packages.md`](./roles/k8s_packages/tasks/k8s_packages.md)
- kubeadm/kubelet/kubectl 설치·버전 고정 + node-ip 고정 (인벤토리 `kubernetes_package_version` 기준)
---

### 🔹 k8s_master → [`📂 k8s_master.md`](./roles/k8s_master/tasks/k8s_master.md)
- 컨트롤플레인 초기화(kubeadm init) + Calico 설치 — 스왑 유지(LimitedSwap) 구성
---

### 🔹 k8s_worker → [`📂 k8s_worker.md`](./roles/k8s_worker/tasks/k8s_worker.md)
- 워커 노드 kubeadm join + 전체 클러스터 검증 (노드 수/Ready/INTERNAL-IP/스왑 유지)
---

### 🔹 k8s_reset → [`📂 k8s_reset.md`](./roles/k8s_reset/tasks/k8s_reset.md)
- 클러스터 해체(kubeadm reset) + 잔여물 정리 — 평소 주석 상태, 해체 시에만 활성화
---

### 🔹 longhorn_prereq → [`📂 longhorn_prereq.md`](./roles/longhorn_prereq/tasks/longhorn_prereq.md)
- Longhorn 노드 사전 준비 — open-iscsi 설치·버전 고정 + multipathd 차단 + 데이터 경로 생성 (인벤토리 `open_iscsi_version`, `longhorn_data_path` 기준)
---

### 🔹 terraform → [`📂 terraform.md`](./roles/terraform/tasks/terraform.md)
- HashiCorp 저장소 등록 + Terraform 설치·버전 고정 (인벤토리 `terraform_version` 기준)
---

### 🔹 docker → [`📂 docker.md`](./roles/docker/tasks/docker.md)
- Docker(docker.io) + compose 플러그인 설치·버전 고정 + docker 그룹 추가 — docker-ce 대신 docker.io로 K8s containerd와 공존 (인벤토리 `docker_version`, `docker_compose_version`, `docker_users` 기준)
---

### 🔹 kafka → [`📂 kafka.md`](./roles/kafka/tasks/kafka.md)
- Kafka tarball 설치 + KRaft 3노드 클러스터 구성 + systemd 기동 + JMX Prometheus exporter — ADR 0에 따라 브로커는 K8s 대신 로컬 설치, Java 17 필수 (인벤토리 `kafka_version`, `kafka_cluster_id`, `kafka_data_dir` 등 기준)
---

### 🔹 kafka_topics → [`📂 kafka_topics.md`](./roles/kafka_topics/tasks/kafka_topics.md)
- 파이프라인 계약 토픽 16종 생성(`--if-not-exists`) + 존재 검증 — 한 노드에서만 실행, 파티션 수는 운영 중 변경 금지 (인벤토리 `kafka_topic_list`, `kafka_topic_partitions` 기준)
---

### 🔹 postgres → [`📂 postgres.md`](./roles/postgres/tasks/postgres.md)
- PostgreSQL 16 + TimescaleDB 설치·버전 고정 + DB 3종(`airflow`/`data_layer`/`iceberg_catalog`) · `data_pipeline` 스키마 · 계보 하이퍼테이블 부트스트랩 — ADR 0에 따라 K8s 대신 로컬 설치, compose `initdb.d` 대체 (인벤토리 `postgres_package_version`, `timescaledb_version`, `postgres_superuser`, `postgres_databases` 등 기준)
---

### 🔹 minio → [`📂 minio.md`](./roles/minio/tasks/minio.md)
- MinIO(단일 노드/단일 디스크) + mc 설치·버전 고정 + 버킷 3종(`config`/`warehouse`/`airflow-logs`) 생성 + config 버킷 시드 주입 — compose `minio` + `minio-init` 대체, `airflow-logs` 부재 시 태스크 로그가 조용히 사라진다 (인벤토리 `minio_version`, `minio_buckets`, `minio_seed_src` 등 기준)
---

### 🔹 neo4j → [`📂 neo4j.md`](./roles/neo4j/tasks/neo4j.md)
- Neo4j Community Edition + cypher-shell 설치·버전 고정 + Bolt(7687)/HTTP(7474) 공개 + 초기 비밀번호 각인 — ADR 0에 따라 K8s 대신 로컬 설치, compose `data_layer-graph` 대체, Java 17 필수. UNIQUE 제약은 컨슈머가 만든다 (인벤토리 `neo4j_package_version`, `neo4j_bolt_port`, `neo4j_password`, `neo4j_heap_size` 등 기준)
---

### 🔹 local_git → [`📂 local_git.md`](./roles/local_git/tasks/local_git.md)
- Airflow 코드 저장소 부트스트랩 — `git init -b master` + `.gitignore`(비밀값 제외) + origin 설정 + 최초 커밋/push. 서버 쪽 bare 저장소는 Terraform `303-git` 이 만들고 이 롤은 클라이언트만 준비한다. 커밋이 있으면 아무것도 하지 않는다 (인벤토리 `local_git_repo_dir`, `local_git_remote_url`, `local_git_branch`, `local_git_ignore` 등 기준)
---
