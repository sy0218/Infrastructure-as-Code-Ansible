# 🐘 PostgreSQL 설치 (TimescaleDB 내장 · 로컬 systemd)

- ADR 0(Kafka)의 판단을 데이터 스토어에도 적용한다 — **K8s 가 아니라 서버 로컬(systemd)**. 단일 인스턴스라 K8s 의 재스케줄 이득이 없고, 로컬 디스크 I/O 가 그대로 성능이다.
- 이 인스턴스 **하나가 DB 3개**를 담는다 (compose 시절 계약 승계).
  | DB | 용도 | 소비자 |
  |---|---|---|
  | `airflow` | Airflow 메타DB | Terraform `304-airflow` |
  | `data_layer` | `collect_job` / `realtime_source` / `data_lineage`(하이퍼테이블) | `305-api`, `307-pipeline` |
  | `iceberg_catalog` | pyiceberg SqlCatalog 메타데이터 | `cdm-consumer-warehouse` |
- compose 의 `initdb.d/01·02·03` 부트스트랩을 이 롤이 **대체**한다 (이미지가 사라졌으므로 이 롤이 DDL 의 단일 원본이다).
- ⚠️ **계정 통일** — `postgres_superuser` 는 compose 의 `POSTGRES_USER` 이자 `COLLECTOR_DB_USER` 다. Terraform `300-data-layer-base` · `304-airflow` 의 `secrets.auto.tfvars` 와 **글자 그대로** 같아야 한다. 갈리면 airflow init Job 이 `db check` 에서 5분씩 7회 재시도 후 죽는다.
- ⚠️ `shared_preload_libraries = 'timescaledb'` 가 없으면 `CREATE EXTENSION timescaledb` 가 실패한다. reload 로는 반영되지 않아 핸들러가 **restart** 를 건다.
- ⚠️ `listen_addresses = '*'` 여야 한다 — 로컬 설치라 Service DNS 가 없고 클러스터 파드가 노드 IP 로 직접 붙는다. `pg_hba` 는 파드 CIDR(`pod_subnet`)과 노드망(`node_cidr`) 둘 다 열어야 한다(hostNetwork 파드는 노드 IP 로 온다).
- 데이터 디렉토리는 배포판 기본값(`/var/lib/postgresql/16/main`)을 그대로 쓴다. 옮기려면 `pg_dropcluster`/`pg_createcluster` 가 필요해 별도 결정 사항으로 남겼다.

---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# PostgreSQL 설치 → Ubuntu 아카이브 postgresql-16 + TimescaleDB 확장
# -----------------------------------------------------
# ADR 0 (Kafka)와 같은 판단을 데이터 스토어에도 적용한다 — K8s 가 아니라 서버 로컬(systemd).
#   - 단일 인스턴스라 K8s 의 재스케줄 이득이 없고, 로컬 디스크 I/O 가 그대로 성능이다.
# compose 시절 계약 승계: 이 인스턴스 하나가 DB 3개를 담는다
#   airflow        — Airflow 메타DB (Terraform 304-airflow)
#   data_layer     — collector(collect_job/realtime_source) + 계보 하이퍼테이블
#   iceberg_catalog— pyiceberg SqlCatalog 메타데이터
# initdb.d/01·02·03 의 부트스트랩을 이 롤이 대체한다(이미지가 사라졌으므로).
#
# [주의] 계정 통일 — postgres_superuser 는 compose 의 POSTGRES_USER 이자 COLLECTOR_DB_USER 다.
#   Terraform 300-data-layer-base 의 postgres_user 와 반드시 같은 값이어야 한다.
# -----------------------------------------------------

# =========================================================================
# 1. TimescaleDB apt 저장소 등록 (deb822_repository 자체가 멱등)
#    → gpg --dearmor 파이프 금지(하우스 스타일) — 모듈의 signed_by 로 키를 직접 받는다
# =========================================================================
- name: "Add timescaledb apt repository"
  deb822_repository:
    name: timescaledb
    types: [deb]
    uris: "https://packagecloud.io/timescale/timescaledb/ubuntu/"
    suites: "{{ timescale_repo_release }}"
    components: [main]
    signed_by: "https://packagecloud.io/timescale/timescaledb/gpgkey"
    state: present
    enabled: true
  register: ts_repo
  retries: 3 # 외부 저장소 조회 불안정 대비
  delay: 10
  until: ts_repo is succeeded

