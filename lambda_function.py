import paramiko
import os
import socket
import shutil

def lambda_handler(event, context):
    # ========= CONFIG =========
    ec2_host = "52.91.217.106"   # EC2 public or private IP
    ec2_user = "ec2-user"
    ansible_playbook = "/etc/ansible/deploy.yaml"

    # Key paths
    source_key = "/var/task/ansible.pem"   # same folder as lambda_function.py
    key_file = "/tmp/ansible.pem"          # writable location

    # ========= PREPARE KEY =========
    shutil.copy(source_key, key_file)
    os.chmod(key_file, 0o400)

    # ========= LOAD SSH KEY =========
    try:
        try:
            pkey = paramiko.RSAKey.from_private_key_file(key_file)
        except paramiko.ssh_exception.SSHException:
            try:
                pkey = paramiko.Ed25519Key.from_private_key_file(key_file)
            except paramiko.ssh_exception.SSHException:
                pkey = paramiko.ECDSAKey.from_private_key_file(key_file)
    except Exception as e:
        print(f"❌ Failed to load SSH key: {e}")
        raise

    # ========= SSH CLIENT =========
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("🔌 Connecting to EC2...")
        ssh.connect(
            hostname=ec2_host,
            username=ec2_user,
            pkey=pkey,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30
        )
        print(f"✅ Connected to {ec2_host}")

        # ========= RUN ANSIBLE =========
        command = f"ansible-playbook {ansible_playbook}"
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)

        # Stream output live
        for line in iter(stdout.readline, ""):
            if line:
                print(line.rstrip())

        for line in iter(stderr.readline, ""):
            if line:
                print("ERR:", line.rstrip())

        exit_code = stdout.channel.recv_exit_status()
        print(f"✅ Ansible finished with exit code: {exit_code}")

        if exit_code != 0:
            raise Exception("Ansible playbook failed")

    except (paramiko.SSHException, socket.timeout) as e:
        print(f"❌ SSH execution failed: {e}")
        raise

    finally:
        ssh.close()
        print("🔒 SSH connection closed")

    return {
        "status": "SUCCESS",
        "exit_code": exit_code
    }
