(() => {
  const main = document.querySelector("main");
  if (!main) return;
  const navLinks = Array.from(document.querySelectorAll(".topbar nav a"));
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  const setActive = (id) => {
    navLinks.forEach((link) => {
      const target = link.getAttribute("href") || "";
      link.setAttribute("aria-current", target === `#${id}` ? "location" : "false");
    });
  };

  if ("IntersectionObserver" in window && sections.length > 0) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.target.id) {
            setActive(entry.target.id);
          }
        });
      },
      { threshold: 0.35 }
    );
    sections.forEach((section) => observer.observe(section));
  }
})();
