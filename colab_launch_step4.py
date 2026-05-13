# ================================================================
# Step4 リモート監視カメラ + AWS Rekognition 起動スクリプト
#
# 【事前準備】
#   import os
#   os.environ["AWS_ACCESS_KEY_ID"]     = "your_key"
#   os.environ["AWS_SECRET_ACCESS_KEY"] = "your_secret"
#   os.environ["AWS_DEFAULT_REGION"]    = "ap-northeast-1"
#
# 【必要なパッケージ】
#   !pip install flask gevent gevent-websocket boto3 opencv-python-headless numpy qrcode[pil] -q
# ================================================================

import subprocess, time, re, sys, io, os
import qrcode
from IPython.display import display, Image as IPImage

PORT    = 5003
APP_DIR = '/content/step4_rekognition'

# 認証ファイルのパスをセット（未設定の場合はデフォルト）
if 'AWS_SHARED_CREDENTIALS_FILE' not in os.environ:
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/content/.aws/credentials'
if 'AWS_CONFIG_FILE' not in os.environ:
    os.environ['AWS_CONFIG_FILE'] = '/content/.aws/config'

# ファイルの存在確認
cred_path = os.environ['AWS_SHARED_CREDENTIALS_FILE']
if os.path.exists(cred_path):
    print(f"✅ 認証ファイル確認済: {cred_path}")
else:
    print(f"⚠️  認証ファイルが見つかりません: {cred_path}")
    print("   /content/.aws/credentials を作成してから再実行してください")

flask_log  = open('/tmp/flask4.log', 'w')
flask_proc = subprocess.Popen(
    [sys.executable, 'app.py'],
    cwd=APP_DIR, stdout=flask_log, stderr=flask_log,
    env=os.environ.copy()
)
time.sleep(3)

cf_log_path = '/tmp/cf4.log'
cf_proc = subprocess.Popen(
    ['cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'],
    stdout=open(cf_log_path,'w'), stderr=subprocess.STDOUT
)

print('URL取得中...')
public_url = None
for _ in range(30):
    time.sleep(1)
    try:
        m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', open(cf_log_path).read())
        if m: public_url = m.group(0); break
    except: pass

if public_url:
    print(f'\n【PC側 送信者URL】\n  {public_url}/?role=sender')
    print(f'\n【スマホ 視聴者URL】\n  {public_url}')
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(public_url)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color='black', back_color='white').save(buf,'PNG')
    buf.seek(0)
    display(IPImage(data=buf.read()))
else:
    print('❌ URL取得失敗'); print(open(cf_log_path).read()[-300:])
    print('Flaskログ:'); print(open('/tmp/flask4.log').read()[-300:])

# 停止: flask_proc.terminate(); cf_proc.terminate()
