#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从多个高质量源获取代理节点并上传到 GitHub Gist
专注于 Clash 格式，确保兼容性
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

# ========== 2025年12月3日最新 Clash 订阅源 ==========
CLASH_SOURCES = [
    # 今天刚更新的源（12月3日）
    "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml",
    "https://raw.githubusercontent.com/free-nodes/clashfree/main/clash.yml",
    
    # 每30分钟更新
    "https://raw.githubusercontent.com/PuddinCat/BestClash/main/clash.yaml",
    
    # 其他活跃维护的源
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/aiboboxx/clashfree/main/clash.yml",
    "https://raw.githubusercontent.com/freefq/free/master/clash.yaml",
]

# V2Ray 订阅源（用于补充）
V2RAY_SOURCES = [
    # barry-far (每10分钟更新)
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub2.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub5.txt",
    
    # ebrasha (每30分钟更新)
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/all_extracted_configs.txt",
]


def log_info(message: str):
    """打印信息日志"""
    print(f"[INFO] {message}")


def log_error(message: str):
    """打印错误日志"""
    print(f"[ERROR] {message}", file=sys.stderr)


def fetch_clash_yaml(url: str, timeout: int = 15) -> dict:
    """
    从URL获取 Clash YAML 配置
    """
    try:
        response = get(url, timeout=timeout)
        response.raise_for_status()
        content = response.text.strip()
        
        # 解析 YAML
        config = yaml.safe_load(content)
        if config and 'proxies' in config:
            return config
        else:
            return None
    except Exception as e:
        log_error(f"Failed to fetch {url[:60]}...: {e}")
        return None


def fetch_v2ray_subscription(url: str, timeout: int = 15) -> str:
    """
    从URL获取 V2Ray 订阅内容（原始链接）
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


def merge_clash_configs(configs: list) -> dict:
    """
    合并多个 Clash 配置
    """
    all_proxies = []
    seen_names = set()
    
    for config in configs:
        if not config or 'proxies' not in config:
            continue
        
        for proxy in config['proxies']:
            name = proxy.get('name', '')
            if not name or name in seen_names:
                continue
            
            seen_names.add(name)
            all_proxies.append(proxy)
    
    # 构建最终配置
    merged_config = {
        'port': 7890,
        'socks-port': 7891,
        'allow-lan': False,
        'mode': 'Rule',
        'log-level': 'info',
        'external-controller': '127.0.0.1:9090',
        'proxies': all_proxies,
        'proxy-groups': [
            {
                'name': '🚀 节点选择',
                'type': 'select',
                'proxies': ['♻️ 自动选择', '🎯 全球直连'] + [p['name'] for p in all_proxies[:50]]  # 限制前50个避免太长
            },
            {
                'name': '♻️ 自动选择',
                'type': 'url-test',
                'proxies': [p['name'] for p in all_proxies],
                'url': 'http://www.gstatic.com/generate_204',
                'interval': 300
            },
            {
                'name': '🎯 全球直连',
                'type': 'select',
                'proxies': ['DIRECT']
            }
        ],
        'rules': [
            'DOMAIN-SUFFIX,local,DIRECT',
            'IP-CIDR,127.0.0.0/8,DIRECT',
            'IP-CIDR,172.16.0.0/12,DIRECT',
            'IP-CIDR,192.168.0.0/16,DIRECT',
            'IP-CIDR,10.0.0.0/8,DIRECT',
            'IP-CIDR,17.0.0.0/8,DIRECT',
            'IP-CIDR,100.64.0.0/10,DIRECT',
            'GEOIP,CN,DIRECT',
            'MATCH,🚀 节点选择'
        ]
    }
    
    return merged_config


def merge_v2ray_subscriptions(contents: list) -> str:
    """
    合并多个 V2Ray 订阅内容，去重
    """
    all_lines = set()
    
    for content in contents:
        if not content:
            continue
        
        for line in content.split('\n'):
            line = line.strip()
            if line and line.startswith(('vmess://', 'vless://', 'trojan://', 'ss://', 'ssr://', 'hysteria://', 'hysteria2://')):
                all_lines.add(line)
    
    return '\n'.join(sorted(list(all_lines)))


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
    log_info("Fetching from 2025-12-03 Latest Sources")
    log_info("=" * 60)
    
    # 获取所有 Clash 配置
    log_info("\nFetching Clash configurations...")
    clash_configs = []
    for idx, url in enumerate(CLASH_SOURCES, 1):
        log_info(f"[{idx}/{len(CLASH_SOURCES)}] {url[40:70]}...")
        config = fetch_clash_yaml(url)
        if config:
            proxy_count = len(config.get('proxies', []))
            clash_configs.append(config)
            log_info(f"  ✓ Got {proxy_count} proxies")
        else:
            log_info(f"  ✗ Failed")
    
    if not clash_configs:
        log_error("Failed to fetch any Clash config")
        sys.exit(1)
    
    # 合并 Clash 配置
    log_info(f"\nMerging {len(clash_configs)} Clash configs...")
    merged_clash = merge_clash_configs(clash_configs)
    proxy_count = len(merged_clash.get('proxies', []))
    log_info(f"✓ Merged {proxy_count} unique proxies")
    
    if proxy_count == 0:
        log_error("No valid proxies found")
        sys.exit(1)
    
    # 获取 V2Ray 订阅（补充）
    log_info("\nFetching V2Ray subscriptions...")
    v2ray_contents = []
    for idx, url in enumerate(V2RAY_SOURCES, 1):
        log_info(f"[{idx}/{len(V2RAY_SOURCES)}] {url[40:70]}...")
        content = fetch_v2ray_subscription(url)
        if content:
            v2ray_contents.append(content)
            log_info(f"  ✓ Got {len(content)} bytes")
        else:
            log_info(f"  ✗ Failed")
    
    # 合并 V2Ray 订阅
    merged_v2ray = merge_v2ray_subscriptions(v2ray_contents) if v2ray_contents else ""
    
    # 准备上传的文件
    files = {}
    
    # Clash YAML
    clash_yaml = yaml.dump(merged_clash, allow_unicode=True, default_flow_style=False, sort_keys=False)
    files['clash.yaml'] = clash_yaml
    log_info(f"✓ Generated clash.yaml ({len(clash_yaml)} bytes, {proxy_count} nodes)")
    
    # V2Ray 订阅（Base64 编码）
    if merged_v2ray:
        v2ray_b64 = base64.b64encode(merged_v2ray.encode()).decode()
        files['v2ray.txt'] = v2ray_b64
        node_count = len(merged_v2ray.split('\n'))
        log_info(f"✓ Generated v2ray.txt ({node_count} nodes)")
    
    # Quantumult X（使用 V2Ray 原始格式）
    if merged_v2ray:
        files['quantumult_x.conf'] = merged_v2ray
        log_info(f"✓ Generated quantumult_x.conf")
    
    # 上传到 Gist
    log_info("\n" + "=" * 60)
    success = upload_to_gist(files)
    
    if success:
        log_info("=" * 60)
        log_info("✓ All done!")
        log_info(f"Clash nodes: {proxy_count}")
        if merged_v2ray:
            log_info(f"V2Ray nodes: {len(merged_v2ray.split(chr(10)))}")
        log_info(f"Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        log_error("Upload failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
