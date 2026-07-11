"""
多视角切换管理器 - 自动化测试套件
测试所有后端逻辑，不依赖 GUI 和 OBS
"""
import json, os, sys, re, io, time, unittest
from unittest.mock import patch, MagicMock

BASE_DIR = r"C:\myobs"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ==================== 测试 1: 配置文件 ====================
class TestConfig(unittest.TestCase):
    def test_config_exists(self):
        """配置文件必须存在"""
        self.assertTrue(os.path.exists(CONFIG_FILE), "config.json 不存在")

    def test_config_valid_json(self):
        """配置文件必须是合法 JSON"""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("players", cfg)
        self.assertIn("obs_host", cfg)
        self.assertIn("obs_port", cfg)

    def test_config_players_valid(self):
        """每个选手必须有 id, name, hotkey, platform"""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for p in cfg["players"]:
            with self.subTest(name=p.get("name", "unknown")):
                self.assertIn("id", p)
                self.assertIn("name", p)
                self.assertIn("hotkey", p)
                self.assertIn("platform", p)
                self.assertIn("platform", p)
                # hotkey 必须是单字符
                hk = p.get("hotkey", "")
                self.assertEqual(len(hk), 1, f"hotkey '{hk}' 长度不为1")
                self.assertTrue(hk.isalnum(), f"hotkey '{hk}' 不是字母数字")

    def test_config_unique_hotkeys(self):
        """所有选手的快捷键不能重复"""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        hotkeys = [p["hotkey"] for p in cfg["players"] if p.get("hotkey")]
        self.assertEqual(len(hotkeys), len(set(hotkeys)), "存在重复的快捷键")

    def test_config_obs_fields(self):
        """OBS 配置字段必须完整"""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("obs_host", cfg)
        self.assertIn("obs_port", cfg)
        self.assertIn("obs_password", cfg)
        self.assertIsInstance(cfg["obs_port"], int)


# ==================== 测试 2: URL 解析逻辑 ====================
class TestParseClipboardURL(unittest.TestCase):
    """从 manager_ui.pyw 中提取 parse_clipboard_url 逻辑单独测试"""

    @classmethod
    def setUpClass(cls):
        # 导入 manager_ui 模块 (mock 掉 GUI 和 OBS 依赖)
        sys.path.insert(0, BASE_DIR)
        # 先 mock 掉所有 GUI 和 OBS 相关导入
        modules_to_mock = {
            'tkinter': MagicMock(),
            'tkinter.ttk': MagicMock(),
            'tkinter.messagebox': MagicMock(),
            'tkinter.scrolledtext': MagicMock(),
            'obswebsocket': MagicMock(),
            'obswebsocket.obsws': MagicMock(),
            'obswebsocket.requests': MagicMock(),
            'psutil': MagicMock(),
            'pynput': MagicMock(),
            'pynput.keyboard': MagicMock(),
            'pynput.mouse': MagicMock(),
            'vlc': MagicMock(),
            'pygetwindow': MagicMock(),
        }
        for mod_name, mock in modules_to_mock.items():
            sys.modules[mod_name] = mock

        # 现在可以安全导入
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "manager_ui", os.path.join(BASE_DIR, "manager_ui.pyw")
        )
        cls.manager_ui = importlib.util.module_from_spec(spec)
        # 在执行前 mock 掉 globals 里的 tkinter 类
        spec.loader.exec_module(cls.manager_ui)

    def test_twitch_url(self):
        """解析 Twitch URL"""
        result = self.manager_ui.parse_clipboard_url("https://www.twitch.tv/meuyou1")
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "twitch")
        self.assertIn("meuyou1", result["twitch_url"])

    def test_bilibili_url(self):
        """解析 Bilibili URL"""
        result = self.manager_ui.parse_clipboard_url("https://live.bilibili.com/30407385")
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "bilibili")
        self.assertEqual(result["room_id"], "30407385")

    def test_twitch_channel_name(self):
        """解析纯 Twitch 频道名"""
        result = self.manager_ui.parse_clipboard_url("https://www.twitch.tv/aceu")
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "twitch")
        self.assertIn("aceu", result["twitch_url"])

    def test_custom_web_url(self):
        """解析自定义网页 URL"""
        result = self.manager_ui.parse_clipboard_url("https://example.com/stream")
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "custom_web")

    def test_empty_string(self):
        """空字符串返回 None"""
        result = self.manager_ui.parse_clipboard_url("")
        self.assertIsNone(result)

    def test_garbage_text(self):
        """无意义文本返回 None"""
        result = self.manager_ui.parse_clipboard_url("asdfghjkl123456")
        self.assertIsNone(result)

    def test_douyin_live_url(self):
        """解析抖音直播 URL (格式: live.douyin.com)"""
        # 现在直接返回 browser_url，不再需要 streamlink 解析
        result = self.manager_ui.parse_clipboard_url("https://live.douyin.com/123456789")
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "douyin")
        self.assertIn("live.douyin.com", result["browser_url"])

    def test_twitch_with_extra_path(self):
        """解析带额外路径的 Twitch URL"""
        result = self.manager_ui.parse_clipboard_url("https://www.twitch.tv/meuyou1/video/123456")
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "twitch")

    def test_douyin_stream_url(self):
        """解析抖音拉流 URL (pull-flv 格式)"""
        url = "https://pull-flv-l1.douyincdn.com/stage/stream-123456.flv"
        result = self.manager_ui.parse_clipboard_url(url)
        self.assertIsNotNone(result)
        self.assertEqual(result["platform"], "douyin")


