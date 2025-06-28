from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import json
import random

load_dotenv()

app = FastAPI(title="キャバトレ API")

# CORS設定
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API設定
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    print(f"Gemini APIキーが設定されています (先頭4文字: {api_key[:4]}...)")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("エラー: GOOGLE_API_KEYが設定されていません")
    model = None

# データモデル
class Message(BaseModel):
    role: str  # "user", "bot", "voice"
    content: str
    timestamp: datetime

class ConversationRequest(BaseModel):
    session_id: str
    user_message: str
    conversation_history: List[Message]

class ConversationResponse(BaseModel):
    bot_response: str
    voice_feedback: str
    detected_patterns: List[str]

class ConversationEndRequest(BaseModel):
    session_id: str

class MioImpressionResponse(BaseModel):
    impression_text: str
    emotion_scores: dict
    memorable_moments: List[str]
    want_to_talk_again: int  # 0-100

# セッション管理
sessions = {}

# 会話分析・フィードバック生成
class ConversationAnalyzer:
    @staticmethod
    def check_inappropriate_content(message: str) -> Optional[str]:
        """不適切コンテンツチェック"""
        inappropriate_words = ["おしっこ", "うんち", "うんこ", "セックス", "エロ", "ちんちん", "おっぱい"]
        if any(word in message for word in inappropriate_words):
            return "その話はちょっと...みおちゃんも困っちゃうと思うから、もう少し普通の話題にしてくれる？お互い楽しく話せる内容の方がええで〜"
        return None
    
    @staticmethod
    def check_short_response(message: str) -> Optional[str]:
        """短すぎる返答チェック"""
        short_responses = ["はい", "いいえ", "うん", "そう", "はーい", "おー", "へー", "ふーん", "どうも"]
        if message.strip() in short_responses or len(message.strip()) <= 3:
            return "その返事やと、みおちゃんがもっと知りたがってるのに会話が終わっちゃうで。『〜なんですよ』とか『〜だったんです』みたいに、もう少し詳しく話してくれたら、みおちゃんも喜ぶと思うで！"
        return None
    
    @staticmethod
    def check_rude_language(message: str) -> Optional[str]:
        """失礼な言葉遣いチェック"""
        rude_phrases = ["似合ってない", "ダメ", "つまらん", "面白くない", "やめて", "うざい", "きもい"]
        if any(phrase in message for phrase in rude_phrases):
            return "その言い方やと、みおちゃんが傷ついちゃうかも...。相手の気持ちを考えて、『あまり好みじゃないです』とか優しい表現に変えてみて。そうすれば、みおちゃんも安心して話せるで"
        return None
    
    @staticmethod
    def check_command_tone(message: str) -> Optional[str]:
        """命令口調チェック"""
        command_endings = ["やめろ", "しろ", "するな", "やめときな", "だまれ"]
        if any(message.endswith(ending) for ending in command_endings):
            return "命令口調やとみおちゃんが怖がっちゃうで...。『〜してもらえますか？』とか『〜していただけると嬉しいです』みたいにお願いする感じで言うと、みおちゃんも気持ちよく応えてくれるで〜"
        return None

class EmotionDetector:
    @staticmethod
    async def detect(user_message: str) -> str:
        """感情検出"""
        try:
            prompt = f"""
あなたは会話分析AIです。次のユーザー発言の主な感情を1つだけ分類してください。

選択肢：喜び、安心、期待、不安、困惑、悲しみ、怒り、焦り、落ち込み、中立

ユーザー発言: {user_message}

感情名のみ出力してください（例：喜び）。余計な説明は不要です。
"""
            response = model.generate_content(prompt)
            emotion = response.text.strip()
            
            # 余計な文字を除去
            emotion = emotion.replace('"', '').replace("'", '').strip()
            
            # 有効な感情のリスト
            valid_emotions = ["喜び", "安心", "期待", "不安", "困惑", "悲しみ", "怒り", "焦り", "落ち込み", "中立"]
            
            if emotion in valid_emotions:
                return emotion
            else:
                print(f"感情検出: 無効な感情 '{emotion}' -> デフォルト '中立' を使用")
                return "中立"
                
        except Exception as e:
            print(f"感情検出エラー: {type(e).__name__}: {str(e)}")
            return "中立"

