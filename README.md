# 🛠 Ansible 기반 서버 구성 자동화 플랫폼 (IaC)

**Ansible 기반 IaC로 인프라를 코드로 선언하고,
OS 및 실행 환경을 자동으로 구성하는 프로젝트 입니다.**

Infrastructure as Code(IaC) 기반으로 **인프라 환경을 코드로 정의하여 재현성을 확보**하고, **재사용성과 확장성**을 고려한 **표준화된 서버 구성 자동화**를 목표로 합니다.

---
</br>

## ✨ 주요 특징
- **Role 기반 모듈 구조** — 기능 단위로 분리된 31개 롤을 조합해 서버 구성
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

---
</br>

## 📂 디렉토리 구조
```bash
IaC_Ansible/
├── ansible.cfg           # Ansible 공통 설정
├── host.yml              # 인벤토리 (서버 목록/변수)
├── ubuntu_ansible.yml    # 메인 플레이북 (서버 프로비저닝)
├── k8s_ansible.yml       # K8s 클러스터 구성 플레이북
├── longhorn_ansible.yml  # Longhorn 노드 사전 준비 플레이북
├── terraform_ansible.yml # Terraform 설치 플레이북
├── bin/
│   ├── ansible_setup.sh       # Ansible 설치 (Control Node용)
│   ├── start_ansible.sh       # 메인 플레이북 실행
│   ├── start_kubernetes.sh    # K8s 플레이북 실행
│   ├── start_longhorn.sh      # Longhorn 플레이북 실행
│   └── start_terraform.sh     # Terraform 플레이북 실행
└── roles/                # 기능별 롤 (31종)
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
sudo /jsy/IaC_Ansible/bin/ansible_setup.sh
```

---
</br>

## 🚀 Ansible 실행
Ansible 프로젝트 홈 디렉토리의 **절대 경로**를 인자로 전달하여 실행합니다.
```bash
# 서버 프로비저닝 (ubuntu_ansible.yml)
/jsy/IaC_Ansible/bin/start_ansible.sh /jsy/IaC_Ansible

# K8s 클러스터 구성 (k8s_ansible.yml)
/jsy/IaC_Ansible/bin/start_kubernetes.sh /jsy/IaC_Ansible

# Longhorn 노드 사전 준비 (longhorn_ansible.yml)
/jsy/IaC_Ansible/bin/start_longhorn.sh /jsy/IaC_Ansible

# Terraform 설치 (terraform_ansible.yml)
/jsy/IaC_Ansible/bin/start_terraform.sh /jsy/IaC_Ansible
```
> ⚠️ **반드시 Ansible 프로젝트의 절대 경로를 인자로 전달해서 실행하세요.**

---
</br>

## 🔧 공통 설정 (ansible.cfg)
실행 옵션을 한 곳에 모아 CLI 옵션 없이 동일한 동작을 보장합니다.
- `inventory = host.yml` → 인벤토리 자동 지정 (`-i` 불필요)
- `host_key_checking = False` → 최초 SSH 접속 시 호스트 키 확인 생략
- `pipelining = True` → SSH 파이프라이닝으로 실행 속도 향상

---
</br>

## 📑 인벤토리 (host.yml)
대상 서버 목록과 접속 정보, 롤에서 사용하는 변수를 정의합니다.
- `Ubuntu_Servers` 그룹에 서버 추가/제거로 대상 확장
- 접속 계정, sudo 비밀번호, 설치 패키지 목록 등 변수 관리

---
</br>

## 📜 플레이북 (ubuntu_ansible.yml)
실행 흐름을 정의하는 메인 플레이북입니다.
- **Play 1** — Control Node 설정 (localhost)
- **Play 2** — Ubuntu_Servers 그룹 일괄 설정
- **적용할 롤은 `roles:` 목록에서 선택**

---
</br>

