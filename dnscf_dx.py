import requests
import traceback
import time
import os
import json
import re

# Cloudflare API 密钥
CF_API_TOKEN    =   os.environ["CF_API_TOKEN"]
CF_ZONE_ID      =   os.environ["CF_ZONE_ID"]

# 域名配置（支持单个或多个逗号分隔的域名）
CF_DNS_NAME  =   os.environ.get("CF_DNS_NAME", "")

# pushplus_token
PUSHPLUS_TOKEN  =   os.environ["PUSHPLUS_TOKEN"]

# 创建全局 Session 对象，复用连接，减少 SSL 握手失败率
session = requests.Session()
headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}
session.headers.update(headers)

def get_cf_speed_test_ip_dx(timeout=30, max_retries=3):
    """
    从 https://ip.164746.xyz/ 获取优选IP，从第一个开始获取
    不需要使用 Playwright，直接用 requests 加上正则高效解析
    """
    url = 'https://ip.164746.xyz/'
    
    for attempt in range(max_retries):
        try:
            print(f"尝试获取优选IP (第 {attempt + 1}/{max_retries} 次)...")
            req_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            # 获取 IP 不走 CF 的 Session
            response = requests.get(url, headers=req_headers, timeout=timeout)
            
            if response.status_code == 200:
                ips = re.findall(r"copyIP\('([\d\.]+)'\)", response.text)
                
                if not ips:
                    print("主页解析未发现IP，尝试读取 ipTop10.html 接口...")
                    backup_url = 'https://ip.164746.xyz/ipTop10.html'
                    backup_response = requests.get(backup_url, headers=req_headers, timeout=timeout)
                    if backup_response.status_code == 200:
                        ips = [ip.strip() for ip in backup_response.text.split(',') if ip.strip()]
                
                telecom_ips = [ip for ip in ips if ':' not in ip]
                
                if telecom_ips:
                    seen = set()
                    unique_ips = [x for x in telecom_ips if not (x in seen or seen.add(x))]
                    print(f"成功获取 {len(unique_ips)} 个优选IP (已按推荐顺序排列)")
                    return ','.join(unique_ips)
                else:
                    print("没有找到有效的 IPv4 优选IP")
            else:
                print(f"获取失败，HTTP 状态码: {response.status_code}")
                    
        except Exception as e:
            traceback.print_exc()
            print(f"get_cf_speed_test_ip_dx Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(3)
    
    return None

# 获取 DNS 记录（加入了错误重试与超时控制）
def get_dns_records(name, max_retries=3):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records'
    
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
            if response.status_code == 200:
                records = response.json()['result']
                def_info = [record['id'] for record in records if record['name'] == name]
                return def_info
            else:
                print(f'获取 DNS 记录失败 (尝试 {attempt + 1}/{max_retries}): {response.text}')
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"连接 Cloudflare API 失败 (第 {attempt + 1}/{max_retries} 次尝试): {e}，正在重试...")
            time.sleep(3)  # 遇到连接重置，先睡 3 秒再试
            
    print(f"获取域名 {name} 的 DNS 记录最终失败")
    return []

# 更新 DNS 记录（加入了错误重试与超时控制）
def update_dns_record(record_id, name, cf_ip, max_retries=3):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record_id}'
    data = {
        'type': 'A',
        'name': name,
        'content': cf_ip,
        'ttl': 60
    }

    for attempt in range(max_retries):
        try:
            response = session.put(url, json=data, timeout=15)
            if response.status_code == 200:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"cf_dns_change success: ---- Time: {current_time} ---- ip：{cf_ip}")
                return f"ip:{cf_ip}解析{name}成功"
            else:
                print(f"更新 DNS 记录失败 (尝试 {attempt + 1}/{max_retries}): {response.text}")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"更新 DNS 记录连接失败 (第 {attempt + 1}/{max_retries} 次尝试): {e}，正在重试...")
            time.sleep(3)

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"cf_dns_change ERROR: ---- Time: {current_time} ---- ip：{cf_ip} 最终失败")
    return f"ip:{cf_ip}解析{name}失败"

# 消息推送
def push_plus(content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "IP优选DNSCF推送(电信)",
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }
    body = json.dumps(data).encode(encoding='utf-8')
    req_headers = {'Content-Type': 'application/json'}
    try:
        requests.post(url, data=body, headers=req_headers, timeout=10)
    except Exception as e:
        print(f"推送消息失败: {e}")

# 主函数
def main():
    print("=" * 50)
    print("电信优选 DNS 更新脚本 (164746.xyz API轻量加固版)")
    print("=" * 50)
    
    # 获取电信优选IP
    ip_addresses_str = get_cf_speed_test_ip_dx()
    if not ip_addresses_str:
        print("Failed to get telecom IP addresses")
        return
    
    ip_addresses = [ip.strip() for ip in ip_addresses_str.split(',')]
    print(f"获取到 {len(ip_addresses)} 个优选IP: {ip_addresses[:5]}...")  # 只显示前5个
    
    push_plus_content = []
    
    if not CF_DNS_NAME:
        print("错误: 未配置 CF_DNS_NAME")
        return
    
    # 自动判断：如果包含逗号，就是多域名模式
    if ',' in CF_DNS_NAME:
        # 多域名模式
        dns_names = [name.strip() for name in CF_DNS_NAME.split(',')]
        print(f"\n多域名模式: 共 {len(dns_names)} 个域名")
        print(f"域名列表: {dns_names}")
        
        if len(ip_addresses) < len(dns_names):
            print(f"警告: 优选IP数量 ({len(ip_addresses)}) 少于域名数量 ({len(dns_names)})")
        
        for index, dns_name in enumerate(dns_names):
            if index >= len(ip_addresses):
                print(f"跳过域名 {dns_name}: 没有足够的IP")
                break
                
            print(f"\n处理域名: {dns_name}")
            dns_records = get_dns_records(dns_name)
            
            if not dns_records:
                print(f"未找到域名 {dns_name} 的DNS记录")
                push_plus_content.append(f"❌ {dns_name}: 未找到DNS记录")
                continue
            
            ip_address = ip_addresses[index]
            dns = update_dns_record(dns_records[0], dns_name, ip_address)
            push_plus_content.append(dns)
            
            # 每处理完一个域名，强制冷却 2 秒，防止请求过快被 Cloudflare 拦截
            time.sleep(2)
    
    else:
        # 单域名模式（一个域名对应多个IP/多条DNS记录）
        print(f"\n单域名模式: {CF_DNS_NAME}")
        dns_records = get_dns_records(CF_DNS_NAME)
        
        if not dns_records:
            print(f"未找到域名 {CF_DNS_NAME} 的DNS记录")
            return
        
        for index, ip_address in enumerate(ip_addresses):
            if index >= len(dns_records):
                break
            dns = update_dns_record(dns_records[index], CF_DNS_NAME, ip_address)
            push_plus_content.append(dns)
            
            # 同样加入冷却延迟
            time.sleep(2)

    # 发送推送通知
    if push_plus_content:
        push_plus('\n'.join(push_plus_content))
    else:
        print("没有需要推送的内容")

if __name__ == '__main__':
    main()