# =========================================================================
# 2. 패키지 설치 (버전 고정 — host.yml 이 단일 출처)
#    → allow_change_held_packages: 아래 3번 hold 가 걸린 뒤에도 핀 변경이 수렴하도록
#    → timescaledb 는 loader 와 확장이 세트다. 로더가 없으면 shared_preload_libraries 가 실패한다.
# =========================================================================
- name: "Install postgresql and timescaledb"
  apt:
    name:
      - "postgresql-{{ postgres_version }}={{ postgres_package_version }}"
      - "postgresql-client-{{ postgres_version }}={{ postgres_package_version }}"
      - "timescaledb-2-postgresql-{{ postgres_version }}={{ timescaledb_version }}"
      - "timescaledb-2-loader-postgresql-{{ postgres_version }}={{ timescaledb_version }}"
      - "timescaledb-tools={{ timescaledb_tools_version }}"
    state: present
    update_cache: true
    allow_change_held_packages: true
    allow_downgrade: true
  register: pg_install
  retries: 3
  delay: 10
  until: pg_install is succeeded

# =========================================================================
# 3. 버전 고정 (dpkg_selections 자체가 멱등)
#    → apt upgrade 가 조용히 메이저 버전을 올리면 확장 ABI 가 깨져 기동 실패한다
# =========================================================================
- name: "Hold postgresql and timescaledb packages"
  dpkg_selections:
    name: "{{ item }}"
    selection: hold
  loop:
    - "postgresql-{{ postgres_version }}"
    - "postgresql-client-{{ postgres_version }}"
    - "timescaledb-2-postgresql-{{ postgres_version }}"
    - "timescaledb-2-loader-postgresql-{{ postgres_version }}"
    - timescaledb-tools

# =========================================================================
# 4. 서버 설정 (copy 자체가 멱등)
#    → Debian 계열 postgresql.conf 는 conf.d 를 include_dir 로 이미 읽는다 →
#      원본을 건드리지 않고 드롭인 한 장으로 끝낸다(패키지 업그레이드와 충돌 없음).
#    ⚠ shared_preload_libraries 가 없으면 CREATE EXTENSION timescaledb 가 실패한다.
#    ⚠ listen_addresses 는 '*' 여야 한다 — 클러스터 파드가 노드 IP 로 붙는다(Service DNS 없음).
#    → 데이터 디렉토리는 배포판 기본값(/var/lib/postgresql/16/main)을 그대로 둔다.
#      옮기려면 pg_dropcluster/pg_createcluster 가 필요해 별도 결정 사항으로 남긴다.
# =========================================================================
- name: "Create postgresql drop-in config"
  copy:
    dest: "/etc/postgresql/{{ postgres_version }}/main/conf.d/10-data-layer.conf"
    owner: postgres
    group: postgres
    mode: '0644'
    content: |
      # Ansible postgres 롤이 관리한다 — 수동 수정 금지
      listen_addresses = '{{ postgres_listen_addresses }}'
      port = {{ postgres_port }}

      # TimescaleDB 확장 로더 (미설정 시 CREATE EXTENSION 이 실패한다)
      shared_preload_libraries = 'timescaledb'
      # 랩 규모 — 튜닝 마법사 대신 기본값에서 접속 수만 올린다
      max_connections = {{ postgres_max_connections }}
      timezone = '{{ postgres_timezone }}'
      log_timezone = '{{ postgres_timezone }}'
  notify: restart postgresql

