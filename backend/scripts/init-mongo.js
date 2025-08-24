// MongoDB初期化スクリプト
db = db.getSiblingDB('twitter_scraper');

// コレクションの作成とインデックス設定
db.createCollection('tweets');
db.createCollection('target_users');
db.createCollection('scraping_jobs');

// tweets コレクションのインデックス
db.tweets.createIndex({ "id_str": 1 }, { unique: true });
db.tweets.createIndex({ "username": 1 });
db.tweets.createIndex({ "created_at": -1 });
db.tweets.createIndex({ "scraped_at": -1 });

// target_users コレクションのインデックス
db.target_users.createIndex({ "username": 1 }, { unique: true });

// scraping_jobs コレクションのインデックス
db.scraping_jobs.createIndex({ "job_id": 1 }, { unique: true });
db.scraping_jobs.createIndex({ "status": 1 });
db.scraping_jobs.createIndex({ "created_at": -1 });

print('MongoDB initialized successfully for twitter_scraper database');