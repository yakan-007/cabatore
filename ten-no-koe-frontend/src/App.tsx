import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// 型定義
interface Message {
  role: 'user' | 'bot' | 'voice';
  content: string;
  timestamp: Date;
  detectedPatterns?: string[];
}

interface ConversationResponse {
  bot_response: string;
  voice_feedback: string;
  detected_patterns: string[];
}

interface MioImpressionResponse {
  impression_text: string;
  emotion_scores: { [key: string]: number };
  memorable_moments: string[];
  want_to_talk_again: number;
}

// APIサービス
class ConversationAPI {
  private static readonly BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  static async createSession(): Promise<{ session_id: string; created_at: string }> {
    const response = await fetch(`${this.BASE_URL}/api/session/create`, {
      method: 'POST',
    });
    return response.json();
  }

  static async sendMessage(
    sessionId: string,
    userMessage: string,
    conversationHistory: Message[]
  ): Promise<ConversationResponse> {
    const response = await fetch(`${this.BASE_URL}/api/conversation/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        user_message: userMessage,
        conversation_history: conversationHistory,
      }),
    });
    return response.json();
  }

  static async endConversation(sessionId: string): Promise<MioImpressionResponse> {
    const response = await fetch(`${this.BASE_URL}/api/conversation/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });
    
    const data = await response.json();
    return data;
  }
}

// メッセージ管理
class MessageManager {
  static createUserMessage(content: string): Message {
    return {
      role: 'user',
      content,
      timestamp: new Date(),
    };
  }

  static createBotMessage(content: string): Message {
    return {
      role: 'bot',
      content,
      timestamp: new Date(),
    };
  }

  static createVoiceMessage(content: string, patterns: string[]): Message {
    return {
      role: 'voice',
      content,
      timestamp: new Date(),
      detectedPatterns: patterns,
    };
  }
}

// メインコンポーネント
const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showImpression, setShowImpression] = useState(false);
  const [mioImpression, setMioImpression] = useState<MioImpressionResponse | null>(null);
  const [conversationTurns, setConversationTurns] = useState(0);
  const [maxTurns] = useState(5); // 5ターンルール
  const [conversationCompleted, setConversationCompleted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // セッション初期化
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const data = await ConversationAPI.createSession();
        setSessionId(data.session_id);
      } catch (error) {
        console.error('セッション作成エラー:', error);
      }
    };
    initializeSession();
  }, []);

  // 自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!inputValue.trim() || !sessionId || isLoading || conversationCompleted) return;

    const userMessage = MessageManager.createUserMessage(inputValue);
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // ターン数を増やす
    const newTurnCount = conversationTurns + 1;
    setConversationTurns(newTurnCount);

    try {
      const data = await ConversationAPI.sendMessage(sessionId, userMessage.content, messages);

      // 天の声フィードバックを先に追加（自分の発言直後）
      if (data.voice_feedback) {
        const voiceMessage = MessageManager.createVoiceMessage(data.voice_feedback, data.detected_patterns);
        setMessages(prev => [...prev, voiceMessage]);
      }

      // Bot応答を遅らせて追加
      setTimeout(async () => {
        const botMessage = MessageManager.createBotMessage(data.bot_response);
        setMessages(prev => [...prev, botMessage]);
        
        // 最大ターン数に達したら自動終了
        if (newTurnCount >= maxTurns) {
          setConversationCompleted(true);
          // 少し待ってから感想を表示
          setTimeout(async () => {
            try {
              const impression = await ConversationAPI.endConversation(sessionId);
              setMioImpression(impression);
              setShowImpression(true);
            } catch (error) {
              console.error('感想取得エラー:', error);
            }
          }, 1000);
        }
      }, 800);

    } catch (error) {
      console.error('メッセージ送信エラー:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // エンターキーでの送信を無効化（Shift+Enterで改行のみ許可）
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
    }
  };

  const endConversation = async () => {
    if (!sessionId) return;
    
    setIsLoading(true);
    try {
      const impression = await ConversationAPI.endConversation(sessionId);
      setMioImpression(impression);
      setShowImpression(true);
    } catch (error) {
      console.error('感想取得エラー:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <Header />
      <ConversationProgress 
        currentTurn={conversationTurns}
        maxTurns={maxTurns}
        completed={conversationCompleted}
      />
      <ChatContainer 
        messages={messages}
        isLoading={isLoading}
        messagesEndRef={messagesEndRef}
      />
      <InputArea
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSendMessage={sendMessage}
        onKeyDown={handleKeyDown}
        isLoading={isLoading}
        disabled={conversationCompleted}
      />
      {!conversationCompleted && (
        <div className="conversation-controls">
          <button 
            onClick={endConversation} 
            disabled={isLoading || messages.length === 0}
            className="end-conversation-button"
          >
            会話を終了して感想を聞く
          </button>
        </div>
      )}
      {showImpression && (
        <ImpressionModal 
          impression={mioImpression} 
          onClose={() => setShowImpression(false)} 
        />
      )}
    </div>
  );
};

// サブコンポーネント
const Header: React.FC = () => (
  <header className="App-header">
    <h1>キャバトレ</h1>
  </header>
);

interface ChatContainerProps {
  messages: Message[];
  isLoading: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

const ChatContainer: React.FC<ChatContainerProps> = ({ messages, isLoading, messagesEndRef }) => (
  <div className="chat-container">
    <div className="messages-area">
      {messages.length === 0 && <WelcomeMessage />}
      
      {messages.map((message, index) => (
        <MessageBubble key={index} message={message} />
      ))}
      
      {isLoading && <LoadingIndicator />}
      <div ref={messagesEndRef} />
    </div>
  </div>
);

const WelcomeMessage: React.FC = () => (
  <div className="welcome-message">
    <h2>🍾 キャバトレ - みおちゃんと会話練習</h2>
    <p>キャバクラ嬢のみおちゃんとの5回の会話で、接客スキルを磨きましょう！</p>
    <p>会話中は<strong>天の声</strong>がリアルタイムでアドバイス、最後に<strong>みおの本音感想</strong>が聞けます。</p>
    <div className="welcome-note">
      💡 研究に基づく5ターンシステムで、科学的に会話力を向上させます
    </div>
  </div>
);

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  // 天の声の構造化フィードバックをフォーマット
  const formatVoiceFeedback = (content: string) => {
    if (!content.includes('【')) return content;
    
    const sections = content.split(/【([^】]+)】/).filter(section => section.trim());
    const formattedSections = [];
    
    for (let i = 0; i < sections.length; i += 2) {
      const title = sections[i];
      const body = sections[i + 1];
      if (title && body) {
        formattedSections.push(
          <div key={i} className="feedback-section">
            <div className="feedback-title">【{title}】</div>
            <div className="feedback-body">{body.trim()}</div>
          </div>
        );
      }
    }
    
    return formattedSections.length > 0 ? formattedSections : content;
  };

  return (
    <div className={`message ${message.role}`}>
      <div className="message-header">
        {message.role === 'bot' && '🤖 みお'}
        {message.role === 'user' && '👤 あなた'}
        {message.role === 'voice' && '💭 天の声'}
      </div>
      <div className="message-content">
        {message.role === 'voice' && typeof message.content === 'string' && message.content.includes('【') 
          ? formatVoiceFeedback(message.content)
          : message.content
        }
      </div>
      {message.detectedPatterns && message.detectedPatterns.length > 0 && (
        <div className="detected-patterns">
          検出: {message.detectedPatterns.join(', ')}
        </div>
      )}
    </div>
  );
};

const LoadingIndicator: React.FC = () => (
  <div className="loading-indicator">
    <span>考え中...</span>
  </div>
);

interface InputAreaProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSendMessage: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  isLoading: boolean;
  disabled?: boolean;
}