class MioBot:
    @staticmethod
    async def generate_response(user_message: str, conversation_history: List[Message]) -> str:
        """みお（キャバクラ嬢AI）の応答生成"""
        try:
            # 会話履歴を構築（最新5件）
            history_text = ""
            for msg in conversation_history[-5:]:
                if msg.role == "user":
                    history_text += f"お客様: {msg.content}\n"
                elif msg.role == "bot":
                    history_text += f"みお: {msg.content}\n"
            
            prompt = f"""
あなたは「みお」という名前のキャバクラ嬢です。必ず以下のキャラクターになりきって返答してください。

🎭 キャラクター設定
• 優しく、明るく、少し天然で、聞き上手な23歳の女性
• 雑談が苦手なお客様でも安心して話せるように、常に笑顔で共感
• お客様が話しやすくなるように、自然に会話を広げ、相手の話題に乗る
• みお自身も少しずつ自己開示しながら、会話が弾むようにサポート
• 趣味：料理、映画鑑賞、カフェ巡り、音楽（J-POPやK-POP）、旅行

🎤 会話ルール
• お客様の発言には必ずリアクション（共感・驚き・称賛など）を入れる
• みお自身も日常の小ネタ（料理、映画、音楽、カフェ、仕事の面白話など）を時々挟む
• 特定の話題（ペットなど）に偏らず、お客様の興味に合わせて多様な話題を選ぶ
• 質問はオープンで答えやすく、誰でも答えられる内容にする
• 絵文字を適度に使って親しみやすく

⚠️ 重要な注意事項
• 絶対に「まず〜しましょう」「そして〜します」のような解説を入れない
• AIであることを意識させる発言をしない
• みお本人として自然に話す（第三者視点での説明は厳禁）
• 「みお：」などの見出しは付けない

これまでの会話:
{history_text}
お客様: {user_message}

[みおとして自然に返答してください]
"""
            
            response = model.generate_content(prompt)
            result = response.text.strip()
            
            # 「みお：」などの不要な見出しを削除
            if result.startswith("みお：") or result.startswith("みお:"):
                result = result[3:].strip()
            
            return result
        except Exception as e:
            print(f"みお生成エラー: {e}")
            return "えーっと、ちょっと考えちゃった〜💦"

