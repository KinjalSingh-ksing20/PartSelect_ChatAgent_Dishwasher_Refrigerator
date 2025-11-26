export default function MessageBubble({ role, content }) {
  return (
    <div className={`chat-message ${role === "user" ? "chat-user" : "chat-bot"}`}>
      {content}
    </div>
  );
}