# =========================================================================
# 5. 접속 허용 (blockinfile 은 마커 사이만 관리 → 멱등)
#    → 파드 CIDR(10.244.0.0/16)과 노드망(192.168.56.0/24) 둘 다 필요하다:
#      hostNetwork 파드는 노드 IP 로, 일반 파드는 파드 IP 로 온다.
#    → scram-sha-256 — PG16 기본 password_encryption 과 맞춘다(md5 로 적으면 인증이 어긋난다).
# =========================================================================
- name: "Allow cluster access in pg_hba"
  blockinfile:
    path: "/etc/postgresql/{{ postgres_version }}/main/pg_hba.conf"
    marker: "# {mark} ANSIBLE MANAGED — data-layer cluster access"
    block: |
      host    all    all    {{ pod_subnet }}    scram-sha-256
      host    all    all    {{ node_cidr }}     scram-sha-256
    owner: postgres
    group: postgres
    mode: '0640'
  notify: restart postgresql

# =========================================================================
# 6. 서비스 기동 + 부팅 자동시작 (systemd 모듈 자체가 멱등)
# =========================================================================
- name: "Enable and start postgresql"
  systemd:
    name: "postgresql@{{ postgres_version }}-main"
    enabled: true
    state: started
    daemon_reload: true

# =========================================================================
# 7. 설정 변경분을 부트스트랩 전에 반영한다
#    → 핸들러는 기본적으로 플레이 끝에 실행되는데, 아래 8번부터가 이미 접속을 시도한다
# =========================================================================
- name: "Flush handlers before bootstrap"
  meta: flush_handlers

# =========================================================================
# 8. 기동 대기 — 재시작 직후 잠깐은 접속을 거절한다
# =========================================================================
- name: "Wait for postgresql to accept connections"
  command: "pg_isready -h 127.0.0.1 -p {{ postgres_port }}"
  register: pg_ready
  changed_when: false
  failed_when: false
  retries: 12 # 최대 1분
  delay: 5
  until: pg_ready.rc == 0

# =========================================================================
# 9. 부트스트랩 SQL 배치 (copy 자체가 멱등)
#    → CREATE ROLE/DATABASE 는 IF NOT EXISTS 를 지원하지 않아 \gexec 패턴을 쓴다.
#    ⚠ psql -c 로는 실행할 수 없다 — -c 는 문자열을 서버로 그대로 넘겨서
#      \gexec 같은 메타명령도, :'var' 치환도 동작하지 않는다(-f/stdin 에서만 된다).
#      compose 시절 initdb.d 가 heredoc 을 쓴 이유가 이것이다.
#    → 값을 psql 변수로 넘기는 이유: 비밀번호의 '!' 같은 특수문자가 %L 로 안전하게 인용된다.
# =========================================================================
- name: "Create role bootstrap sql"
  copy:
    dest: /etc/postgresql/data_layer_role.sql
    owner: postgres
    group: postgres
    mode: '0640'
    content: |
      -- Ansible postgres 롤이 관리한다 — 수동 수정 금지
      -- SUPERUSER 인 이유: compose 의 POSTGRES_USER 계약 승계(이 계정 하나가 DB 3개를 만들고 소유한다).
      SELECT format('CREATE ROLE %I WITH LOGIN SUPERUSER CREATEDB PASSWORD %L', :'db_user', :'db_password')
      WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'db_user')
      \gexec

      -- 이미 있던 롤도 host.yml 의 현재 비밀번호로 동기화한다(갈리면 airflow 접속이 깨진다)
      SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'db_user', :'db_password')
      \gexec

- name: "Create database bootstrap sql"
  copy:
    dest: /etc/postgresql/data_layer_database.sql
    owner: postgres
    group: postgres
    mode: '0640'
    content: |
      -- Ansible postgres 롤이 관리한다 — 수동 수정 금지
      SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_user')
      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name')
      \gexec

- name: "Create data-layer superuser role"
  command: >-
    psql -v ON_ERROR_STOP=1
    -v db_user={{ postgres_superuser | quote }}
    -v db_password={{ postgres_superuser_password | quote }}
    -d postgres -tA -f /etc/postgresql/data_layer_role.sql
  become_user: postgres
  register: role_create
  changed_when: "'CREATE ROLE' in role_create.stdout"
  no_log: true # 비밀번호가 인자로 들어간다

