#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");

// 15分間隔でcron:jobsを実行
const INTERVAL_MINUTES = 15;
const INTERVAL_MS = INTERVAL_MINUTES * 60 * 1000;

console.log(`🕒 開発環境スケジューラー開始 (${INTERVAL_MINUTES}分間隔)`);
console.log("Ctrl+C で停止してください\n");

let runCount = 0;

function runScheduledJobs() {
  runCount++;
  const timestamp = new Date().toLocaleString("ja-JP", {
    timeZone: "Asia/Tokyo"
  });
  
  console.log(`[${timestamp}] 実行 #${runCount}: スケジュールされたジョブを実行中...`);
  
  const process = spawn("pnpm", ["run", "cron:jobs"], {
    stdio: "inherit",
    cwd: path.resolve(__dirname, "..")
  });
  
  process.on("error", (error) => {
    console.error(`❌ エラー: ${error.message}`);
  });
  
  process.on("exit", (code) => {
    if (code === 0) {
      console.log(`✅ 実行 #${runCount} 完了\n`);
    } else {
      console.log(`❌ 実行 #${runCount} 失敗 (終了コード: ${code})\n`);
    }
  });
}

// 最初の実行
console.log("📋 初回実行中...");
runScheduledJobs();

// 定期実行を開始
setInterval(runScheduledJobs, INTERVAL_MS);

// 次回実行時刻を表示
function showNextRun() {
  const nextRun = new Date(Date.now() + INTERVAL_MS);
  console.log(`⏰ 次回実行予定: ${nextRun.toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })}`);
}

setTimeout(showNextRun, 5000);

// 終了時の処理
process.on("SIGINT", () => {
  console.log("\n🛑 スケジューラーを停止しています...");
  process.exit(0);
});