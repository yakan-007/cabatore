# キャバトレ 🍾 - AI会話練習アプリ

キャバクラ嬢のみおちゃんとの会話練習で接客スキルを向上させるAIアプリケーション

## 🌟 特徴

- **5ターン会話システム**: 心理学研究に基づく最適な会話長
- **リアルタイムフィードバック**: 天の声がその場でアドバイス
- **みおの本音感想**: 会話終了後に詳細な評価
- **感情スコア可視化**: みおの気持ちをグラフで表示
- **段階評価**: また話したい度を0-100%で評価

## セットアップ

### Backend (FastAPI)

1. 環境変数設定
```bash
cd ten-no-koe-backend
cp .env.example .env
# .envファイルにGoogle API Key (Gemini)を設定
```

2. 仮想環境とパッケージインストール
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. サーバー起動
```bash
uvicorn main:app --reload
```

### Frontend (React)

1. パッケージインストール
```bash
cd ten-no-koe-frontend
npm install
```

2. 開発サーバー起動
```bash
npm start
```

## 使い方

1. ブラウザで http://localhost:3000 にアクセス
2. メッセージを入力してBotと会話
3. 天の声からのフィードバックを確認

## 🚀 デプロイ

### Frontend (Vercel)

1. [Vercel](https://vercel.com)でアカウント作成
2. GitHubリポジトリをインポート
3. 設定:
   - **Framework Preset**: Create React App
   - **Root Directory**: `ten-no-koe-frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
4. 環境変数:
   ```
   REACT_APP_API_URL=https://your-railway-backend.railway.app
   ```

### Backend (Railway)

1. [Railway](https://railway.app)でアカウント作成
2. GitHubリポジトリをデプロイ
3. 環境変数を設定:
   ```
   GOOGLE_API_KEY=your-gemini-api-key
   FRONTEND_URL=https://your-vercel-app.vercel.app
   ```
4. nixpacks.tomlが自動的に認識されます

## 📝 環境変数

### Backend (.env)
```
GOOGLE_API_KEY=AIzaSy...  # Google Gemini API Key
FRONTEND_URL=https://your-frontend.vercel.app  # CORS設定用
```

### Frontend (.env)
```
REACT_APP_API_URL=https://your-backend.railway.app  # バックエンドURL
```

## 🔑 Google Gemini API Keyの取得

1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. 「Get API Key」をクリック
3. 新しいAPIキーを作成
4. Railwayの環境変数に設定