# =========================================================================
# 10. DB 3종 생성 (\gexec 패턴 — 이미 있으면 아무 일도 없다)
# =========================================================================
- name: "Create data-layer databases"
  command: >-
    psql -v ON_ERROR_STOP=1
    -v db_name={{ item | quote }}
    -v db_user={{ postgres_superuser | quote }}
    -d postgres -tA -f /etc/postgresql/data_layer_database.sql
  become_user: postgres
  loop: "{{ postgres_databases }}"
  register: db_create
  changed_when: "'CREATE DATABASE' in db_create.stdout"

# =========================================================================
# 11. collector DB 부트스트랩 SQL 배치 (copy 자체가 멱등)
#     → compose 시절 initdb.d/01_collector_db.sh + 03_data_lineage.sql 의 DDL 승계.
#       이미지가 사라졌으므로 이 파일이 이제 DDL 의 단일 원본이다.
#     → DROP 을 두지 않는다 — 재적용으로 적재된 계보가 날아가면 안 되기 때문.
#     ⚠ :"db_schema" / :'db_user' 는 psql 변수 인용이다(Jinja 아님 — 그대로 렌더된다).
# =========================================================================
- name: "Create collector bootstrap sql"
  copy:
    dest: /etc/postgresql/data_layer_collector_bootstrap.sql
    owner: postgres
    group: postgres
    mode: '0640'
    content: |
      -- Ansible postgres 롤이 관리한다 — 수동 수정 금지
      -- 전부 IF NOT EXISTS / if_not_exists => TRUE 라 재실행이 안전하다.

      -- 하이퍼테이블용. shared_preload_libraries 에 timescaledb 가 없으면 여기서 실패한다.
      CREATE EXTENSION IF NOT EXISTS timescaledb;

      CREATE SCHEMA IF NOT EXISTS :"db_schema" AUTHORIZATION :"db_user";

      -- 배치 수집 잡 (화면: 수집 › 배치 등록)
      CREATE TABLE IF NOT EXISTS :"db_schema".collect_job (
        job_id          bigserial PRIMARY KEY,
        job_name        text        NOT NULL,
        collector_type  text        NOT NULL,   -- CollectorFactory 키 (SFTP/PROCEDURE ...)
        processor_name  text        NOT NULL,   -- ProcessorFactory 키
        topic           text        NOT NULL,   -- 발행 Kafka 토픽
        config          jsonb       NOT NULL,   -- {date}/{hour} placeholder 포함, password 암호화
        enabled         boolean     NOT NULL DEFAULT true,
        run_hours       integer[]   NOT NULL    -- WHERE %s = ANY(run_hours)
      );
      ALTER TABLE :"db_schema".collect_job OWNER TO :"db_user";

      -- 실시간 수집 소스 (TCP_SOCKET | CDC). 상주형이라 run_hours 가 없다.
      CREATE TABLE IF NOT EXISTS :"db_schema".realtime_source (
        source_id    bigserial PRIMARY KEY,
        source_name  text        NOT NULL UNIQUE,
        source_type  text        NOT NULL,          -- TCP_SOCKET | CDC
        topic        text        NOT NULL,
        config       jsonb       NOT NULL,          -- password 는 암호화 저장
        enabled      boolean     NOT NULL DEFAULT true
      );
      ALTER TABLE :"db_schema".realtime_source OWNER TO :"db_user";

      -- 계보 (4-Tier 키). ingest_ts 가 청크 기준이라 엔티티당 상수여야 한다.
      CREATE TABLE IF NOT EXISTS :"db_schema".data_lineage (
        entity_key    text        NOT NULL,
        ingest_ts     timestamptz NOT NULL,
        event_ts      timestamptz NOT NULL,
        source_type   text        NOT NULL,   -- airflow|kafka|postgres|graph|vector|dlq
        source_detail text        NOT NULL,
        target_type   text        NOT NULL,
        target_detail text        NOT NULL,
        last_event_ts timestamptz,            -- NULL = 재처리 없음
        process_count int         NOT NULL DEFAULT 1,
        PRIMARY KEY (entity_key, ingest_ts, source_detail, target_detail)
      );
      ALTER TABLE :"db_schema".data_lineage OWNER TO :"db_user";

      SELECT create_hypertable(
        format('%I.%I', :'db_schema', 'data_lineage'),
        'ingest_ts',
        chunk_time_interval => INTERVAL '1 day',
        if_not_exists       => TRUE
      );

