export default function ProductCard({ part }) {
  if (!part) return null; // ✅ crash guard

  const {
    name,
    brand,
    category,
    price,
    currency,
    in_stock,
    rating,
    review_count,
    image_url,
    compatible_models = [],
    symptoms_vector = [],
    installation_metadata = {},
  } = part;

  return (
    <div className="product-card">
      <img
        src={image_url || "https://via.placeholder.com/300"}
        alt={name}
        className="product-image"
      />

      <h3>{name}</h3>
      <p>{brand} · {category}</p>

      <p className="price">
        {currency || "USD"} ${price}
      </p>

      <p>{in_stock ? "✅ In Stock" : "❌ Out of Stock"}</p>

      {rating && (
        <p>⭐ {rating} ({review_count} reviews)</p>
      )}

      {installation_metadata?.difficulty && (
        <p>Difficulty: {installation_metadata.difficulty}</p>
      )}

      <button className="add-to-cart">Add to Cart</button>
    </div>
  );
}
