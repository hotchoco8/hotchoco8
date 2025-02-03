#!/usr/bin/env python3

import os
import subprocess


# ===== [서버 목록 설정] =====
SERVERS = [
    {"name": "m1", "ip": "192.168.0.15"},
    {"name": "m2", "ip": "192.168.0.89"},
    {"name": "m3", "ip": "192.168.0.65"},
    {"name": "w1", "ip": "192.168.0.103"},
    {"name": "w2", "ip": "192.168.0.55"},
    {"name": "w3", "ip": "192.168.0.98"}
]

# SSH 접속 기본 정보
USER = "ubuntu"                            # SSH 사용자명
KEY_FILE = "~/.ssh/junwoo_24.pem"         # PEM 키 파일 경로


# ===== [서버 목록 출력 함수] =====
def display_servers():
    print("\n[ 서버 목록 ]")
    for idx, server in enumerate(SERVERS, start=1):
        print(f"{idx}. {server['name']} ({server['ip']})")


# ===== [SSH 접속 함수] =====
def ssh_connect(ip):
    key_path = os.path.expanduser(KEY_FILE)
    command = f"ssh -i {key_path} {USER}@{ip}"
    subprocess.run(command, shell=True)


# ===== [메인 함수] =====
def main():
    while True:
        # 서버 목록 표시
        display_servers()

        # 사용자 입력 처리
        try:
            choice = input("\n접속할 서버 번호를 선택하세요 (종료: q): ")

            if choice.lower() == 'q':
                print("프로그램 종료.")
                break

            choice = int(choice) - 1

            if 0 <= choice < len(SERVERS):
                server = SERVERS[choice]
                print(f"\n{server['name']} ({server['ip']})에 접속합니다...")
                ssh_connect(server["ip"])
            else:
                print("[ERROR] 잘못된 입력입니다. 다시 선택하세요.")

        except ValueError:
            print("[ERROR] 숫자 또는 'q'를 입력하세요.")


if __name__ == "__main__":
    main()