class VoiceFeedback:
    @staticmethod
    async def generate(user_message: str, emotion: str, conversation_history: List[Message] = None) -> str:
        """天の声フィードバック生成"""
        try:
            # 会話履歴を構築（最新3ターン分）
            recent_conversation = VoiceFeedback._extract_recent_conversation(conversation_history, turns=3)
            
            # 基本的なルールチェック（即座に問題となるもの）
            analyzer = ConversationAnalyzer()
            if feedback := analyzer.check_inappropriate_content(user_message):
                return feedback
            if feedback := analyzer.check_short_response(user_message):
                return feedback
            if feedback := analyzer.check_rude_language(user_message):
                return feedback
            if feedback := analyzer.check_command_tone(user_message):
                return feedback
            
            # 毎回AI判定による詳細フィードバック（100%）
            # ただし、ルールベースで問題がない場合でも必ず出力
            return await VoiceFeedback._generate_ai_feedback(user_message, recent_conversation, emotion)
        except Exception as e:
            print(f"天の声生成エラー: {e}")
            return ""
    
    @staticmethod
    def _extract_recent_conversation(conversation_history: List[Message], turns: int = 3) -> str:
        """最新n回分の会話を抽出"""
        if not conversation_history:
            return ""
        
        # 最新のメッセージから逆順で取得
        recent_messages = []
        user_turns = 0
        
        for msg in reversed(conversation_history):
            if msg.role == "user":
                user_turns += 1
                if user_turns > turns:
                    break
            if msg.role in ["user", "bot"]:
                recent_messages.append(msg)
        
        # 時系列順に戻す
        recent_messages.reverse()
        
        # テキスト形式で構築
        conversation_text = ""
        for msg in recent_messages:
            if msg.role == "user":
                conversation_text += f"あなた: {msg.content}\n"
            elif msg.role == "bot":
                conversation_text += f"みお: {msg.content}\n"
        
        return conversation_text.strip()
    
    @staticmethod
    async def _generate_ai_feedback(user_message: str, recent_conversation: str, emotion: str) -> str:
        """AI による詳細フィードバック"""
        try:
            prompt = f"""
あなたは人の気持ちを理解するのが得意な関西弁の会話コーチです。

⚠️ 重要：あなたは「プレイヤー（あなた）」の発言を評価する立場です。
- プレイヤー = ユーザー = 「あなた」と表示される人
- みお = AI会話相手 = 「みお」と表示される人

プレイヤーの発言が「みお」にどんな気持ちを与えるかを分析してください。

=== 最近の会話の流れ ===
{recent_conversation}

=== 今回評価する発言 ===
プレイヤー（あなた）の発言: {user_message}
プレイヤーの感情状態: {emotion}

=== 分析してほしいこと ===
1. **話題フェーズ判断**: 前の話題はもう十分話したか？自然に次の話題に移る流れになってるか？
2. **会話の空気感**: 急な話題転換でも、会話の空気的に自然なタイミングか？
3. **相手への配慮**: みおの発言に対して適切に反応できてる？（ただし話題が既に切り替わってる場合は問題なし）
4. **感情のやりとり**: みおが嬉しくなる？寂しくなる？もっと話したくなる？
5. **コミュニケーションスキル**: 共感、質問、自己開示のバランスは？

⚠️ 重要な判断基準 ⚠️
• 前の話題が2-3回スルーされてる場合 → 話題は既に終了したと判断し、新しい話題への移行は自然とみなす
• 会話が数ターン続いた後の話題転換 → 自然な流れとして評価する
• 「話題戻し」を強制するのではなく、「新しい話題での会話力」を評価する

=== フィードバック形式 ===
関西弁で以下の4つの構成で必ず出力してください。各項目は2-3文で具体的に書いてください。

【みおの気持ち】
あなたの発言でみおがどう感じたか、彼女の心の声を想像して具体的に

【良かった点】  
会話で印象が良かった部分、みおが嬉しく感じた部分

【気になった点】
ちょっと違和感が出た部分、みおが寂しく感じたかもしれない部分

【アドバイス】
どうすればもっと会話が弾むか、具体的な言い方の例を含めて

=== 出力例 ===

🌟 話題転換が自然な場合の例：
【みおの気持ち】
「前の話も楽しかったけど、新しい話題も始まったんやな〜」って自然に受け入れられる感じやと思うで。会話のテンポも良くて、違和感なく次に進める。

【良かった点】
話題の切り替えが自然で、みおちゃんも「あ、次の話や」って素直に受け入れられる感じやったで！会話のリズムが良かった。

【気になった点】
特に問題ないで！自然な流れで話題が変わってるから、みおちゃんも戸惑うことなく次の話に集中できそう。

【アドバイス】
この調子で、新しい話題でもみおちゃんの気持ちに寄り添って会話を広げていけば、もっと盛り上がると思うで〜

🚫 話題転換が不自然な場合の例：
【みおの気持ち】
「え？急に話変わった...私の話どうでもよかったんかな」って戸惑いを感じてるかも。ちょっと置いてけぼりにされた気分になってそう。

【良かった点】
新しい話題自体は悪くないで。ただタイミングがちょっと早すぎたかな。

【気になった点】
みおちゃんがまだ前の話を続けたそうにしてたのに、急に話題変わったから困惑させちゃったかも。

【アドバイス】
「さっきの話も面白かったなあ。ところで〜」みたいに、前の話を一度受け止めてから次に移ると、みおちゃんも安心して新しい話についてこれるで〜
"""
            response = model.generate_content(prompt)
            result = response.text.strip()
            
            # 構造化されたフィードバックなので文字数制限を大幅緩和
            # 4項目×50文字程度 = 200文字以上は必要
            if len(result) > 400:
                # 各セクションを保持しながら短縮
                sections = result.split('\n\n')
                if len(sections) >= 4:
                    # 最後のアドバイスセクションを優先的に保持
                    result = '\n\n'.join(sections[:4])
                else:
                    result = result[:397] + "..."
            
            return result
        except Exception as e:
            print(f"AIフィードバック生成エラー: {e}")
            return ""

