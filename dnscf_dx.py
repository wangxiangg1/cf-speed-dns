import requests
import traceback
import time
import os
import re

# Cloudflare API 密钥
CF_API_TOKEN    =   os.environ["CF_API_TOKEN"]
CF_ZONE_ID      =   os.environ["CF_ZONE_ID"]

# 域名配置（支持单个或多个逗号分隔的域名）
CF_DNS_NAME  =   os.environ.get("CF_DNS_NAME", "")

# 创建全局 Session 对象，复用连接，减少 SSL 握手失败率
session = requests.Session()
headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}
session.headers.update(headers)

def get_cf_speed_test_ip_dx(timeout=30, max_retries=3):
    """
    从 https://ip.164746.xyz/ 获取优选IP
    """
    url = 'https://ip.164746.xyz/'
    
    for attempt in range(max_retries):
        try:
            print(f"尝试获取优选IP (第 {attempt + 1}/{max_retries} 次)...")
            req_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
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
            print(f"get_cf_speed_test_ip_dx 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            time.sleep(3)
    
    return None

# 获取 DNS 记录
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
            print(f"连接 Cloudflare 失败 (第 {attempt + 1}/{max_retries} 次尝试): {e}，正在重试...")
            time.sleep(3)
            
    print(f"获取域名 {name} 的 DNS 记录最终失败")
    return []

# 更新 DNS 记录
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
                print(f"cf_dns_change success: ---- {current_time} ---- ip：{cf_ip}")
                return True
            else:
                print(f"更新 DNS 记录失败 (尝试 {attempt + 1}/{max_retries}): {response.text}")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"更新 DNS 连接失败 (第 {attempt + 1}/{max_retries} 次尝试): {e}，正在重试...")
            time.sleep(3)

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"cf_dns_change ERROR: ---- {current_time} ---- ip：{cf_ip} 最终失败")
    return False

# 主函数
def main():
    print("=" * 50)
    print("电信优选 DNS 更新脚本 (精简纯净版)")
    print("=" * 50)
    
    # 获取电信优选IP
    ip_addresses_str = get_cf_speed_test_ip_dx()
    if not ip_addresses_str:
        print("无法获取有效的电信优选 IP，流程终止。")
        return
    
    ip_addresses = [ip.strip() for ip in ip_addresses_str.split(',')]
    print(f"获取到 {len(ip_addresses)} 个优选IP: {ip_addresses[:5]}...")
    
    if not CF_DNS_NAME:
        print("错误: 未配置 CF_DNS_NAME 环境变量")
        return
    
    # 多域名模式
    if ',' in CF_DNS_NAME:
        dns_names = [name.strip() for name in CF_DNS_NAME.split(',')]
        print(f"\n[多域名模式]: 共 {len(dns_names)} 个域名")
        
        if len(ip_addresses) < len(dns_names):
            print(f"警告: 优选IP数量 ({len(ip_addresses)}) 少于域名数量 ({len(dns_names)})")
        
        for index, dns_name in enumerate(dns_names):
            if index >= len(ip_addresses):
                print(f"跳过域名 {dns_name}: 没有足够的IP分配")
                break
                
            print(f"\n正在处理: {dns_name}")
            dns_records = get_dns_records(dns_name)
            
            if not dns_records:
                print(f"未找到域名 {dns_name} 的 DNS 记录，请确认该记录已在 CF 后台手动创建过。")
                continue
            
            ip_address = ip_addresses[index]
            update_dns_record(dns_records[0], dns_name, ip_address)
            
            # 协同冷却，防止请求过快
            time.sleep(2)
    
    # 单域名模式
    else:
        print(f"\n[单域名模式]: {CF_DNS_NAME}")
        dns_records = get_dns_records(CF_DNS_NAME)
        
        if not dns_records:
            print(f"未找到域名 {CF_DNS_NAME} 的 DNS 记录，请确认该记录已在 CF 后台手动创建过。")
            return
        
        for index, ip_address in enumerate(ip_addresses):
            if index >= len(dns_records):
                break
            update_dns_record(dns_records[index], CF_DNS_NAME, ip_address)
            time.sleep(2)

    print("\n=" * 50)
    print("所有 DNS 记录更新流程结束。")
    print("=" * 50)

if __name__ == '__main__':
    main()
