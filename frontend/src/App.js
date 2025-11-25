import React, { useState } from "react";
import "./App.css";
import { getAIMessage } from "./api/api";

function App() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi, how can I help you today?" }
  ]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);

    const reply = await getAIMessage(input);
    setMessages(prev => [...prev, reply]);

    setInput("");
  };

  return (
    <div className="app-container">
      <div className="header">Instalily Case Study</div>

      <div className="chat-window">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`message ${m.role === "user" ? "user" : "bot"}`}
          >
            {m.content}
          </div>
        ))}
      </div>

      <div className="input-container">
        <input
          className="input-box"
          placeholder="Type a message..."
          value={input}
          onChange={e => setInput(e.target.value)}
        />
        <button className="send-btn" onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default App;

