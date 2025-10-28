import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Sparkles, MessageSquare, Trash2, Upload } from "lucide-react";

interface Message {
  id: string;
  type: "question" | "answer";
  content: string;
  timestamp: number;
}

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  // Load chat history from storage on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const result = await window.localStorage.get("chat-history");
        if (result && result.value) {
          const history = JSON.parse(result.value);
          setMessages(history);
        }
      } catch (error) {
        console.log("No previous chat history found", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadHistory();
  }, []);

  // Save chat history whenever messages change
  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      const saveHistory = async () => {
        try {
          await window.localStorage.set(
            "chat-history",
            JSON.stringify(messages)
          );
        } catch (error) {
          console.error("Failed to save chat history:", error);
        }
      };
      saveHistory();
    }
  }, [messages, isLoading]);

  const handleAskStream = () => {
    if (!question.trim()) return;

    const questionMsg: Message = {
      id: Date.now().toString(),
      type: "question",
      content: question,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, questionMsg]);
    setCurrentAnswer("");
    setIsStreaming(true);
    setIsThinking(true);
    setQuestion("");

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `http://localhost:8000/ask_stream?question=${encodeURIComponent(
      questionMsg.content
    )}`;
    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    let accumulatedAnswer = "";
    let hasFirstToken = false;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.token) {
          if (!hasFirstToken) {
            setIsThinking(false); // stop "đang suy nghĩ"
            hasFirstToken = true;
          }
          accumulatedAnswer += data.token;
          setCurrentAnswer(accumulatedAnswer);
        }
      } catch (err) {
        console.error("JSON parse error:", err);
      }
    };

    es.onerror = (err) => {
      console.error("EventSource error:", err);
      es.close();
      setIsStreaming(false);
      setIsThinking(false);

      if (accumulatedAnswer) {
        const answerMsg: Message = {
          id: (Date.now() + 1).toString(),
          type: "answer",
          content: accumulatedAnswer,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, answerMsg]);
      }
      setCurrentAnswer("");
    };
  };

  const handleClearHistory = async () => {
    if (window.confirm("Bạn có chắc muốn xóa toàn bộ lịch sử chat?")) {
      try {
        await window.localStorage.delete("chat-history");
        setMessages([]);
        setCurrentAnswer("");
      } catch (error) {
        console.error("Failed to clear history:", error);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAskStream();
    }
  };

  // ---- Upload PDF ----
  const handleUploadPDF = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/upload_pdf", {
        method: "POST",
        body: formData,
      });
      console.log(res);
      if (!res.ok) throw new Error(await res.text());

      alert("Tải lên và xử lý file thành công!");
    } catch (err) {
      console.error(err);
      alert("Lỗi khi tải file PDF lên!");
    } finally {
      setUploading(false);
      e.target.value = ""; // reset input
    }
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, currentAnswer]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Đang tải...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-800">
                  Business AI Assistant
                </h1>
                <p className="text-xs text-slate-500">
                  Powered by OmniMer Crop
                </p>
              </div>
            </div>
            {messages.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Xóa lịch sử chat"
              >
                <Trash2 className="w-4 h-4" />
                <span className="hidden sm:inline">Xóa lịch sử</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
          {/* Chat Area */}
          <div
            className="h-[500px] overflow-y-auto p-6 bg-gradient-to-b from-white to-slate-50"
            ref={chatRef}
          >
            {messages.length === 0 && !currentAnswer && (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center mb-6">
                  <MessageSquare className="w-10 h-10 text-blue-600" />
                </div>
                <h2 className="text-2xl font-bold text-slate-800 mb-2">
                  Xin chào! Tôi có thể giúp gì cho bạn?
                </h2>
                <p className="text-slate-500 max-w-md">
                  Đặt câu hỏi của bạn bên dưới và tôi sẽ trả lời một cách chi
                  tiết nhất. Lịch sử chat sẽ được lưu tự động.
                </p>
              </div>
            )}

            <div className="space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.type === "question" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.type === "question" ? (
                    <div className="max-w-[80%] bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-md">
                      <p className="text-sm leading-relaxed">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="max-w-[85%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
                      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100">
                        <div className="w-6 h-6 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
                          <Sparkles className="w-3 h-3 text-white" />
                        </div>
                        <span className="text-xs font-semibold text-slate-600">
                          Business AI Assistant
                        </span>
                      </div>
                      <div className="prose prose-sm max-w-none prose-slate">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {isThinking && (
                <div className="flex justify-start mb-3">
                  <div className="max-w-[85%] bg-white border border-slate-200 rounded-2xl px-5 py-4 shadow-sm italic text-slate-500">
                    Đang tra Chat GPT
                  </div>
                </div>
              )}

              {/* Current streaming answer */}
              {currentAnswer && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100">
                      <div className="w-6 h-6 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
                        <Sparkles className="w-3 h-3 text-white" />
                      </div>
                      <span className="text-xs font-semibold text-slate-600">
                        Business AI Assistant
                      </span>
                    </div>
                    <div className="prose prose-sm max-w-none prose-slate">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {currentAnswer}
                      </ReactMarkdown>
                    </div>
                    {isStreaming && (
                      <div className="flex items-center gap-1 mt-3">
                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-slate-200 bg-white p-4">
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Nhập câu hỏi của bạn..."
                  disabled={isStreaming}
                  rows={1}
                  className="w-full px-4 py-3 pr-12 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-slate-50 disabled:text-slate-500 transition-all"
                  style={{ minHeight: "48px", maxHeight: "120px" }}
                />
              </div>
              <button
                onClick={handleAskStream}
                disabled={!question.trim() || isStreaming}
                className="px-5 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg disabled:shadow-none flex items-center gap-2 font-medium"
              >
                <Send className="w-5 h-5" />
                <span>Gửi</span>
              </button>

              <input
                type="file"
                accept="application/pdf"
                onChange={handleUploadPDF}
                disabled={uploading}
                className="hidden"
                id="uploadPDF"
              />
              <label
                htmlFor="uploadPDF"
                className={`flex items-center gap-2 px-4 py-3 border border-slate-300 rounded-xl cursor-pointer bg-gradient-to-r ${
                  uploading
                    ? "from-slate-300 to-slate-400 cursor-not-allowed"
                    : "from-blue-100 to-indigo-100 hover:from-blue-200 hover:to-indigo-200"
                } transition-all duration-200`}
              >
                <Upload className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-slate-700">
                  {uploading ? "Đang tải..." : "Tải PDF"}
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