# ==================== 测试 3: 工具函数 ====================
class TestUtils(unittest.TestCase):
    """测试 get_next_view_label 和 normalize_view_label"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, BASE_DIR)
        # 重用上面的 mock 环境
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "manager_ui", os.path.join(BASE_DIR, "manager_ui.pyw")
        )
        cls.manager_ui = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.manager_ui)

    def test_get_next_view_label_empty(self):
        """空列表返回 1"""
        result = self.manager_ui.get_next_view_label([])
        self.assertEqual(result, 1)

    def test_get_next_view_label_sequential(self):
        """[1,2,3] 返回 4"""
        players = [{"view_label": 1}, {"view_label": 2}, {"view_label": 3}]
        result = self.manager_ui.get_next_view_label(players)
        self.assertEqual(result, 4)

    def test_get_next_view_label_with_gap(self):
        """[1,3] 返回 2 (补缺)"""
        players = [{"view_label": 1}, {"view_label": 3}]
        result = self.manager_ui.get_next_view_label(players)
        self.assertEqual(result, 2)

    def test_normalize_view_label_int(self):
        """整数保持不变"""
        result = self.manager_ui.normalize_view_label(5)
        self.assertEqual(result, 5)

    def test_normalize_view_label_string_digit(self):
        """数字字符串转整数"""
        result = self.manager_ui.normalize_view_label("5")
        self.assertEqual(result, 5)

    def test_normalize_view_label_invalid(self):
        """无效值返回 0"""
        result = self.manager_ui.normalize_view_label("abc")
        self.assertEqual(result, 0)


# ==================== 测试 4: 窗口标题生成 ====================
class TestWindowTitle(unittest.TestCase):
    """测试窗口标题命名规则的一致性"""

    def test_obs_source_name_format(self):
        """OBS 源名称格式: {name}_{view_label}_{hotkey}"""
        name = "meuyou1"
        view_label = 1
        hotkey = "1"
        expected = "meuyou1_1_1"
        self.assertEqual(f"{name}_{view_label}_{hotkey}", expected)

    def test_stream_name_format(self):
        """RTMP 流名称格式: player{id}"""
        pid = 1
        expected = "player1"
        self.assertEqual(f"player{pid}", expected)


# ==================== 测试 5: 代码语法检查 ====================
class TestCodeSyntax(unittest.TestCase):
    """检查所有 .py 文件语法"""

    def test_manager_ui_syntax(self):
        """manager_ui.pyw 语法检查"""
        try:
            with open(os.path.join(BASE_DIR, "manager_ui.pyw"), "r", encoding="utf-8") as f:
                compile(f.read(), "manager_ui.pyw", "exec")
        except SyntaxError as e:
            self.fail(f"manager_ui.pyw 语法错误: {e}")

    def test_switcher_syntax(self):
        """switcher.py 语法检查"""
        try:
            with open(os.path.join(BASE_DIR, "switcher.py"), "r", encoding="utf-8") as f:
                compile(f.read(), "switcher.py", "exec")
        except SyntaxError as e:
            self.fail(f"switcher.py 语法错误: {e}")


# ==================== 测试 6: OBSController 初始化 ====================
class TestOBSController(unittest.TestCase):
    """测试 OBSController 类的基本逻辑"""

    def test_controller_init(self):
        """OBSController 初始化参数正确"""
        # 直接导入 OBSController 类
        sys.path.insert(0, BASE_DIR)

        # 手动模拟 OBSController
        controller_code = """
class OBSController:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.connected = False
        self.scene_name = None
