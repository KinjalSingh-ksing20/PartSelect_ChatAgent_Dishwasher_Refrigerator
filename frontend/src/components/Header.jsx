export default function Header() {
  return (
    <header className="ps-header">
      <div className="ps-header-left">
        <img
          src="/assets/partselectlogo.svg"
          alt="PartSelect Logo"
          className="ps-logo"
        />
      </div>

      <div className="ps-header-right">
        <span className="ps-nav-item">Order Status</span>
        <span className="ps-nav-item">Your Account</span>
        <span className="ps-cart">🛒</span>
      </div>
    </header>
  );
}