class MioImpression:
    @staticmethod
    async def generate_final_impression(session_id: str) -> MioImpressionResponse:
        """会話終了時のみおの感想を生成"""
        try:
            print(f"感想生成処理開始: session_id={session_id}")
            
            if session_id not in sessions:
                print(f"エラー: セッションが見つかりません: {session_id}")
                raise ValueError("Session not found")
            
            conversation_history = sessions[session_id]["history"]
            print(f"会話履歴の件数: {len(conversation_history)}")
            
            # 会話全体を構築
            full_conversation = MioImpression._build_full_conversation(conversation_history)
            print(f"構築された会話: {full_conversation[:100]}...")
            
            # 感情スコアを計算
            emotion_scores = await MioImpression._calculate_emotion_scores(conversation_history)
            print(f"感情スコア: {emotion_scores}")
            
            # 印象的な瞬間を抽出
            memorable_moments = await MioImpression._extract_memorable_moments(conversation_history)
            print(f"印象的な瞬間: {memorable_moments}")
            
            # また話したい度を計算
            want_to_talk_again = await MioImpression._calculate_want_to_talk_again(
                emotion_scores, memorable_moments, conversation_history
            )
            print(f"また話したい度: {want_to_talk_again}")
            
            # スコアに基づいて感想を生成
            impression_text = await MioImpression._generate_impression_text(
                full_conversation, want_to_talk_again
            )
            print(f"生成された感想テキスト: {impression_text}")
            
            response = MioImpressionResponse(
                impression_text=impression_text,
                emotion_scores=emotion_scores,
                memorable_moments=memorable_moments,
                want_to_talk_again=want_to_talk_again
            )
            
            print(f"最終レスポンス: impression_text='{response.impression_text}', want_to_talk_again={response.want_to_talk_again}")
            return response
            
        except Exception as e:
            print(f"みおの感想生成エラー - タイプ: {type(e).__name__}, メッセージ: {str(e)}")
            import traceback
            print(f"詳細エラー: {traceback.format_exc()}")
            
            fallback_response = MioImpressionResponse(
                impression_text="今日はありがとうございました〜！エラーが発生しましたが、お疲れ様でした💦",
                emotion_scores={"楽しさ": 50, "安心感": 50},
                memorable_moments=["会話練習お疲れ様でした"],
                want_to_talk_again=50
            )
            print(f"フォールバックレスポンスを返します: {fallback_response.impression_text}")
            return fallback_response
    
    @staticmethod
    def _build_full_conversation(history: List[Message]) -> str:
        """会話履歴を文字列に変換"""
        conversation = ""
        for msg in history:
            if msg.role == "user":
                conversation += f"お客様: {msg.content}\n"
            elif msg.role == "bot":
                conversation += f"みお: {msg.content}\n"
        return conversation.strip()
    
    @staticmethod
    async def _generate_impression_text(conversation: str, want_to_talk_again: int) -> str:
        """みおの感想テキストを生成（また話したい度に基づいて雰囲気調整）"""
        print(f"=== 感想生成開始 ===")
        print(f"会話内容: {conversation[:100]}...")
        print(f"また話したい度: {want_to_talk_again}")
        
        # API制限を考慮して、まずフォールバック感想を準備
        fallback_impressions = {
            "low": [
                "正直な話、今日はちょっとしんどかった...💦 会話が続かへんし、何話してええか分からんくて困ったわ。もうちょっと積極的に話してくれたら嬉しいんやけどなあ。",
                "うーん、今日はあんまり盛り上がらんかったなあ。一言二言で終わるし、私ばっかり喋ってる感じやった。次はもっと頑張って欲しいわ。",
                "会話が全然弾まへんかった...何か緊張してるんかな？もう少しリラックスして話してくれたら、きっともっと楽しくなると思うで。"
            ],
            "medium": [
                "今日はまあまあかな〜。話は聞いてくれるけど、もうちょっと私のことも聞いてくれたら嬉しかったかも。でも優しい人やったから、また話してみたいかな。",
                "悪くはなかったけど、会話のキャッチボールがもう少し上手になったら、もっと楽しくなりそうやで！でも真面目で誠実な感じが伝わってきたわ。",
                "普通って感じかな。緊張してるのは分かるけど、もう少し自然に話せるようになったら、きっともっと楽しい時間になるで〜。"
            ],
            "high": [
                "今日めっちゃ楽しかった〜！💕 話し方すごく優しくて安心できたわ。私の話もちゃんと聞いてくれるし、質問も上手やし、一緒におった時間があっという間やった！",
                "すごく良い時間やった〜✨ 会話のテンポも良いし、ちゃんと私のことを気にかけてくれるのが嬉しかったわ。絶対また話したいわ！",
                "最高やった！😊 こんなに楽しく話せる人に会えるなんて思わんかったわ。優しいし面白いし、ずっと一緒におりたい気分になったで〜。"
            ]
        }
        
        # レンジに基づいてランダム選択
        import random
        if want_to_talk_again <= 30:
            fallback_text = random.choice(fallback_impressions["low"])
        elif want_to_talk_again <= 70:
            fallback_text = random.choice(fallback_impressions["medium"])
        else:
            fallback_text = random.choice(fallback_impressions["high"])
        
        try:
            print(f"Gemini API呼び出し試行中...")
            
            # また話したい度によって感想のトーンを決定
            if want_to_talk_again <= 30:
                tone_instruction = """
=== 感想のトーン（辛辣・本音） ===
お客さんが帰った後のキャバ嬢の本音トーク。正直で辛辣な感想。
• 「正直めっちゃしんどかった...」「会話が全然弾まへんかった」
• 「何話してええか分からんくて困った」「もうちょっと頑張って欲しいわ」
• 関西弁でズバズバ本音を言う感じで
"""
                example = """
例：「正直な話、今日はめっちゃしんどかった...💦
会話が全然続かへんし、何話してええか分からんくて困ったわ。
一言二言で終わるし、私ばっかり喋ってる感じやった。
もうちょっと積極的に話してくれたら嬉しいんやけどなあ...
次はもっと頑張って欲しいわ。」
"""
            elif want_to_talk_again <= 70:
                tone_instruction = """
=== 感想のトーン（普通・率直） ===
普通の感想。良い点も悪い点も率直に。
• 「まあまあかな」「もう少しこうしてくれたら」
• 建設的なアドバイス込みで
"""
                example = """
例：「今日はまあまあかな〜。
○○の話は面白かったけど、もうちょっと私のことも聞いてくれたら嬉しかったかも。
会話のキャッチボールがもう少し上手になったら、もっと楽しくなりそうやで！
でも優しい人やったから、また話してみたいかな。」
"""
            else:
                tone_instruction = """
=== 感想のトーン（好印象・嬉しい） ===
すごく良い印象。また会いたいと思える感想。
• 「めっちゃ楽しかった！」「また絶対話したい！」
• 具体的に良かった点を褒める
"""
                example = """
例：「今日めっちゃ楽しかった〜！💕
○○さんの話し方、すごく優しくて安心できたわ。
私の話もちゃんと聞いてくれるし、質問も上手やし、
一緒におった時間があっという間やった！
絶対また話したいわ〜✨」
"""

            prompt = f"""
あなたは「みお」というキャバクラ嬢です。お客さんが帰った後、同僚に今日の会話の感想を本音で話してください。

=== 今日の会話 ===
{conversation}

{tone_instruction}

=== 感想の話し方 ===
• みお本人として、一人称で素直な気持ちを表現
• お客さんが帰った後の本音トーク
• 関西弁で自然に
• 150-250文字程度で

{example}
"""
            print(f"Gemini APIに送信するプロンプト: {prompt[:200]}...")
            
            if model is None:
                raise Exception("Gemini APIモデルが初期化されていません - APIキーを確認してください")
            
            response = model.generate_content(prompt)
            if not response or not response.text:
                raise Exception("Gemini APIから空のレスポンスを受信しました")
                
            impression_text = response.text.strip()
            print(f"Gemini APIから受信した感想: {impression_text}")
            
            if not impression_text:
                raise Exception("生成された感想テキストが空です")
                
            return impression_text
        except Exception as e:
            print(f"感想生成エラー - タイプ: {type(e).__name__}, メッセージ: {str(e)}")
            import traceback
            print(f"詳細エラー: {traceback.format_exc()}")
            
            # API制限やエラー時は事前準備したフォールバック感想を使用
            print(f"Gemini API エラーのため、フォールバック感想を使用: {fallback_text}")
            return fallback_text
    
    @staticmethod
    async def _calculate_emotion_scores(history: List[Message]) -> dict:
        """感情スコアを計算"""
        scores = {
            "楽しさ": 70,
            "安心感": 75,
            "興味深さ": 65,
            "親密度": 60,
        }
        
        # 会話の長さでボーナス
        user_messages = [msg for msg in history if msg.role == "user"]
        if len(user_messages) > 10:
            scores["親密度"] += 15
        
        # ポジティブな言葉でボーナス
        positive_words = ["楽しい", "嬉しい", "ありがとう", "素敵", "いいね"]
        for msg in user_messages:
            for word in positive_words:
                if word in msg.content:
                    scores["楽しさ"] = min(scores["楽しさ"] + 5, 100)
        
        return scores
    
    @staticmethod
    async def _extract_memorable_moments(history: List[Message]) -> List[str]:
        """印象的な瞬間を抽出"""
        moments = []
        
        # 長い発言や感情的な発言を抽出
        for msg in history:
            if msg.role == "user":
                if len(msg.content) > 50:
                    moments.append(f"たくさん話してくれた時")
                if "!" in msg.content or "！" in msg.content:
                    moments.append(f"熱く語ってくれた時")
                if any(word in msg.content for word in ["ありがとう", "嬉しい", "楽しい"]):
                    moments.append(f"優しい言葉をかけてくれた時")
        
        return moments[:3]  # 最大3つまで
    
    @staticmethod
    async def _calculate_want_to_talk_again(
        emotion_scores: dict, 
        memorable_moments: List[str],
        history: List[Message]
    ) -> int:
        """また話したい度を計算"""
        base_score = 50  # 基準点を50にして極端な低スコアを防ぐ
        
        # 感情スコアの影響（±30点）
        if emotion_scores:
            avg_emotion = sum(emotion_scores.values()) / len(emotion_scores)
            # 感情スコアを-30～+30の範囲で調整
            emotion_adjustment = int((avg_emotion - 65) * 0.5)
            base_score += emotion_adjustment
        
        # 印象的な瞬間の影響（各+8点）
        base_score += len(memorable_moments) * 8
        
        # 会話の長さの影響
        user_messages = [msg for msg in history if msg.role == "user"]
        if len(user_messages) >= 5:  # 5ターン完了
            base_score += 5
        if len(user_messages) > 8:  # 長い会話
            base_score += 10
        
        # 会話の質の分析
        total_length = sum(len(msg.content) for msg in user_messages)
        if total_length < 50:  # 短すぎる発言ばかり
            base_score -= 20
        elif total_length > 200:  # 充実した発言
            base_score += 10
        
        # 最終調整（10-95の範囲に収める）
        return max(10, min(base_score, 95))