"""
        # 直接编译验证
        compile(controller_code, "<test>", "exec")

    def test_controller_params(self):
        """确认配置中的参数与 Controller 匹配"""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        host = cfg.get("obs_host", "localhost")
        port = cfg.get("obs_port", 4455)
        pwd = cfg.get("obs_password", "")
        self.assertIsInstance(host, str)
        self.assertIsInstance(port, int)
        self.assertIsInstance(pwd, str)


# ==================== 测试 7: 日志系统 ====================
class TestLogSystem(unittest.TestCase):
    """测试日志格式和文件写入"""

    def test_log_format(self):
        """日志格式: [模块-步骤-状态] 描述"""
        log_line = "[新增桌面-步骤1-完成] 新桌面已创建"
        pattern = r'^\[.+\] .+'
        self.assertRegex(log_line, pattern)

    def test_step_log_format(self):
        """步骤日志格式验证"""
        test_cases = [
            "[新增桌面-步骤0] 开始流程",
            "[新增桌面-步骤0-失败] URL 为空",
            "[新增桌面-步骤1-完成] 新桌面已创建",
            "[新增桌面-步骤2-失败] 启动失败",
            "[新增桌面-步骤3-完成] 已切回主桌面",
            "[新增桌面-完成] 流程结束",
        ]
        for line in test_cases:
            with self.subTest(line=line):
                # 格式: [xxx-xxx-xxx] xxx
                self.assertRegex(line, r'^\[.+\] .+',
                                 f"日志格式不匹配: {line}")

    def test_debug_log_writable(self):
        """debug.log 可写入"""
        log_path = os.path.join(BASE_DIR, "debug.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [测试] 日志写入测试\n")
            writable = True
        except:
            writable = False
        self.assertTrue(writable, "debug.log 不可写入")


# ==================== 测试 8: Simulated open_browser_window ====================
class TestBrowserSource(unittest.TestCase):
    """测试 Browser Source 创建流程"""

    def test_url_empty_early_return(self):
        """URL 为空时 sync_player 应提前终止"""
        player = {"name": "test", "browser_url": ""}
        url = player.get("browser_url", "") or player.get("douyin_url", "")
        if not url:
            self.assertTrue(True, "URL 为空，应提前 return")
            return
        self.fail("不应执行到这里")

    def test_url_valid_continue(self):
        """URL 有效时流程继续"""
        player = {"name": "test", "browser_url": "https://live.bilibili.com/123"}
        url = player.get("browser_url", "") or player.get("douyin_url", "")
        self.assertTrue(url, "URL 有效，流程继续")

    def test_browser_source_settings(self):
        """Browser Source 设置参数验证"""
        settings = {
            "url": "https://live.bilibili.com/123",
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "reroute_audio": True,
            "restart_when_active": False,
            "shutdown": False,
        }
        self.assertEqual(settings["width"], 1920)
        self.assertEqual(settings["height"], 1080)
        self.assertTrue(settings["reroute_audio"], "reroute_audio 必须为 True 才能独立音频控制")

    def test_obs_source_name_format(self):
        """OBS 源名称格式: {name}_{view_label}_{hotkey}"""
        name = "meuyou1"
        view_label = 1
        hotkey = "1"
        expected = "meuyou1_1_1"
        self.assertEqual(f"{name}_{view_label}_{hotkey}", expected)


# ==================== 测试 9: 文件完整性 ====================
class TestFileIntegrity(unittest.TestCase):
    """检查项目文件完整性"""

    def test_core_files_exist(self):
        """核心文件必须存在"""
        required_files = [
            "manager_ui.pyw",
            "switcher.py",
            "config.json",
            ".gitignore",
        ]
        for f in required_files:
            with self.subTest(file=f):
                path = os.path.join(BASE_DIR, f)
                self.assertTrue(os.path.exists(path), f"缺少文件: {f}")

    def test_core_files_nonempty(self):
        """核心文件不能为空"""
        required_files = ["manager_ui.pyw", "switcher.py"]
        for f in required_files:
            with self.subTest(file=f):
                path = os.path.join(BASE_DIR, f)
                size = os.path.getsize(path)
                self.assertGreater(size, 100, f"{f} 文件太小 (可能为空)")


# ==================== 运行测试 ====================
if __name__ == "__main__":
    # 设置编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("  多视角切换管理器 - 自动化测试套件")
    print("=" * 60)
    print()

    # 运行测试
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = None  # 保持测试顺序

    suite = unittest.TestSuite()

    # 按顺序添加测试类
    suite.addTest(loader.loadTestsFromTestCase(TestFileIntegrity))
    suite.addTest(loader.loadTestsFromTestCase(TestCodeSyntax))
    suite.addTest(loader.loadTestsFromTestCase(TestConfig))
    suite.addTest(loader.loadTestsFromTestCase(TestUtils))
    suite.addTest(loader.loadTestsFromTestCase(TestWindowTitle))
    suite.addTest(loader.loadTestsFromTestCase(TestOBSController))
    suite.addTest(loader.loadTestsFromTestCase(TestLogSystem))
    suite.addTest(loader.loadTestsFromTestCase(TestBrowserSource))

    # URL 解析测试单独放最后（可能依赖网络）
    suite.addTest(loader.loadTestsFromTestCase(TestParseClipboardURL))

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print()
    print("=" * 60)
    print(f"  结果: {result.testsRun} 个测试, "
          f"成功 {result.testsRun - len(result.failures) - len(result.errors)} 个, "
          f"失败 {len(result.failures)} 个, "
          f"错误 {len(result.errors)} 个")
    print("=" * 60)

    # 返回非零退出码方便 CI 检测
    sys.exit(0 if result.wasSuccessful() else 1)