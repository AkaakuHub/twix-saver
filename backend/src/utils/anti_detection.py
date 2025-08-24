"""
多層的アンチ検知システム
"""

import random
import time
import asyncio
from typing import Dict, List, Optional
from fake_useragent import UserAgent

from src.config.settings import settings
from src.utils.logger import setup_logger


class AntiDetectionManager:
    """アンチ検知対策の統合管理クラス"""
    
    def __init__(self):
        self.logger = setup_logger("anti_detection")
        self.user_agent_generator = UserAgent()
        self._user_agent_pool = settings.user_agents.copy()
        
        # 使用統計
        self.request_count = 0
        self.last_request_time = 0
        self.current_session_requests = 0
        
        self.logger.info("アンチ検知管理システムを初期化しました")
    
    def get_random_user_agent(self, use_fake_useragent: bool = False) -> str:
        """ランダムなUser-Agentを取得"""
        if use_fake_useragent:
            try:
                return self.user_agent_generator.random
            except Exception as e:
                self.logger.warning(f"fake-useragent エラー: {e}, プリセットを使用")
        
        return random.choice(self._user_agent_pool)
    
    def should_rotate_user_agent(self) -> bool:
        """User-Agentをローテーションするべきかの判定"""
        # 一定リクエスト数ごとにローテーション
        return self.current_session_requests > 0 and self.current_session_requests % 50 == 0
    
    async def human_like_delay(
        self, 
        min_delay: float = 1.0, 
        max_delay: float = 3.0,
        action_type: str = "general"
    ) -> None:
        """人間らしい遅延パターン"""
        
        # アクションタイプに応じた遅延調整
        delay_multipliers = {
            "login": (2.0, 5.0),
            "scroll": (1.5, 4.0),
            "click": (0.5, 2.0),
            "navigation": (2.0, 6.0),
            "general": (1.0, 3.0)
        }
        
        if action_type in delay_multipliers:
            base_min, base_max = delay_multipliers[action_type]
            min_delay = max(min_delay, base_min)
            max_delay = max(max_delay, base_max)
        
        # ランダムな遅延（正規分布を使用してより自然に）
        delay = random.uniform(min_delay, max_delay)
        
        # 時々長めの休憩（人間らしい不規則性）
        if random.random() < 0.1:  # 10%の確率
            delay += random.uniform(5, 15)
            self.logger.debug(f"長めの休憩: {delay:.2f}秒")
        
        self.logger.debug(f"{action_type} 遅延: {delay:.2f}秒")
        await asyncio.sleep(delay)
        
        # リクエスト統計更新
        self.request_count += 1
        self.current_session_requests += 1
        self.last_request_time = time.time()
    
    async def rate_limit_check(self) -> bool:
        """レート制限チェック"""
        current_time = time.time()
        
        # 直前のリクエストから最小間隔をチェック
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            min_interval = 1.0  # 最小1秒間隔
            
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                self.logger.info(f"レート制限: {wait_time:.2f}秒待機")
                await asyncio.sleep(wait_time)
        
        # セッション内リクエスト数チェック
        if self.current_session_requests > settings.scraping.max_tweets_per_session:
            self.logger.warning("セッション内最大リクエスト数に到達")
            return False
        
        return True
    
    def get_randomized_viewport(self) -> Dict[str, int]:
        """ランダム化されたビューポートサイズ"""
        base_width = settings.anti_detection.viewport_width
        base_height = settings.anti_detection.viewport_height
        
        # ±50ピクセルの範囲でランダム化
        width = base_width + random.randint(-50, 50)
        height = base_height + random.randint(-50, 50)
        
        # 最小サイズを保証
        width = max(width, 1024)
        height = max(height, 768)
        
        return {"width": width, "height": height}
    
    def get_browser_args(self) -> List[str]:
        """ステルス用のブラウザ引数"""
        args = [
            # 自動化検知を無効化
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            
            # パフォーマンス最適化
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            
            # 追加のフィンガープリント対策
            "--disable-ipc-flooding-protection",
            "--disable-background-networking",
            "--disable-sync",
            "--no-zygote",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            
            # GPU関連
            "--disable-gpu",
            "--disable-software-rasterizer"
        ]
        
        # ランダムなウィンドウサイズ
        viewport = self.get_randomized_viewport()
        args.append(f"--window-size={viewport['width']},{viewport['height']}")
        
        return args
    
    async def simulate_mouse_movement(self, page, element_selector: str):
        """マウス移動のシミュレーション"""
        try:
            # 要素の位置を取得
            element = await page.query_selector(element_selector)
            if element:
                box = await element.bounding_box()
                if box:
                    # 要素の中心に向かって段階的にマウスを移動
                    target_x = box["x"] + box["width"] / 2
                    target_y = box["y"] + box["height"] / 2
                    
                    # 現在のマウス位置から段階的に移動
                    steps = random.randint(3, 8)
                    for i in range(steps):
                        progress = (i + 1) / steps
                        x = target_x * progress
                        y = target_y * progress
                        
                        await page.mouse.move(x, y)
                        await asyncio.sleep(random.uniform(0.05, 0.2))
                    
                    # 要素上で少し待機
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    
        except Exception as e:
            self.logger.debug(f"マウス移動シミュレーションエラー: {e}")
    
    def should_take_break(self) -> bool:
        """休憩を取るべきかの判定"""
        # 一定時間経過後や一定リクエスト数後に休憩を推奨
        if self.current_session_requests > 0:
            if self.current_session_requests % 100 == 0:  # 100リクエストごと
                return True
        
        current_time = time.time()
        if self.last_request_time > 0:
            session_duration = current_time - (self.last_request_time - self.current_session_requests)
            if session_duration > 3600:  # 1時間以上のセッション
                return True
        
        return False
    
    async def take_break(self):
        """人間らしい休憩の実行"""
        break_duration = random.uniform(300, 900)  # 5-15分
        self.logger.info(f"休憩中: {break_duration/60:.1f}分")
        
        await asyncio.sleep(break_duration)
        
        # セッション統計をリセット
        self.current_session_requests = 0
    
    def get_realistic_timing_profile(self) -> Dict[str, float]:
        """現実的なタイミングプロファイル"""
        return {
            "typing_delay": random.uniform(0.1, 0.3),  # キー入力間隔
            "click_delay": random.uniform(0.2, 0.8),   # クリック前の待機
            "page_load_wait": random.uniform(2.0, 5.0), # ページ読み込み待機
            "scroll_delay": random.uniform(1.0, 3.0),   # スクロール間隔
            "navigation_delay": random.uniform(2.0, 6.0) # ナビゲーション間隔
        }