- name: "Bootstrap collector database objects"
  command: >-
    psql -v ON_ERROR_STOP=1
    -v db_schema={{ collector_db_schema | quote }}
    -v db_user={{ postgres_superuser | quote }}
    -d {{ collector_db_name | quote }}
    -f /etc/postgresql/data_layer_collector_bootstrap.sql
  become_user: postgres
  changed_when: false # 전부 IF NOT EXISTS — 출력으로 실제 변경 여부를 가를 수 없다

# =========================================================================
# 12. 검증 — 롤 규약: 상태 조회(changed_when: false) → assert
# =========================================================================
- name: "Check postgresql service status"
  command: "systemctl is-active postgresql@{{ postgres_version }}-main"
  register: pg_status
  changed_when: false
  failed_when: false
  retries: 3
  delay: 5
  until: pg_status.stdout == "active"

- name: "Check installed postgresql server version"
  command: "psql -tAc 'SHOW server_version'"
  become_user: postgres
  register: pg_version_check
  changed_when: false

- name: "Check databases exist"
  command: "psql -tAc 'SELECT datname FROM pg_database'"
  become_user: postgres
  register: pg_db_list
  changed_when: false

- name: "Check timescaledb extension in collector database"
  command: "psql -d {{ collector_db_name | quote }} -tAc \"SELECT extname FROM pg_extension WHERE extname = 'timescaledb'\""
  become_user: postgres
  register: pg_ts_ext
  changed_when: false

- name: "Check lineage hypertable"
  command: >-
    psql -d {{ collector_db_name | quote }} -tAc
    "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name = 'data_lineage'"
  become_user: postgres
  register: pg_hypertable
  changed_when: false

# 클러스터 파드가 실제로 붙는 경로(노드 IP + 계정)로 접속해 본다 —
# 127.0.0.1 만 확인하면 listen_addresses/pg_hba 오류를 못 잡는다.
- name: "Check remote connectivity with data-layer account"
  command: "psql -h {{ ansible_host }} -p {{ postgres_port }} -U {{ postgres_superuser }} -d {{ airflow_db_name }} -tAc 'SELECT 1'"
  environment:
    PGPASSWORD: "{{ postgres_superuser_password }}"
  register: pg_remote
  changed_when: false
  failed_when: false

- name: "Assert postgresql is ready for the data layer"
  assert:
    that:
      - pg_status.stdout == "active"
      - postgres_version in pg_version_check.stdout # 고정 버전 일치 (조건문 안에서는 {{ }} 금지)
      - airflow_db_name in pg_db_list.stdout_lines
      - collector_db_name in pg_db_list.stdout_lines
      - iceberg_catalog_db_name in pg_db_list.stdout_lines
      - "'timescaledb' in pg_ts_ext.stdout"
      - "'data_lineage' in pg_hypertable.stdout"
      - pg_remote.rc == 0 # 노드 IP + 계정으로 실제 접속 성공
    success_msg: "Good!.. | postgresql {{ postgres_version }} active — DB 3종({{ postgres_databases | join(', ') }}) + timescaledb + 원격접속 OK"
    fail_msg: "ERROR!.. | postgresql NOT ready → 노드에서 journalctl -u postgresql@{{ postgres_version }}-main -n 50 확인 (shared_preload_libraries / pg_hba / listen_addresses 순으로 의심)"
```

---
<br>

## 🔔 handlers/main.yml
```yaml
# -----------------------------------------------------
# postgresql 재시작 핸들러 → conf.d 드롭인 / pg_hba 변경 시에만 실행
# -----------------------------------------------------
# shared_preload_libraries 는 reload 로 반영되지 않는다 → restart 여야 한다.
- name: restart postgresql
  systemd:
    name: "postgresql@{{ postgres_version }}-main"
    state: restarted
    daemon_reload: true
```
