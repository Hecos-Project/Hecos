const EMOTICONS = [
  "😊","😃","🤣","😂","😅","😁","😉","😋","😎","😍","😘","😗","😇","🤔","😐",
  "🙄","😏","😣","😥","😮","🤐","😯","😪","😫","😴","😌","🤓","😛","😜","😝",
  "🤤","😒","😓","😔","😕","🙃","🤑","😲","☹","🙁","😖","😞","😟","😤","😢",
  "😭","😦","😧","😨","😩","🤯","😬","😰","😱","😳","🤪","😵","😡","😠","🤬",
  "😷","🤒","🤕","🤢","🤮","🤧","😇","🤠","😎","🤓","🧐","👍","👎","👏","🤝",
  "❤","🔥","✨","🎉","💯","☕","🍕","🌟","💡","💪","👀","🙏","👌","✌","🤞"
];

function initEmoticonPicker() {
  const container = document.createElement("div");
  container.id = "emoticon-picker";
  
  const header = document.createElement("div");
  header.className = "emoji-picker-header";
  header.innerHTML = `<span>Emoji</span><button class="emoji-close-btn" onclick="toggleEmoticonPicker(event)" title="Close">✕</button>`;
  container.appendChild(header);

  const grid = document.createElement("div");
  grid.id = "emoticon-picker-grid";
  container.appendChild(grid);

  EMOTICONS.forEach(emo => {
    const btn = document.createElement("button");
    btn.className = "emoji-btn";
    btn.innerHTML = emo;
    btn.onclick = (e) => {
      e.stopPropagation();
      const input = document.getElementById("user-input");
      if(input) {
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const text = input.value;
        input.value = text.substring(0, start) + emo + text.substring(end);
        input.selectionStart = input.selectionEnd = start + emo.length;
        if(window.autoResize) window.autoResize(input);
        input.focus();
      }
      toggleEmoticonPicker();
    };
    grid.appendChild(btn);
  });

  document.body.appendChild(container);
}

window.toggleEmoticonPicker = function(event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  const picker = document.getElementById("emoticon-picker");
  if (!picker) return;
  
  picker.classList.toggle("active");
  
  if (picker.classList.contains("active")) {
     // Position Picker relatively to the emoji button
     const btn = document.querySelector(".emoji-trigger-btn");
     if(btn) {
         const rect = btn.getBoundingClientRect();
         // Position above the toolbar
         picker.style.bottom = (window.innerHeight - rect.top + 10) + "px";
         picker.style.left = Math.max(10, rect.left - 100) + "px"; // center roughly
     }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  initEmoticonPicker();
});

// Hide picker when clicking outside
document.addEventListener('click', (e) => {
  const picker = document.getElementById("emoticon-picker");
  if (picker && picker.classList.contains("active")) {
      if (!picker.contains(e.target) && !e.target.closest('.emoji-trigger-btn')) {
          picker.classList.remove("active");
      }
  }
});
