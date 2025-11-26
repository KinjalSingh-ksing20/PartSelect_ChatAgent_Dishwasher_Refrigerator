import { useState } from "react";

export default function PartSelectChat() {
  const [messages, setMessages] = useState([
    {
      role: "bot",
      content:
        "Hi! I’m your PartSelect assistant. I can help you find dishwasher and refrigerator parts, check compatibility, and guide installation.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      const data = await res.json();

      const botMessage = {
        role: "bot",
        content: data.answer,
        product: data.tool_output?.[0]?.part || null,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", content: "⚠️ Backend connection failed." },
      ]);
    }

    setLoading(false);
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="bg-partselectTeal text-white p-4 rounded-lg shadow flex justify-between items-center">
        <h1 className="text-xl font-bold">PartSelect AI Assistant</h1>
        <span className="text-sm bg-white text-partselectTeal px-3 py-1 rounded">
          OEM Parts Only
        </span>
      </div>

      {/* Chat Window */}
      <div className="bg-white mt-4 rounded-lg shadow p-4 h-[500px] overflow-y-auto space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg max-w-[80%] ${
              msg.role === "user"
                ? "ml-auto bg-partselectYellow"
                : "mr-auto bg-gray-100"
            }`}
          >
            <p className="text-sm">{msg.content}</p>

            {/* ✅ Product Card Rendering */}
            {msg.product && (
              <div className="border mt-3 p-3 rounded bg-white">
                <img
                  src={msg.product.image_url}
                  alt={msg.product.name}
                  className="w-32 mb-2"
                />
                <h3 className="font-bold">{msg.product.name}</h3>
                <p className="text-sm text-gray-600">
                  Brand: {msg.product.brand}
                </p>
                <p className="text-sm text-gray-600">
                  Category: {msg.product.category}
                </p>
                <p className="font-bold mt-1">${msg.product.price}</p>

                <div className="flex gap-2 mt-3">
                  <button className="bg-partselectTeal text-white px-3 py-1 rounded text-xs">
                    Add to Cart
                  </button>
                  <button className="border px-3 py-1 rounded text-xs">
                    Check Fit
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="text-sm text-gray-500">Thinking…</div>
        )}
      </div>

      {/* Input Bar */}
      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 border p-3 rounded"
          placeholder="Ask about refrigerator or dishwasher parts..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button
          onClick={sendMessage}
          className="bg-partselectTeal text-white px-5 rounded"
        >
          Send
        </button>
      </div>
    </div>
  );
}

