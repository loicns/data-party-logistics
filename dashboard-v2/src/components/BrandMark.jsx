export default function BrandMark({ className = "h-10 w-10", alt = "Data Party Logistics" }) {
  return (
    <img
      src="/favicon.svg?v=port-logo"
      alt={alt}
      className={`block shrink-0 object-contain ${className}`}
      draggable="false"
    />
  );
}
