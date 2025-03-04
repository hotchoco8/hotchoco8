#!/usr/bin/env python3

import subprocess
import os

# ===== [기본 버전 설정] =====
VERSIONS = {
    "containerd": "1.6.28",
    "runc": "1.1.14",
    "cni_plugin": "1.6.0",
    "crictl": "1.30.1",
    "nerdctl": "1.7.6",
    "pause_image": "registry.k8s.io/pause:3.10",
    "kubernetes": "1.28.2"
}

# Kubernetes Major.Minor 버전 추출 (예: "1.28")
K8S_MAJOR_MINOR = ".".join(VERSIONS["kubernetes"].split(".")[:2])
K8S_GPG_KEY_URL = f"https://pkgs.k8s.io/core:/stable:/v{K8S_MAJOR_MINOR}/deb/Release.key"
K8S_REPO_URL = f"https://pkgs.k8s.io/core:/stable:/v{K8S_MAJOR_MINOR}/deb/"

# ===== [명령어 실행 함수] =====
def run_command(command, error_msg):
    """명령어 실행 및 오류 처리"""
    process = subprocess.run(command, shell=True, text=True, capture_output=True)
    
    if process.returncode != 0:
        print(f"[ERROR] {error_msg}\n[STDOUT]: {process.stdout}\n[STDERR]: {process.stderr}")
        raise RuntimeError(error_msg)
    else:
        print(f"[SUCCESS] {command}")

# ===== [1. Kubernetes APT 저장소 및 GPG 키 설정] =====
def setup_kubernetes_repo():
    """Kubernetes APT 저장소 및 GPG 키 설정"""
    print("🔹 Setting up Kubernetes APT repository...")

    # 필수 패키지 설치
    run_command("sudo apt-get update", "Failed to update package lists.")
    run_command("sudo apt-get install -y apt-transport-https ca-certificates curl gpg nfs-common",
                "Failed to install required packages.")

    # GPG 키 추가
    run_command("sudo mkdir -p /etc/apt/keyrings", "Failed to create keyrings directory.")
    run_command(f"curl -fsSL {K8S_GPG_KEY_URL} | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
                "Failed to download Kubernetes GPG key.")

    # APT 저장소 추가
    run_command(f"echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] {K8S_REPO_URL} /' | sudo tee /etc/apt/sources.list.d/kubernetes.list",
                "Failed to add Kubernetes repository.")

    # APT 패키지 목록 업데이트
    run_command("sudo apt-get update", "Failed to update package lists after adding Kubernetes repo.")

    print("✅ Kubernetes APT repository has been set up successfully!")

# ===== [2. Swap 비활성화] =====
def disable_swap():
    print("Disabling Swap...")
    run_command("sudo swapoff -a", "Failed to disable swap temporarily.")
    run_command("sudo sed -i '/swap/d' /etc/fstab", "Failed to remove swap entry from fstab.")
    print("✅ Swap has been successfully disabled and cleaned up!")

# ===== [3. runc 설치] =====
def install_runc():
    """runc 설치 (GitHub 다운로드)"""
    runc_version = VERSIONS["runc"]
    runc_url = f"https://github.com/opencontainers/runc/releases/download/v{runc_version}/runc.amd64"

    print(f"Installing runc {runc_version} from GitHub...")
    run_command(f"sudo wget {runc_url} -O /usr/local/sbin/runc", "Failed to download runc.")
    run_command("sudo chmod +x /usr/local/sbin/runc", "Failed to set executable permission for runc.")
    print("✅ runc has been installed successfully!")

# ===== [4. CNI Plugin 설치] =====
def install_cni_plugin():
    """CNI 플러그인 설치 (GitHub 다운로드)"""
    cni_version = VERSIONS["cni_plugin"]
    cni_url = f"https://github.com/containernetworking/plugins/releases/download/v{cni_version}/cni-plugins-linux-amd64-v{cni_version}.tgz"

    print(f"Installing CNI plugins {cni_version} from GitHub...")
    run_command("sudo mkdir -p /opt/cni/bin", "Failed to create CNI plugin directory.")
    run_command(f"sudo wget {cni_url} -O /tmp/cni-plugins.tgz", "Failed to download CNI plugins.")
    run_command("sudo tar Cxzvf /opt/cni/bin /tmp/cni-plugins.tgz", "Failed to extract CNI plugins.")
    print("✅ CNI plugins have been installed successfully!")

# ===== [5. Containerd 설치 및 설정] =====
def install_containerd():
    """Containerd 설치 및 설정"""
    containerd_version = VERSIONS["containerd"]
    containerd_url = f"https://github.com/containerd/containerd/releases/download/v{containerd_version}/containerd-{containerd_version}-linux-amd64.tar.gz"
    pause_image = VERSIONS["pause_image"]

    print(f"Installing containerd {containerd_version} from GitHub...")
    run_command(f"sudo wget {containerd_url} -O /tmp/containerd.tar.gz", "Failed to download containerd.")
    run_command("sudo tar Cxzvf /usr/local /tmp/containerd.tar.gz", "Failed to extract containerd.")

    run_command("sudo mkdir -p /usr/local/lib/systemd/system", "Failed to create systemd directory.")
    run_command("sudo wget -O /usr/local/lib/systemd/system/containerd.service https://raw.githubusercontent.com/containerd/containerd/main/containerd.service",
                "Failed to download containerd service file.")

    run_command("sudo systemctl daemon-reload", "Failed to reload systemd daemon.")
    run_command("sudo systemctl enable --now containerd", "Failed to enable and start containerd service.")

    # Containerd 설정 파일 생성 및 수정
    print("🔧 Configuring containerd...")
    run_command("sudo mkdir -p /etc/containerd", "Failed to create containerd config directory.")
    run_command("containerd config default > /tmp/config.toml", "Failed to generate default containerd config.")
    
    # sandbox_image 및 SystemdCgroup 설정
    run_command(f"sudo sed -i 's|sandbox_image = .*|sandbox_image = \"{pause_image}\"|' /tmp/config.toml",
                "Failed to update sandbox_image.")
    
    run_command("sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /tmp/config.toml",
                "Failed to enable SystemdCgroup.")

    run_command("sudo mv /tmp/config.toml /etc/containerd/config.toml", "Failed to move containerd config file.")


    # containerd 재시작
    run_command("sudo systemctl restart containerd", "Failed to restart containerd.")
    print("✅ Containerd has been installed and configured successfully!")