class CaptchaDetector:
    """CAPTCHA検知と対応システム"""
    
    def __init__(self):
        self.logger = setup_logger("captcha_detector")
        self.captcha_selectors = [
            # 一般的なCAPTCHAセレクタ
            '[aria-label*="captcha"]',
            '.captcha',
            '#captcha',
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            # Twitter固有のチャレンジ
            '[data-testid="ocfChallengeForm"]',
            '[data-testid="challenge"]'
        ]
    
    async def detect_captcha(self, page) -> bool:
        """CAPTCHAの存在を検知"""
        try:
            for selector in self.captcha_selectors:
                if await page.is_visible(selector, timeout=1000):
                    self.logger.warning(f"CAPTCHA検知: {selector}")
                    return True
            return False
        except Exception as e:
            self.logger.debug(f"CAPTCHA検知エラー: {e}")
            return False
    
    async def handle_captcha(self, page) -> bool:
        """CAPTCHA対応処理"""
        if not settings.captcha_service_api_key:
            self.logger.error("CAPTCHA解決サービスが設定されていません")
            return False
        
        self.logger.info("CAPTCHA解決を試行中...")
        
        # ここでサードパーティのCAPTCHA解決サービスを呼び出し
        # 例: 2Captcha, Anti-Captcha など
        
        # プレースホルダー実装
        await asyncio.sleep(30)  # CAPTCHA解決待機時間
        
        self.logger.warning("CAPTCHA解決機能は未実装です")
        return False


# グローバルインスタンス
anti_detection = AntiDetectionManager()
captcha_detector = CaptchaDetector()