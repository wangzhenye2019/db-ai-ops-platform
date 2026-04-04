"""
告警通知发送工具
"""
import json
import time
import hmac
import hashlib
import base64
import requests
from urllib.parse import quote
from flask import current_app


def send_test_notification(channel):
    """发送测试通知"""
    test_message = {
        'title': '【测试】告警通知测试',
        'content': '这是一条测试消息，用于验证通知渠道配置是否正确。',
        'level': 'p2',
        'time': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    return send_notification(channel, test_message)


def send_notification(channel, message):
    """
    发送告警通知

    channel: {
        'channel_type': 'webhook'|'email'|'wechat'|'dingtalk'|'feishu',
        'config': {...}
    }
    message: {
        'title': '告警标题',
        'content': '告警内容',
        'level': 'p0'|'p1'|'p2'|'p3',
        'target_name': '目标名称',
        'metric': '指标名',
        'metric_value': 值,
        'threshold': 阈值,
        'time': '触发时间'
    }
    """
    channel_type = channel['channel_type']
    config = channel.get('config', {})

    try:
        if channel_type == 'webhook':
            return _send_webhook(config, message)
        elif channel_type == 'email':
            return _send_email(config, message)
        elif channel_type == 'wechat':
            return _send_wechat(config, message)
        elif channel_type == 'dingtalk':
            return _send_dingtalk(config, message)
        elif channel_type == 'feishu':
            return _send_feishu(config, message)
        else:
            return False, f'未知的渠道类型: {channel_type}'
    except Exception as e:
        return False, str(e)


def _send_webhook(config, message):
    """发送 Webhook 通知"""
    url = config.get('url')
    if not url:
        return False, 'Webhook URL 未配置'

    headers = config.get('headers', {})
    secret = config.get('secret')

    payload = {
        'title': message['title'],
        'content': message['content'],
        'level': message['level'],
        'timestamp': int(time.time())
    }

    # 如果配置了密钥，添加签名
    if secret:
        sign = _generate_sign(secret, payload['timestamp'])
        payload['sign'] = sign

    response = requests.post(
        url,
        headers={'Content-Type': 'application/json', **headers},
        json=payload,
        timeout=30
    )

    if response.status_code == 200:
        return True, None
    else:
        return False, f'HTTP {response.status_code}: {response.text}'


def _send_email(config, message):
    """发送邮件通知"""
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header

    smtp_host = config.get('smtp_host')
    smtp_port = config.get('smtp_port', 587)
    smtp_user = config.get('smtp_user')
    smtp_password = config.get('smtp_password')
    from_addr = config.get('from_addr', smtp_user)
    to_addrs = config.get('to_addrs', [])

    if not all([smtp_host, smtp_user, smtp_password, to_addrs]):
        return False, '邮件配置不完整'

    level_colors = {
        'p0': '🔴',
        'p1': '🟠',
        'p2': '🟡',
        'p3': '🔵'
    }

    subject = f"{level_colors.get(message['level'], '⚪')} {message['title']}"
    content = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>{message['title']}</h2>
        <p><strong>级别:</strong> {message['level'].upper()}</p>
        <p><strong>目标:</strong> {message.get('target_name', 'N/A')}</p>
        <p><strong>指标:</strong> {message.get('metric', 'N/A')} = {message.get('metric_value', 'N/A')}</p>
        <p><strong>阈值:</strong> {message.get('threshold', 'N/A')}</p>
        <p><strong>时间:</strong> {message['time']}</p>
        <hr>
        <p>{message['content']}</p>
    </body>
    </html>
    """

    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)


def _send_wechat(config, message):
    """发送企业微信通知"""
    corp_id = config.get('corp_id')
    agent_id = config.get('agent_id')
    secret = config.get('secret')

    if not all([corp_id, agent_id, secret]):
        return False, '企业微信配置不完整'

    # 获取 access_token
    token_url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}'
    token_resp = requests.get(token_url, timeout=10).json()

    if token_resp.get('errcode') != 0:
        return False, f"获取token失败: {token_resp.get('errmsg')}"

    access_token = token_resp['access_token']

    level_colors = {
        'p0': '🔴 紧急',
        'p1': '🟠 重要',
        'p2': '🟡 一般',
        'p3': '🔵 提示'
    }

    content = f"""{level_colors.get(message['level'], '⚪')}
{message['title']}

目标: {message.get('target_name', 'N/A')}
指标: {message.get('metric', 'N/A')} = {message.get('metric_value', 'N/A')}
阈值: {message.get('threshold', 'N/A')}
时间: {message['time']}

{message['content']}"""

    send_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
    payload = {
        'touser': config.get('to_user', '@all'),
        'msgtype': 'text',
        'agentid': agent_id,
        'text': {'content': content}
    }

    if config.get('to_party'):
        payload['toparty'] = config['to_party']

    resp = requests.post(send_url, json=payload, timeout=10).json()

    if resp.get('errcode') == 0:
        return True, None
    else:
        return False, resp.get('errmsg', '未知错误')


def _send_dingtalk(config, message):
    """发送钉钉通知"""
    webhook = config.get('webhook')
    secret = config.get('secret')

    if not webhook:
        return False, '钉钉 webhook 未配置'

    # 计算签名
    timestamp = str(round(time.time() * 1000))
    if secret:
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        sign = quote(base64.b64encode(hmac_code), safe='')
        webhook = f'{webhook}&timestamp={timestamp}&sign={sign}'

    level_colors = {
        'p0': '#FF0000',
        'p1': '#FF6600',
        'p2': '#FFCC00',
        'p3': '#0066FF'
    }

    payload = {
        'msgtype': 'markdown',
        'markdown': {
            'title': message['title'],
            'text': f"""## {message['title']}
**级别:** <font color="{level_colors.get(message['level'], '#999999')}">{message['level'].upper()}</font>
**目标:** {message.get('target_name', 'N/A')}
**指标:** {message.get('metric', 'N/A')} = {message.get('metric_value', 'N/A')}
**阈值:** {message.get('threshold', 'N/A')}
**时间:** {message['time']}

{message['content']}"""
        }
    }

    if config.get('at_mobiles') or config.get('at_all'):
        payload['at'] = {
            'atMobiles': config.get('at_mobiles', []),
            'isAtAll': config.get('at_all', False)
        }

    resp = requests.post(webhook, json=payload, timeout=10).json()

    if resp.get('errcode') == 0:
        return True, None
    else:
        return False, resp.get('errmsg', '未知错误')


def _send_feishu(config, message):
    """发送飞书通知"""
    webhook = config.get('webhook')
    secret = config.get('secret')

    if not webhook:
        return False, '飞书 webhook 未配置'

    timestamp = str(int(time.time()))

    # 计算签名
    if secret:
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
    else:
        sign = ''

    level_emojis = {
        'p0': '🔴',
        'p1': '🟠',
        'p2': '🟡',
        'p3': '🔵'
    }

    payload = {
        'timestamp': timestamp,
        'sign': sign,
        'msg_type': 'interactive',
        'card': {
            'header': {
                'title': {
                    'tag': 'plain_text',
                    'content': f"{level_emojis.get(message['level'], '⚪')} {message['title']}"
                },
                'template': message['level'] if message['level'] in ['p0', 'p1', 'p2', 'p3'] else 'blue'
            },
            'elements': [
                {
                    'tag': 'div',
                    'text': {
                        'tag': 'lark_md',
                        'content': f"""**目标:** {message.get('target_name', 'N/A')}
**指标:** {message.get('metric', 'N/A')} = {message.get('metric_value', 'N/A')}
**阈值:** {message.get('threshold', 'N/A')}
**时间:** {message['time']}"""
                    }
                },
                {'tag': 'hr'},
                {
                    'tag': 'div',
                    'text': {
                        'tag': 'plain_text',
                        'content': message['content']
                    }
                }
            ]
        }
    }

    resp = requests.post(webhook, json=payload, timeout=10)

    if resp.status_code == 200:
        return True, None
    else:
        return False, f'HTTP {resp.status_code}: {resp.text}'


def _generate_sign(secret, timestamp):
    """生成签名"""
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode('utf-8')
