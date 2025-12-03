#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从多个高质量源获取代理节点并上传到 GitHub Gist
支持：Clash, Quantumult X, V2Ray 等格式
"""

import os
import sys
import time
import base64
from datetime import datetime

try:
    import yaml
except ImportError:
    print("请安装 PyYAML: pip install pyyaml")
    sys.exit(1)

try:
    from requests import get, post
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)


# ========== 配置区域 ==========

# GitHub Gist 配置（从环境变量读取）
GIST_PAT = os.environ.get("GIST_PAT", "")
GIST_LINK = os.environ.get("GIST_LINK", "")

# 目标格式
TARGETS = ["clash", "v2ray", "quanx"]

# 文件名映射
FILENAME_MAP = {
    "clash": "clash.yaml",
    "v2ray": "v2ray.txt",
    "quanx": "quantumult_x.conf"
}

# ========== 2025年12月最新订阅源（每10-30分钟更新） ==========
SUBSCRIPTION_SOURCES = [
    # barry-far/V2ray-Configs (每 10 分钟更新)
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub2.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub3.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub4.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub5.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub6.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub7.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub8.txt",
    
    # MatinGhanbari/v2ray-configs (每 10-15 分钟更新)
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/xray/base64/vmess",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/xray/base64/vless",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/xray/base64/trojan",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/shadowsocks/base64/ss",
    
    # ebrasha/free-v2ray-public-list (每 30 分钟更新)
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/all_extracted_configs.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/vmess_configs.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/vless_configs.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/trojan_configs.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/ss_configs.txt",
    
    # Epodonios/v2ray-configs (每 5 分钟更新)
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vmess.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/trojan.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/ss.txt",
]


def log_info(message: str):
    """打印信息日志"""
    print(f"[INFO] {message}")


def log_error(message: str):
    """打印错误日志"""
    print(f"[ERROR] {message}", file=sys.stderr)


def fetch_subscription(url: str, timeout: int = 15) -> str:
    """
    从URL获取订阅内容
    """
    try:
        response = get(url, timeout=timeout)
        response.raise_for_status()
        content = response.text.strip()
        
        # 尝试 base64 解码
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            if decoded and ('vmess://' in decoded or 'vless://' in decoded or 'trojan://' in decoded or 'ss://' in decoded):
                return decoded
        except:
            pass
        
        return content
    except Exception as e:
        log_error(f"Failed to fetch {url[:60]}...: {e}")
        return ""


def merge_subscriptions(contents: list) -> str:
    """
    合并多个订阅内容，去重
    """
    all_lines = set()
    
    for content in contents:
        if not content:
            continue
        
        for line in content.split('\n'):
            line = line.strip()
            if line and line.startswith(('vmess://', 'vless://', 'trojan://', 'ss://','ssr://', 'hysteria://', 'hysteria2://')):
                all_lines.add(line)
    
    return '\n'.join(sorted(list(all_lines)))


def convert_to_clash(v2ray_content: str) -> str:
    """
    将 V2Ray 订阅转换为 Clash 格式（简化版）
    """
    # 这里简化处理，实际应该解析每个链接
    # 由于格式复杂，建议直接使用已有的 Clash 源
    proxies = []
    
    for line in v2ray_content.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 简单示例：只处理 vmess
        if line.startswith('vmess://'):
            try:
                decoded = base64.b64decode(line[8:]).decode('utf-8')
                config = yaml.safe_load(decoded) if decoded.startswith('{') else eval(decoded)
                
                proxy = {
                    'name': config.get('ps', 'vmess-node'),
                    'type': 'vmess',
                    'server': config.get('add'),
                    'port': int(config.get('port', 443)),
                    'uuid': config.get('id'),
                    'alterId': int(config.get('aid', 0)),
                    'cipher': 'auto',
                }
                
                if config.get('net') == 'ws':
                    proxy['network'] = 'ws'
                    proxy['ws-opts'] = {'path': config.get('path', '/')}
                
                if config.get('tls') == 'tls':
                    proxy['tls'] = True
                
                proxies.append(proxy)
            except:
                continue
    
    clash_config = {
        'proxies': proxies,
        'proxy-groups': [
            {
                'name': 'auto',
                'type': 'url-test',
                'proxies': [p['name'] for p in proxies],
                'url': 'http://www.gstatic.com/generate_204',
                'interval': 300
            }
        ]
    }
    
    return yaml.dump(clash_config, allow_unicode=True, default_flow_style=False)


def upload_to_gist(files: dict) -> bool:
    """
    上传文件到 GitHub Gist
    """
    if not GIST_PAT or not GIST_LINK:
        log_error("GIST_PAT or GIST_LINK not set")
        return False
    
    parts = GIST_LINK.split('/')
    if len(parts) != 2:
        log_error(f"Invalid GIST_LINK format: {GIST_LINK}")
        return False
    
    username, gist_id = parts
    
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {GIST_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 构建文件 payload
    gist_files = {}
    for filename, content in files.items():
        if content:
            gist_files[filename] = {"content": content}
    
    if not gist_files:
        log_error("No valid files to upload")
        return False
    
    data = {"files": gist_files}
    
    try:
        log_info(f"Uploading {len(gist_files)} files to Gist...")
        response = post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        log_info(f"✓ Successfully uploaded to: https://gist.github.com/{username}/{gist_id}")
        return True
    except Exception as e:
        log_error(f"Failed to upload to Gist: {e}")
        return False


def main():
    """主函数"""
    log_info("=" * 60)
    log_info("Fetching from 2025 Latest Subscription Sources")
    log_info("=" * 60)
    
    # 获取所有订阅
    all_contents = []
    for idx, url in enumerate(SUBSCRIPTION_SOURCES, 1):
        log_info(f"[{idx}/{len(SUBSCRIPTION_SOURCES)}] Fetching: {url[50:80]}...")
        content = fetch_subscription(url)
        if content:
            all_contents.append(content)
            log_info(f"  ✓ Got {len(content)} bytes")
        else:
            log_info(f"  ✗ Failed")
    
    if not all_contents:
        log_error("Failed to fetch any content from all sources")
        sys.exit(1)
    
    # 合并订阅
    log_info(f"\nMerging {len(all_contents)} sources...")
    merged_v2ray = merge_subscriptions(all_contents)
    
    if not merged_v2ray:
        log_error("No valid subscription content after merging")
        sys.exit(1)
    
    log_info(f"✓ Merged {len(merged_v2ray.split(chr(10)))} unique nodes")
    
    # 准备上传的文件
    files = {}
    
    # V2Ray 格式（Base64 编码）
    v2ray_b64 = base64.b64encode(merged_v2ray.encode()).decode()
    files[FILENAME_MAP["v2ray"]] = v2ray_b64
    log_info(f"✓ Generated {FILENAME_MAP['v2ray']}")
    
    # Clash 格式（简化版）
    log_info("Converting to Clash format...")
    clash_content = convert_to_clash(merged_v2ray)
    files[FILENAME_MAP["clash"]] = clash_content
    log_info(f"✓ Generated {FILENAME_MAP['clash']}")
    
    # Quantumult X 格式（使用 V2Ray 原始格式）
    files[FILENAME_MAP["quanx"]] = merged_v2ray
    log_info(f"✓ Generated {FILENAME_MAP['quanx']}")
    
    # 上传到 Gist
    log_info("\n" + "=" * 60)
    success = upload_to_gist(files)
    
    if success:
        log_info("=" * 60)
        log_info("✓ All done!")
        log_info(f"Total nodes: {len(merged_v2ray.split(chr(10)))}")
        log_info(f"Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        log_error("Upload failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
