export default function BrandMark({ className = "h-14 w-14", alt = "Data Party Logistics" }) {
  return (
    <img
      src="/favicon.png?v=dpl-transparent-logo"
      alt={alt}
      className={`block shrink-0 object-contain ${className}`}
      draggable="false"
    />
  );
}
