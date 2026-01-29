import requests
import traceback
import time
import os
import json
from bs4 import BeautifulSoup

# API 密钥
CF_API_TOKEN    =   os.environ["CF_API_TOKEN"]
CF_ZONE_ID      =   os.environ["CF_ZONE_ID"]

# 域名配置（支持单个或多个逗号分隔的域名）
CF_DNS_NAME_YD  =   os.environ.get("CF_DNS_NAME_YD", "")

# pushplus_token
PUSHPLUS_TOKEN  =   os.environ["PUSHPLUS_TOKEN"]

headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_cf_speed_test_ip_lt(timeout=15, max_retries=3):
    """
    从 https://api.uouin.com/cloudflare.html 获取联通优选IP
    解析HTML表格，筛选出"联通"线路的IP
    """
    url = 'https://api.uouin.com/cloudflare.html'
    
    for attempt in range(max_retries):
        try:
            # 发送 GET 请求
            response = requests.get(url, timeout=timeout, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                # 解析HTML
                soup = BeautifulSoup(response.text, 'lxml')
                
                # 查找表格
                table = soup.find('table')
                if not table:
                    print("未找到表格")
                    continue
                
                # 获取所有行
                rows = table.find_all('tr')
                
                unicom_ips = []
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        # 第一列是线路，第二列是IP
                        line_type = cells[0].get_text(strip=True)
                        ip_address = cells[1].get_text(strip=True)
                        
                        # 筛选联通线路
                        if '联通' in line_type and ip_address:
                            # 排除IPv6地址
                            if ':' not in ip_address:
                                unicom_ips.append(ip_address)
                
                if unicom_ips:
                    print(f"成功获取 {len(unicom_ips)} 个联通优选IP")
                    return ','.join(unicom_ips)
                else:
                    print("未找到联通优选IP")
                    
        except Exception as e:
            traceback.print_exc()
            print(f"get_cf_speed_test_ip_lt Request failed (attempt {attempt + 1}/{max_retries}): {e}")
    
    return None

# 获取 DNS 记录
def get_dns_records(name):
    def_info = []
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        records = response.json()['result']
        for record in records:
            if record['name'] == name:
                def_info.append(record['id'])
        return def_info
    else:
        print('Error fetching DNS records:', response.text)

# 更新 DNS 记录
def update_dns_record(record_id, name, cf_ip):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record_id}'
    data = {
        'type': 'A',
        'name': name,
        'content': cf_ip
    }

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"cf_dns_change success: ---- Time: " + str(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + " ---- ip：" + str(cf_ip))
        return "ip:" + str(cf_ip) + "解析" + str(name) + "成功"
    else:
        traceback.print_exc()
        print(f"cf_dns_change ERROR: ---- Time: " + str(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + " ---- MESSAGE: " + str(response))
        return "ip:" + str(cf_ip) + "解析" + str(name) + "失败"

# 消息推送
def push_plus(content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "IP优选DNSCF推送(联通)",
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }
    body = json.dumps(data).encode(encoding='utf-8')
    headers = {'Content-Type': 'application/json'}
    requests.post(url, data=body, headers=headers)

# 主函数
def main():
    print("=" * 50)
    print("联通优选 DNS 更新脚本")
    print("=" * 50)
    
    # 获取联通优选IP
    ip_addresses_str = get_cf_speed_test_ip_lt()
    if not ip_addresses_str:
        print("Failed to get unicom IP addresses")
        return
    
    ip_addresses = [ip.strip() for ip in ip_addresses_str.split(',')]
    print(f"获取到 {len(ip_addresses)} 个联通优选IP: {ip_addresses[:5]}...")  # 只显示前5个
    
    push_plus_content = []
    
    if not CF_DNS_NAME_YD:
        print("错误: 未配置 CF_DNS_NAME_YD")
        return
    
    # 自动判断：如果包含逗号，就是多域名模式
    if ',' in CF_DNS_NAME_YD:
        # 多域名模式
        dns_names = [name.strip() for name in CF_DNS_NAME_YD.split(',')]
        print(f"\n多域名模式: 共 {len(dns_names)} 个域名")
        print(f"域名列表: {dns_names}")
        
        # 确保 IP 数量足够
        if len(ip_addresses) < len(dns_names):
            print(f"警告: 优选IP数量 ({len(ip_addresses)}) 少于域名数量 ({len(dns_names)})")
        
        # 为每个域名更新 DNS 记录
        for index, dns_name in enumerate(dns_names):
            if index >= len(ip_addresses):
                print(f"跳过域名 {dns_name}: 没有足够的IP")
                break
                
            print(f"\n处理域名: {dns_name}")
            # 获取该域名的所有 DNS 记录
            dns_records = get_dns_records(dns_name)
            
            if not dns_records:
                print(f"未找到域名 {dns_name} 的DNS记录")
                push_plus_content.append(f"❌ {dns_name}: 未找到DNS记录")
                continue
            
            # 使用第一个记录进行更新
            ip_address = ip_addresses[index]
            dns = update_dns_record(dns_records[0], dns_name, ip_address)
            push_plus_content.append(dns)
    
    else:
        # 单域名模式（一个域名对应多个IP/多条DNS记录）
        print(f"\n单域名模式: {CF_DNS_NAME_YD}")
        dns_records = get_dns_records(CF_DNS_NAME_YD)
        
        if not dns_records:
            print(f"未找到域名 {CF_DNS_NAME_YD} 的DNS记录")
            return
        
        # 遍历 IP 地址列表
        for index, ip_address in enumerate(ip_addresses):
            if index >= len(dns_records):
                break
            # 执行 DNS 变更
            dns = update_dns_record(dns_records[index], CF_DNS_NAME_YD, ip_address)
            push_plus_content.append(dns)

    # 发送推送通知
    if push_plus_content:
        push_plus('\n'.join(push_plus_content))
    else:
        print("没有需要推送的内容")

if __name__ == '__main__':
    main()
