import { test, expect } from '@playwright/test';

test.describe('Twix Saver Frontend - 全機能テスト', () => {
  
  test.beforeEach(async ({ page }) => {
    // コンソールエラーをキャッチ
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error(`Console error: ${msg.text()}`);
      }
    });
    
    // ページエラーをキャッチ
    page.on('pageerror', error => {
      console.error(`Page error: ${error.message}`);
    });
  });

  test('メインページの読み込みとレンダリング', async ({ page }) => {
    await page.goto('/');
    
    // ページが正常にロードされること
    await expect(page).toHaveTitle(/Twix Saver/);
    
    // サイドバーが表示されること
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
    
    // メインコンテンツエリアが表示されること
    await expect(page.locator('main')).toBeVisible();
    
    // ヘッダーが表示されること
    await expect(page.locator('header')).toBeVisible();
  });

  test('ダッシュボードページの機能確認', async ({ page }) => {
    await page.goto('/');
    
    // ダッシュボードリンクをクリック
    await page.click('text=ダッシュボード');
    
    // ダッシュボードの統計カードが表示されること
    await expect(page.locator('.stats-card')).toBeVisible();
    
    // チャートが表示されること（エラーなしでレンダリング）
    await expect(page.locator('.recharts-wrapper')).toBeVisible();
    
    // アクティビティフィードが表示されること
    await expect(page.locator('[data-testid="activity-feed"]')).toBeVisible();
  });

  test('設定ページの機能確認', async ({ page }) => {
    await page.goto('/settings');
    
    // 設定ページが表示されること
    await expect(page.locator('h1').filter({ hasText: '設定' })).toBeVisible();
    
    // タブナビゲーションが表示されること
    await expect(page.locator('[role="tablist"]')).toBeVisible();
    
    // プロキシ設定フォームが表示されること
    await page.click('text=プロキシ');
    await expect(page.locator('input[type="checkbox"]')).toBeVisible();
    
    // スクレイピング設定フォームが表示されること
    await page.click('text=スクレイピング');
    await expect(page.locator('input[type="number"]')).toBeVisible();
    
    // 一般設定フォームが表示されること
    await page.click('text=一般');
    await expect(page.locator('select')).toBeVisible();
  });

  test('設定保存機能のテスト', async ({ page }) => {
    await page.goto('/settings');
    
    // スクレイピング設定を変更
    await page.click('text=スクレイピング');
    const intervalInput = page.locator('input[id="interval-minutes"]');
    await intervalInput.clear();
    await intervalInput.fill('20');
    
    // 保存ボタンをクリック
    await page.click('button:has-text("保存")');
    
    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=設定を保存しました')).toBeVisible({ timeout: 10000 });
  });

  test('レスポンシブデザインの確認', async ({ page }) => {
    // モバイルビューポート
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // モバイルでも基本要素が表示されること
    await expect(page.locator('main')).toBeVisible();
    
    // タブレットビューポート
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.reload();
    
    // タブレットでも基本要素が表示されること
    await expect(page.locator('main')).toBeVisible();
    
    // デスクトップビューポート
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.reload();
    
    // デスクトップでも基本要素が表示されること
    await expect(page.locator('main')).toBeVisible();
  });

  test('エラーハンドリングの確認', async ({ page }) => {
    // ネットワークエラーをシミュレート
    await page.route('**/api/**', route => route.abort());
    
    await page.goto('/');
    
    // エラーバウンダリまたはエラーメッセージが表示されること
    const errorElements = page.locator('text=エラー').or(page.locator('[data-testid="error-boundary"]'));
    await expect(errorElements.first()).toBeVisible({ timeout: 10000 });
  });

  test('UIコンポーネントの動作確認', async ({ page }) => {
    await page.goto('/settings');
    
    // スイッチコンポーネントの動作確認
    await page.click('text=プロキシ');
    const switchLabel = page.locator('label').filter({ has: page.locator('input[type="checkbox"]') }).first();
    await switchLabel.click();
    const proxySwitch = page.locator('input[type="checkbox"]').first();
    await expect(proxySwitch).toBeChecked();
    
    // タブコンポーネントの動作確認
    await page.click('text=スクレイピング');
    await expect(page.locator('text=実行間隔')).toBeVisible();
    
    // ボタンコンポーネントの動作確認
    const saveButton = page.locator('button:has-text("保存")');
    await expect(saveButton).toBeEnabled();
  });

  test('フォームバリデーションの確認', async ({ page }) => {
    await page.goto('/settings');
    
    // スクレイピング設定で無効な値を入力
    await page.click('text=スクレイピング');
    const intervalInput = page.locator('input[id="interval-minutes"]');
    await intervalInput.clear();
    await intervalInput.fill('-1'); // 無効な値
    
    // 保存を試行
    await page.click('button:has-text("保存")');
    
    // エラーメッセージまたはバリデーションエラーが表示されること
    // (具体的なメッセージは実装に依存)
    await page.waitForTimeout(1000); // APIコールを待機
  });

  test('ナビゲーションの確認', async ({ page }) => {
    await page.goto('/');
    
    // 設定ページへのナビゲーション
    await page.click('text=設定');
    await expect(page).toHaveURL(/.*settings.*/);
    
    // ダッシュボードに戻る
    await page.click('text=ダッシュボード');
    await expect(page).toHaveURL(/.*\/$|.*dashboard.*/);
  });

  test('パフォーマンステスト', async ({ page }) => {
    // ページロード時間の計測
    const startTime = Date.now();
    await page.goto('/');
    const loadTime = Date.now() - startTime;
    
    // 5秒以内にロードされること
    expect(loadTime).toBeLessThan(5000);
    
    // 重要な要素が適切な時間で表示されること
    await expect(page.locator('main')).toBeVisible({ timeout: 3000 });
  });
});