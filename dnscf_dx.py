import requests
import traceback
import time
import os
import json
from playwright.sync_api import sync_playwright

# Cloudflare API 密钥
CF_API_TOKEN    =   os.environ["CF_API_TOKEN"]
CF_ZONE_ID      =   os.environ["CF_ZONE_ID"]

# 域名配置（支持单个或多个逗号分隔的域名）
CF_DNS_NAME_DX  =   os.environ.get("CF_DNS_NAME_DX", "")

# pushplus_token
PUSHPLUS_TOKEN  =   os.environ["PUSHPLUS_TOKEN"]

headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_cf_speed_test_ip_dx(timeout=30, max_retries=3):
    """
    使用 Playwright 无头浏览器从 https://api.uouin.com/cloudflare.html 获取电信优选IP
    等待 JavaScript 动态加载完成后再解析数据
    """
    url = 'https://api.uouin.com/cloudflare.html'
    
    for attempt in range(max_retries):
        try:
            print(f"尝试获取优选IP (第 {attempt + 1}/{max_retries} 次)...")
            
            with sync_playwright() as p:
                # 启动无头浏览器
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 访问页面
                page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
                
                # 等待表格加载完成（等待包含"电信"的单元格出现）
                page.wait_for_selector('td:has-text("电信")', timeout=15000)
                
                # 额外等待一下确保数据完全加载
                time.sleep(2)
                
                # 获取所有表格行
                rows = page.query_selector_all('table tr')
                
                telecom_ips = []
                
                for row in rows:
                    cells = row.query_selector_all('td')
                    if len(cells) >= 2:
                        # 第一列是线路，第二列是IP
                        line_type = cells[0].inner_text().strip()
                        ip_address = cells[1].inner_text().strip()
                        
                        # 筛选电信线路
                        if '电信' in line_type and ip_address:
                            # 排除IPv6地址
                            if ':' not in ip_address:
                                telecom_ips.append(ip_address)
                                print(f"  找到电信IP: {ip_address}")
                
                browser.close()
                
                if telecom_ips:
                    print(f"成功获取 {len(telecom_ips)} 个电信优选IP")
                    return ','.join(telecom_ips)
                else:
                    print("未找到电信优选IP")
                    
        except Exception as e:
            traceback.print_exc()
            print(f"get_cf_speed_test_ip_dx Request failed (attempt {attempt + 1}/{max_retries}): {e}")
    
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
        "title": "IP优选DNSCF推送(电信)",
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
    print("电信优选 DNS 更新脚本 (Playwright版)")
    print("=" * 50)
    
    # 获取电信优选IP
    ip_addresses_str = get_cf_speed_test_ip_dx()
    if not ip_addresses_str:
        print("Failed to get telecom IP addresses")
        return
    
    ip_addresses = [ip.strip() for ip in ip_addresses_str.split(',')]
    print(f"获取到 {len(ip_addresses)} 个电信优选IP: {ip_addresses[:5]}...")  # 只显示前5个
    
    push_plus_content = []
    
    if not CF_DNS_NAME_DX:
        print("错误: 未配置 CF_DNS_NAME_DX")
        return
    
    # 自动判断：如果包含逗号，就是多域名模式
    if ',' in CF_DNS_NAME_DX:
        # 多域名模式
        dns_names = [name.strip() for name in CF_DNS_NAME_DX.split(',')]
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
        print(f"\n单域名模式: {CF_DNS_NAME_DX}")
        dns_records = get_dns_records(CF_DNS_NAME_DX)
        
        if not dns_records:
            print(f"未找到域名 {CF_DNS_NAME_DX} 的DNS记录")
            return
        
        # 遍历 IP 地址列表
        for index, ip_address in enumerate(ip_addresses):
            if index >= len(dns_records):
                break
            # 执行 DNS 变更
            dns = update_dns_record(dns_records[index], CF_DNS_NAME_DX, ip_address)
            push_plus_content.append(dns)

    # 发送推送通知
    if push_plus_content:
        push_plus('\n'.join(push_plus_content))
    else:
        print("没有需要推送的内容")

if __name__ == '__main__':
    main()