# ===== [6. Kubernetes 설치] =====
def install_kubernetes_tools():
    """Kubernetes(kubeadm, kubelet, kubectl) 설치"""
    default_version = VERSIONS["kubernetes"]

    result = subprocess.run("apt-cache madison kubelet", shell=True, text=True, capture_output=True)
    available_versions = [line.split("|")[1].strip() for line in result.stdout.split("\n") if line]

    if not available_versions:
        print("⚠️ No available Kubernetes versions found in the package list. Exiting...")
        raise RuntimeError("No available Kubernetes versions found.")

    # 버전이 정확히 일치하는지 확인 후, 올바른 형식 선택
    matching_version = next((v for v in available_versions if default_version in v), None)
    if not matching_version:
        print(f"⚠️ Specified Kubernetes version {default_version} not found. Using latest available version: {available_versions[0]}")
        matching_version = available_versions[0]

    print(f"✅ Installing Kubernetes version: {matching_version}")

    run_command(f"sudo apt-get install -y kubelet={matching_version} kubeadm={matching_version} kubectl={matching_version}",
                "Failed to install Kubernetes tools.")
    
    run_command("sudo apt-mark hold kubeadm kubelet kubectl", "Failed to hold Kubernetes packages.")

    run_command("sudo systemctl restart kubelet", "Failed to restart kubelet service.")
    print("✅ Kubernetes installed successfully!")

# ===== [6. crictl 설치] =====
def install_crictl():
    """crictl 설치 (GitHub 다운로드)"""
    crictl_version = VERSIONS["crictl"]
    crictl_url = f"https://github.com/kubernetes-sigs/cri-tools/releases/download/v{crictl_version}/crictl-v{crictl_version}-linux-amd64.tar.gz"

    print(f"Installing crictl {crictl_version} from GitHub...")
    run_command(f"sudo wget {crictl_url} -O /tmp/crictl.tar.gz", "Failed to download crictl.")
    run_command("sudo tar Cxzvf /usr/local/bin /tmp/crictl.tar.gz", "Failed to extract crictl.")

    # ✅ crictl이 containerd와 연결될 수 있도록 설정 추가
    crictl_config = """
    runtime-endpoint: unix:///run/containerd/containerd.sock
    image-endpoint: unix:///run/containerd/containerd.sock
    timeout: 10
    debug: false
    """
    run_command(f"echo '{crictl_config}' | sudo tee /etc/crictl.yaml > /dev/null", "Failed to create crictl.yaml")

    print("✅ crictl has been installed and configured successfully!")

# ===== [7. nerdctl 설치] =====
def install_nerdctl():
    """nerdctl 설치 (GitHub 다운로드)"""
    nerdctl_version = VERSIONS["nerdctl"]
    nerdctl_url = f"https://github.com/containerd/nerdctl/releases/download/v{nerdctl_version}/nerdctl-{nerdctl_version}-linux-amd64.tar.gz"

    print(f"Installing nerdctl {nerdctl_version} from GitHub...")
    run_command(f"sudo wget {nerdctl_url} -O /tmp/nerdctl.tar.gz", "Failed to download nerdctl.")
    run_command("sudo tar Cxzvf /usr/local/bin /tmp/nerdctl.tar.gz", "Failed to extract nerdctl.")
    print("✅ nerdctl has been installed successfully!")

# ===== [8. Kernel 모듈 및 네트워크 설정] =====
def configure_kernel_modules():
    """Kubernetes를 위한 커널 모듈 및 sysctl 설정"""
    print("Configuring kernel modules and sysctl parameters...")
    run_command("sudo modprobe overlay", "Failed to load overlay module.")
    run_command("sudo modprobe br_netfilter", "Failed to load br_netfilter module.")

    sysctl_config = """
    net.bridge.bridge-nf-call-iptables  = 1
    net.bridge.bridge-nf-call-ip6tables = 1
    net.ipv4.ip_forward                 = 1
    """
    run_command(f"echo '{sysctl_config}' | sudo tee /etc/sysctl.d/k8s.conf", "Failed to configure sysctl parameters.")

    run_command("sudo sysctl --system", "Failed to apply sysctl settings.")
    print("✅ Kernel modules and sysctl parameters configured successfully!")

def download_pause_image():
    """Pause 컨테이너 이미지 다운로드"""
    pause_image = VERSIONS["pause_image"] 
    run_command(f"sudo nerdctl --namespace=k8s.io pull {pause_image}", "Failed to pull pause image.")
    print("✅ Pause image has been downloaded successfully!")

# ===== [메인 함수] =====
def main():
    print("🚀 Starting Kubernetes Node Setup...")

    setup_kubernetes_repo()
    disable_swap()
    configure_kernel_modules()
    install_runc()
    install_cni_plugin()
    install_containerd()
    install_kubernetes_tools()
    install_crictl() 
    install_nerdctl()
    download_pause_image()

    print("🎉 Kubernetes Node Setup Completed Successfully!")

if __name__ == "__main__":
    main()