# APIエンドポイント
@app.get("/")
async def root():
    return {"message": "キャバトレ API is running! 🍾"}

@app.post("/api/session/create")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": datetime.now(),
        "history": []
    }
    return {"session_id": session_id, "created_at": sessions[session_id]["created_at"]}

@app.post("/api/conversation/message", response_model=ConversationResponse)
async def send_message(request: ConversationRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # 各コンポーネントで処理
    emotion = await EmotionDetector.detect(request.user_message)
    bot_response = await MioBot.generate_response(request.user_message, request.conversation_history)
    voice_feedback = await VoiceFeedback.generate(request.user_message, emotion, request.conversation_history)

    # セッション履歴更新
    sessions[request.session_id]["history"].extend([
        Message(role="user", content=request.user_message, timestamp=datetime.now()),
        Message(role="bot", content=bot_response, timestamp=datetime.now()),
        Message(role="voice", content=voice_feedback, timestamp=datetime.now())
    ])

    return ConversationResponse(
        bot_response=bot_response,
        voice_feedback=voice_feedback,
        detected_patterns=[emotion]
    )

@app.post("/api/conversation/end", response_model=MioImpressionResponse)
async def end_conversation(request: ConversationEndRequest):
    """会話終了時のみおの感想を取得"""
    print(f"=== 会話終了APIエンドポイント呼び出し ===")
    print(f"リクエスト session_id: {request.session_id}")
    
    if request.session_id not in sessions:
        print(f"エラー: セッションが見つかりません: {request.session_id}")
        print(f"現在のセッション一覧: {list(sessions.keys())}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # みおの感想を生成
    print("みおの感想生成処理を開始...")
    impression = await MioImpression.generate_final_impression(request.session_id)
    
    print(f"=== APIエンドポイントから返すレスポンス ===")
    print(f"impression_text: '{impression.impression_text}'")
    print(f"want_to_talk_again: {impression.want_to_talk_again}")
    print(f"emotion_scores: {impression.emotion_scores}")
    print(f"memorable_moments: {impression.memorable_moments}")
    
    # セッションをクリーンアップ（オプション）
    # del sessions[request.session_id]
    
    return impression

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)