from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import os
import socket

# ==================== Flask 应用和 SocketIO ====================
flask_app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
socketio = SocketIO(flask_app, cors_allowed_origins="*", async_mode='threading')
_app_ref = None  # ManagerApp 引用

def set_app(app):
    """设置 ManagerApp 引用"""
    global _app_ref
    _app_ref = app

def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ==================== REST API ====================

@flask_app.route('/')
def index():
    return render_template('mobile.html')

@flask_app.route('/api/status')
def api_status():
    if _app_ref is None:
        return jsonify({"error": "应用未初始化"}), 500
    obs_connected = _app_ref.obs and _app_ref.obs.connected
    current = _app_ref.get_current_display_name()
    return jsonify({
        "obs_connected": obs_connected,
        "active_count": len(_app_ref.active_players),
        "total_count": len(_app_ref.players),
        "current_view": current,
        "local_ip": get_local_ip()
    })

@flask_app.route('/api/players')
def api_players():
    if _app_ref is None:
        return jsonify({"error": "应用未初始化"}), 500
    players_data = []
    for p in _app_ref.players:
        players_data.append({
            "name": p["name"],
            "platform": p["platform"],
            "hotkey": p["hotkey"],
            "active": p.get("active", False),
            "obs_source_name": p.get("obs_source_name", ""),
            "is_current": (_app_ref.get_current_display_name() == p["name"])
        })
    return jsonify({"players": players_data})

@flask_app.route('/api/current')
def api_current():
    if _app_ref is None:
        return jsonify({"error": "应用未初始化"}), 500
    current = _app_ref.get_current_display_name()
    return jsonify({"current": current})

@flask_app.route('/api/switch', methods=['POST'])
def api_switch():
    if _app_ref is None:
        return jsonify({"error": "应用未初始化"}), 500
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "缺少 name 参数"}), 400
    name = data['name']
    player = _app_ref.find_player_in_any(name)
    if not player:
        return jsonify({"error": f"选手 {name} 不存在"}), 404
    if not player.get("active"):
        return jsonify({"error": f"选手 {name} 未激活"}), 400
    _app_ref.switch_to(player)
    return jsonify({"success": True, "switched_to": name})

# ==================== WebSocket 截图推送 ====================

_screenshot_thread = None
_screenshot_running = False

def screenshot_loop():
    """每 500ms 获取活跃选手截图并推送"""
    global _screenshot_running
    while _screenshot_running:
        try:
            if _app_ref and _app_ref.obs and _app_ref.obs.connected:
                for p in _app_ref.active_players:
                    if not p.get("active"):
                        continue
                    src_name = p.get("obs_source_name")
                    if not src_name:
                        continue
                    try:
                        img_b64 = _app_ref.obs.get_source_screenshot(src_name, 480, 270, 50)
                        if img_b64:
                            socketio.emit('screenshot', {
                                "name": p["name"],
                                "platform": p["platform"],
                                "active": p.get("active", False),
                                "is_current": (_app_ref.get_current_display_name() == p["name"]),
                                "image": img_b64,
                                "hotkey": p.get("hotkey", "")
                            })
                    except Exception:
                        pass  # 截图失败静默跳过
        except Exception:
            pass
        time.sleep(0.5)  # 500ms 间隔

def start_screenshot_push():
    global _screenshot_thread, _screenshot_running
    if _screenshot_running:
        return
    _screenshot_running = True
    _screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
    _screenshot_thread.start()

def stop_screenshot_push():
    global _screenshot_running
    _screenshot_running = False

def start_web_server(app_ref):
    """在独立线程启动 Flask 服务器"""
    set_app(app_ref)
    start_screenshot_push()
    ip = get_local_ip()
    port = 5000

    def run():
        try:
            socketio.run(flask_app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
        except Exception as e:
            print(f"[Web遥控] 启动失败: {e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return f"http://{ip}:{port}"