## 📜 K8s 플레이북 (k8s_ansible.yml)
K8s 클러스터(kubeadm + containerd + Calico) 구성 플레이북입니다.
- **Play 1** — 필수 Ansible 컬렉션 사전 검증 (Control Node)
- **Play 2** — kubernetes 그룹 공통 사전 준비
- **Play 3~4** — 컨트롤플레인 초기화(kubernetes_master) → 워커 조인(kubernetes_workers)
- **적용할 롤은 `roles:` 목록 주석 해제로 선택** (해체용 k8s_reset 플레이는 주석 상태)

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
- 네트워크 인터페이스 이름 설정
---

### 🔹 cloud_init → [`📂 cloud_init.md`](./roles/cloud_init/tasks/cloud_init.md)
- cloud-init 설정 (초기화 간섭 방지)
---

### 🔹 ufw → [`📂 ufw.md`](./roles/ufw/tasks/ufw.md)
- UFW 방화벽 설정
---

### 🔹 locale_ko → [`📂 locale_ko.md`](./roles/locale_ko/tasks/locale_ko.md)
- 한국어 로케일 설정
---

### 🔹 ssh_root_login → [`📂 ssh_root_login.md`](./roles/ssh_root_login/tasks/ssh_root_login.md)
- root SSH 로그인 정책 설정
---

### 🔹 timezone → [`📂 timezone.md`](./roles/timezone/tasks/timezone.md)
- 타임존 설정 (Asia/Seoul)
---

### 🔹 ntp → [`📂 ntp.md`](./roles/ntp/tasks/ntp.md)
- NTP 시간 동기화 설정
---

### 🔹 open_files → [`📂 open_files.md`](./roles/open_files/tasks/open_files.md)
- open files(ulimit) 제한 설정
---

### 🔹 logrotate → [`📂 logrotate.md`](./roles/logrotate/tasks/logrotate.md)
- 로그 로테이션 설정
---

### 🔹 shell_default → [`📂 shell_default.md`](./roles/shell_default/tasks/shell_default.md)
- 기본 쉘 설정
---

### 🔹 java → [`📂 java.md`](./roles/java/tasks/java.md)
- OpenJDK 설치 (인벤토리 `java_version` 기준)
---

### 🔹 disable_swap → [`📂 disable_swap.md`](./roles/disable_swap/tasks/disable_swap.md)
- 스왑 비활성화
---

### 🔹 enable_swap → [`📂 enable_swap.md`](./roles/enable_swap/tasks/enable_swap.md)
- 스왑 파일 생성 및 활성화 (인벤토리 `swap_file_path`, `swap_size_mb` 기준)
---

### 🔹 package_version_lock → [`📂 package_version_lock.md`](./roles/package_version_lock/tasks/package_version_lock.md)
- 패키지 버전 고정 (hold)
---

### 🔹 package_update_lock → [`📂 package_update_lock.md`](./roles/package_update_lock/tasks/package_update_lock.md)
- 자동 업데이트 잠금
---

### 🔹 bash_common → [`📂 bash_common.md`](./roles/bash_common/tasks/bash_common.md)
- bash 공통 환경 설정
---

### 🔹 ssh_keygen → [`📂 ssh_keygen.md`](./roles/ssh_keygen/tasks/ssh_keygen.md)
- SSH 키 생성 및 배포
---

### 🔹 etc_hosts → [`📂 etc_hosts.md`](./roles/etc_hosts/tasks/etc_hosts.md)
- /etc/hosts 호스트 등록
---

### 🔹 collection_check → [`📂 collection_check.md`](./roles/collection_check/tasks/collection_check.md)
- k8s 롤에 필요한 Ansible 컬렉션 사전 검증 (인벤토리 `required_collections` 기준)
---

### 🔹 k8s_prereq → [`📂 k8s_prereq.md`](./roles/k8s_prereq/tasks/k8s_prereq.md)
- K8s 사전 준비 — 커널 모듈(overlay/br_netfilter) + sysctl + cgroup v2 검증
---

### 🔹 containerd → [`📂 containerd.md`](./roles/containerd/tasks/containerd.md)
- 컨테이너 런타임 containerd 설치·버전 고정 + SystemdCgroup 활성화 + HTTP 사설 레지스트리 허용(certs.d) (인벤토리 `containerd_version`, `containerd_insecure_registries` 기준)
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
