document$.subscribe(() => {
  mermaid.initialize({
    startOnLoad: false,
    theme: "neutral",
    securityLevel: "loose",
  });

  mermaid.run({
    querySelector: ".mermaid",
  });
});
