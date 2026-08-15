const SUPPORTED = ["en", "pt-BR", "es"];
const STORAGE_KEY = "pdf-utils-lang";

const I18n = {
  lang: "en",
  dict: {},

  t(key, vars = {}) {
    let text = this.dict[key] ?? key;
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
    return text;
  },

  async load(lang) {
    const next = SUPPORTED.includes(lang) ? lang : "en";
    const res = await fetch(`/static/i18n/${next}.json`);
    if (!res.ok) throw new Error(`locale ${next} missing`);
    this.dict = await res.json();
    this.lang = next;
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.lang = next;
    this.apply();
    document.dispatchEvent(new CustomEvent("i18n:changed", { detail: { lang: next } }));
  },

  detect() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (SUPPORTED.includes(saved)) return saved;
    const nav = (navigator.language || "en").toLowerCase();
    if (nav.startsWith("pt")) return "pt-BR";
    if (nav.startsWith("es")) return "es";
    return "en";
  },

  apply() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = this.t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", this.t(el.dataset.i18nPlaceholder));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", this.t(el.dataset.i18nAria));
    });
    const select = document.getElementById("lang-select");
    if (select) select.value = this.lang;
  },
};

window.I18n = I18n;
window.t = (key, vars) => I18n.t(key, vars);
