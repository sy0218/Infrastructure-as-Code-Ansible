# 🧵 Kafka 토픽 프로비저닝 (파이프라인 계약)

- 파이프라인이 계약으로 쓰는 토픽 16종(raw 8 + cdm/dlq/lineage 8)을 생성한다.
- 토픽은 클러스터 전체에 반영되므로 **한 노드에서만 실행**한다 (플레이북이 `hosts: ap` 로 고정).
- `--if-not-exists` 라 몇 번 돌아도 안전하다. 목록/파티션 수의 단일 소스는 host.yml.
- ⚠️ **기존 토픽의 파티션 수는 변경 금지** — 프로듀서가 `hash(key) % PARTITIONS` 로 파티션을 고르므로 값을 바꾸면 같은 키의 순서 보장이 깨진다.

---
<br>

## 🧩 main.yml
```yaml
# -----------------------------------------------------
# Kafka 토픽 프로비저닝 — 파이프라인 계약 토픽 생성
# -----------------------------------------------------
# 토픽은 클러스터 전체에 반영되므로 한 노드에서만 실행한다(플레이북이 hosts 를 1대로 고정).
# 목록/파티션 수의 단일 소스는 host.yml 의 kafka_topic_list / kafka_topic_partitions.
# ⚠ 기존 토픽의 파티션 수는 바꾸지 않는다 — 프로듀서가 hash(key) % PARTITIONS 로
#   파티션을 고르므로 값을 바꾸면 같은 키의 순서 보장이 깨진다.
# -----------------------------------------------------

# 1. 토픽 생성 (--if-not-exists 로 멱등 — 실제로 생성된 경우에만 changed)
#    복제계수는 명시하지 않는다 → 브로커 default.replication.factor(=3)를 상속 (kafka 롤과 단일 출처)
- name: "Create kafka topics"
  command: >-
    {{ kafka_home }}/bin/kafka-topics.sh --create --if-not-exists
    --bootstrap-server {{ ansible_host }}:{{ kafka_client_port }}
    --topic {{ item }} --partitions {{ kafka_topic_partitions }}
  loop: "{{ kafka_topic_list }}"
  register: topic_create
  changed_when: "'Created topic' in topic_create.stdout"
  environment:
    JAVA_HOME: "{{ kafka_java_home }}"

# -----------------------------------------------------
# 검증
# -----------------------------------------------------
- name: "List kafka topics"
  command: "{{ kafka_home }}/bin/kafka-topics.sh --list --bootstrap-server {{ ansible_host }}:{{ kafka_client_port }}"
  register: topic_list
  changed_when: false
  environment:
    JAVA_HOME: "{{ kafka_java_home }}"

- name: "Assert all pipeline topics exist"
  assert:
    that:
      - item in topic_list.stdout_lines # 라인 단위 정확 일치 (조건문 안에서는 {{ }} 금지)
    success_msg: "Good!.. | Topic exists: {{ item }}"
    fail_msg: "ERROR!.. | Topic NOT found: {{ item }}"
  loop: "{{ kafka_topic_list }}"
```
---
<br>

## 📌 host.yml 예시
```yaml
kafka:
  vars:
    kafka_topic_partitions: "3" # ⚠ 운영 중 변경 금지 (키 순서 보장 깨짐)
    kafka_topic_list:
      # raw — 수집기가 적재 (Airflow 배치 · TCP socket push · Debezium CDC)
      - raw.qm.qm-chemical.batches
      - raw.qm.qm-chemical.qc-results
      # ... (전체 목록은 host.yml 참조)
      # 파이프라인 내부 (cdm / dlq / lineage)
      - cdm-topic
      - dlq-cdm-topic
      - lineage-topic
```
---
<br>

## 🛠 작업 내용
### 1️⃣ 토픽 생성 (멱등성 핵심)
- `--if-not-exists` 로 재실행 안전, `changed_when: 'Created topic' in stdout` 으로 **실제 생성 시에만 changed**
- 복제계수는 명시하지 않고 브로커 `default.replication.factor`(=3)를 상속 → RF 의 단일 출처는 kafka 롤
---
### 2️⃣ 검증
- `kafka-topics.sh --list` 결과에 대해 토픽별 라인 단위 정확 일치 `assert`
---
<br>

## ✅ 실행 결과 예시
```bash
TASK [Assert all pipeline topics exist]
ok: [192.168.56.200] => (item=cdm-topic) => {
    "msg": "Good!.. | Topic exists: cdm-topic"
}
```
---
