#!/usr/bin/env python3
import sys
import re
import hashlib
import os
import subprocess

# === 批量配置区 ===
# 在这里配置你需要批量打的标签。设为 None 则不生成该行。
CONFIG = {
    "Mainline": "AUTO",  # "AUTO": 自动从 (cherry picked from ...) 提取
    "From": "AUTO",      # "AUTO": 自动根据 Mainline hash 推导上游版本 (如 v6.18-rc1)
    "Severity": "Low", # "Important"/"Moderate"
    "CVE": None,
    "Task": "#596319",
    "K2CI-Arch": None   # "All"
}

def get_git_config(key, default):
    """获取 Git 配置信息（如用户名和邮箱）"""
    try:
        val = subprocess.check_output(['git', 'config', key], text=True).strip()
        return val if val else default
    except subprocess.CalledProcessError:
        return default

def generate_change_id():
    """生成 Gerrit 风格的随机 Change-Id"""
    return "I" + hashlib.sha1(os.urandom(20)).hexdigest()

def get_upstream_version(commit_hash):
    """使用 git describe 极速获取 commit 首次合入的 Tag"""
    if not commit_hash:
        return None
    
    try:
        # --match='v[0-9]*' 确保只匹配正式的版本号，过滤掉其他乱七八糟的 tag
        cmd = f"git describe --contains --match='v[0-9]*' {commit_hash}"
        # 屏蔽 stderr，防止没找到 tag 时在终端满屏报错
        result = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
        
        if result:
            # git describe 输出格式形如 v6.19-rc1~15^2
            # 利用正则按照 ~ 或 ^ 分割，只取第一部分的纯 Tag 名称
            return re.split(r'[~^]', result)[0]
            
    except subprocess.CalledProcessError:
        # 找不到对应的 tag 时静默失败
        pass
        
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rewrite_msg.py <msg_file>")
        sys.exit(1)
        
    msg_file = sys.argv[1]
    
    with open(msg_file, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    if not lines:
        return

    subject = lines[0]
    body_lines = lines[1:] if len(lines) > 1 else []

    clean_body = []
    mainline_hash = ""
    existing_change_id = None
    
    # 正则匹配 Git 原生 cherry-pick 提示和已存在的 Change-Id
    cp_pattern = re.compile(r'^\s*\(cherry picked from commit ([a-f0-9]+)\)')
    cid_pattern = re.compile(r'^Change-Id:\s*(I[a-f0-9]+)')

    for line in body_lines:
        # 提取 mainline hash
        cp_match = cp_pattern.search(line)
        if cp_match:
            mainline_hash = cp_match.group(1)
            continue
            
        # 提取现有的 Change-Id
        cid_match = cid_pattern.search(line)
        if cid_match:
            existing_change_id = cid_match.group(1)
            continue
            
        clean_body.append(line)

    # 移除正文首尾多余的空行
    while clean_body and not clean_body[0].strip():
        clean_body.pop(0)
    while clean_body and not clean_body[-1].strip():
        clean_body.pop()

    # 构建头部元数据块
    meta_header = []
    
    # 1. Mainline
    ml_val = mainline_hash if CONFIG.get("Mainline") == "AUTO" else CONFIG.get("Mainline")
    if ml_val:
        meta_header.append(f"Mainline: {ml_val}")
    
    # 2. From
    from_val = CONFIG.get("From")
    if from_val == "AUTO" and mainline_hash:
        auto_version = get_upstream_version(mainline_hash)
        if auto_version:
            meta_header.append(f"From: {auto_version}")
        else:
            meta_header.append("From: <unknown-version>")
    elif from_val and from_val != "AUTO":
        meta_header.append(f"From: {from_val}")
    
    # 3. 其他头部标签
    for k in ["Severity", "CVE"]:
        if CONFIG.get(k):
            meta_header.append(f"{k}: {CONFIG[k]}")
            
    if meta_header:
        meta_header.append("") # 视觉分隔空行
        
    # 4. Task
    if CONFIG.get("Task"):
        meta_header.append(f"Task: {CONFIG['Task']}")
        meta_header.append("")

    # 构建尾部元数据块
    meta_footer = [""]
    if CONFIG.get("K2CI-Arch"):
        meta_footer.append(f"K2CI-Arch: {CONFIG['K2CI-Arch']}")
        
    change_id = existing_change_id if existing_change_id else generate_change_id()
    meta_footer.append(f"Change-Id: {change_id}")

    my_name = get_git_config("user.name", "Huiwen He")
    my_email = get_git_config("user.email", "hehuiwen@kylinos.cn")
    sob = f"Signed-off-by: {my_name} <{my_email}>"
    
    # 避免重复追加自身的 Signed-off-by
    if not any(sob in line for line in clean_body):
        meta_footer.append(sob)

    # 组装并原地写回文件
    new_content = "\n".join([subject, ""] + meta_header + clean_body + meta_footer) + "\n"
    with open(msg_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    main()
