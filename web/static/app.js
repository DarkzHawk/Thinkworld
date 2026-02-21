async function fetchItems() {
  const query = document.getElementById("query").value;
  const tag = document.getElementById("tag").value;
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (tag) params.set("tag", tag);
  const res = await fetch(`/api/items?${params.toString()}`);
  const items = await res.json();
  renderItems(items);
}

function renderItems(items) {
  const container = document.getElementById("items");
  if (!items.length) {
    container.innerHTML = "<p class=\"muted\">No items yet.</p>";
    return;
  }
  container.innerHTML = items
    .map(
      (item) => `
      <div class="item">
        <div>
          <a href="/items/${item.id}">#${item.id}</a> -
          <span>${item.title || item.url}</span>
        </div>
        <div class="meta">
          <span>${item.type || "unknown"}</span>
          <span>${item.status}</span>
          <span>${item.source_domain || ""}</span>
        </div>
      </div>
    `,
    )
    .join("\n");
}

const form = document.getElementById("add-form");
const statusEl = document.getElementById("add-status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Submitting...";
  const data = new FormData(form);
  const url = data.get("url");
  const tagsRaw = data.get("tags") || "";
  const tags = tagsRaw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const res = await fetch("/api/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, tags }),
  });

  if (!res.ok) {
    const err = await res.json();
    statusEl.textContent = err.detail || "Failed";
    return;
  }

  statusEl.textContent = "Queued.";
  form.reset();
  fetchItems();
});

const searchButton = document.getElementById("search");
searchButton.addEventListener("click", fetchItems);

fetchItems();