const InputArea: React.FC<InputAreaProps> = ({ 
  inputValue, 
  setInputValue, 
  onSendMessage, 
  onKeyDown, 
  isLoading,
  disabled = false
}) => (
  <div className="input-area">
    <textarea
      value={inputValue}
      onChange={(e) => setInputValue(e.target.value)}
      onKeyDown={onKeyDown}
      placeholder={disabled ? "会話が完了しました" : "メッセージを入力..."}
      rows={3}
      disabled={isLoading || disabled}
    />
    <button 
      onClick={onSendMessage} 
      disabled={isLoading || !inputValue.trim() || disabled}
    >
      送信
    </button>
  </div>
);

// 進捗表示コンポーネント
interface ConversationProgressProps {
  currentTurn: number;
  maxTurns: number;
  completed: boolean;
}

const ConversationProgress: React.FC<ConversationProgressProps> = ({ currentTurn, maxTurns, completed }) => (
  <div className="conversation-progress">
    <div className="progress-header">
      <h3>会話の進行状況</h3>
      <div className="progress-info">
        <span className="turn-counter">{currentTurn}/{maxTurns}回</span>
        {completed && <span className="completed-badge">完了</span>}
      </div>
    </div>
    <div className="progress-bar">
      <div 
        className="progress-fill" 
        style={{ width: `${(currentTurn / maxTurns) * 100}%` }}
      />
    </div>
    <div className="progress-dots">
      {[...Array(maxTurns)].map((_, i) => (
        <div 
          key={i} 
          className={`progress-dot ${i < currentTurn ? 'filled' : ''} ${i === currentTurn - 1 ? 'current' : ''}`}
        />
      ))}
    </div>
    <div className="research-note">
      💡 研究によると、5回の会話で基本的な印象が決まります（Sunnafrank & Ramirez, 2004）
    </div>
  </div>
);

// みおの感想表示コンポーネント
interface ImpressionModalProps {
  impression: MioImpressionResponse | null;
  onClose: () => void;
}

const ImpressionModal: React.FC<ImpressionModalProps> = ({ impression, onClose }) => {
  if (!impression) {
    return null;
  }

  return (
    <div className="impression-modal-overlay" onClick={onClose}>
      <div className="impression-modal" onClick={(e) => e.stopPropagation()}>
        <div className="impression-header">
          <h2>💭 みおの今日の感想</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="impression-content">
          <div className="impression-text">
            {impression.impression_text || 'impression_textが空です'}
          </div>
          
          {impression.emotion_scores && Object.keys(impression.emotion_scores).length > 0 && (
            <div className="emotion-scores">
              <h3>みおの気持ち</h3>
              {Object.entries(impression.emotion_scores).map(([emotion, score]) => (
                <div key={emotion} className="emotion-bar">
                  <span className="emotion-label">{emotion}</span>
                  <div className="emotion-progress">
                    <div 
                      className="emotion-fill" 
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <span className="emotion-score">{score}%</span>
                </div>
              ))}
            </div>
          )}
          
          {impression.memorable_moments && impression.memorable_moments.length > 0 && (
            <div className="memorable-moments">
              <h3>印象的だった瞬間</h3>
              <ul>
                {impression.memorable_moments.map((moment, index) => (
                  <li key={index}>✨ {moment}</li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="want-to-talk-again">
            <h3>また話したい度</h3>
            <div className="rating">
              <div className="stars">
                {[...Array(5)].map((_, i) => (
                  <span 
                    key={i} 
                    className={i < Math.floor((impression.want_to_talk_again || 0) / 20) ? 'star filled' : 'star'}
                  >
                    ⭐
                  </span>
                ))}
              </div>
              <span className="percentage">{impression.want_to_talk_again || 0}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;