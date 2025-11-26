import { useState } from "react";
import MessageBubble from "./MessageBubble";
import ProductCard from "./ProductCard";

export default function ChatWindow() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "bot",
      content:
        "Hi! I’m your PartSelect assistant. I can help you find dishwasher and refrigerator parts, check compatibility, and guide installation."
    }
  ]);

  const [products, setProducts] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input;

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId 
        })
      });

      const data = await res.json();

      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }

      setMessages((prev) => [
        ...prev,
        { role: "bot", content: data.answer || "No response generated." }
      ]);

      if (Array.isArray(data.tool_output) && data.tool_output.length > 0) {
        setProducts(data.tool_output);
      } else {
        setProducts([]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", content: "⚠️ Backend connection failed." }
      ]);
      setProducts([]);
    }
  };

  return (
    <div className="chat-container">

      {/* ✅ FLOATING LEFT SIDEBAR FROM SAME PRODUCT DATA */}
      {products.length > 0 && (
        <div className="product-rec-box">
          <h3 style={{ 
              marginBottom: "12px",
              fontWeight: "600",
              color: "#2f7d78",
              borderBottom: "2px solid #2f7d78",
              paddingBottom: "6px"
            }}>
              Recommended Parts
            </h3>


          <div className="product-grid">
            {products.map((p, i) => (
              <ProductCard key={i} part={p} />
            ))}
          </div>
        </div>
      )}

      {/* ✅ CHAT MESSAGES */}
      <div className="messages-scroll">
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
      </div>

      {/* ✅ INPUT BAR */}
      <div className="input-bar">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask about dishwasher or refrigerator parts..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
