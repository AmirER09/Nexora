const provider = document.querySelector("#provider");
const model = document.querySelector("#model");
const baseField = document.querySelector("#base-url-field");
const base = document.querySelector("#base_url");
const presetField = document.querySelector("#service-preset-field");
const preset = document.querySelector("#service_preset");
const baseHelp = document.querySelector("#base-url-help");

const presets = {
  openai: {base: "https://api.openai.com/v1", model: "gpt-4o-mini"},
  deepseek: {base: "https://api.deepseek.com", model: "deepseek-flash"},
  qwen: {base: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", model: "qwen-plus"},
  kimi: {base: "https://api.moonshot.ai/v1", model: "kimi-k2.6"},
  alibaba: {base: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", model: "qwen-plus"},
  opencode: {base: "https://opencode.ai/inference/openai/v1", model: "deepseek-v4.1-flash"},
  freebuff: {base: "", model: ""},
  custom: {base: "", model: ""}
};

function setPreset(applyModel = true) {
  const value = presets[preset.value] || presets.custom;
  base.value = value.base;
  if (applyModel && value.model) model.value = value.model;
  if (preset.value === "alibaba") {
    baseHelp.textContent = "آدرس پیش‌فرض بین‌المللی است؛ اگر پنل Alibaba برای حساب تو Workspace یا منطقه دیگری داده، همان آدرس را وارد کن.";
  } else if (preset.value === "opencode") {
    baseHelp.textContent = "برای OpenCode Console از endpoint رسمی OpenAI Chat Completions استفاده می‌شود؛ مدل و کلید را از پنل OpenCode بردار. بعضی مدل‌های رایگان فقط داخل خود OpenCode در دسترس‌اند.";
  } else if (preset.value === "freebuff") {
    baseHelp.textContent = "آدرس رسمی API را از پنل سرویس بردار؛ چون endpoint قابل‌تأیید ثابتی در این تنظیمات نداریم، آدرس حدسی وارد نکن.";
  } else {
    baseHelp.textContent = "Base URL پیش‌فرض را می‌توانی با آدرس رسمی منطقه یا Workspace خودت جایگزین کنی.";
  }
}

function providerUI(changed = false) {
  const selected = provider.value;
  const compatible = selected === "openai_compatible";
  presetField.style.display = compatible ? "flex" : "none";
  baseField.style.display = selected === "gemini" ? "none" : "flex";

  if (selected === "openrouter") {
    base.value = "https://openrouter.ai/api/v1";
    if (changed || !model.value || model.value === "gpt-4o-mini") model.value = "openai/gpt-4o-mini";
    model.placeholder = "مثلاً openai/gpt-4o-mini";
  } else if (selected === "anthropic") {
    if (changed || !base.value || base.value.includes("openrouter.ai")) base.value = "https://api.anthropic.com";
    if (changed || !model.value || model.value.startsWith("openai/")) model.value = "claude-sonnet-4-5";
    model.placeholder = "شناسه مدل از پنل Anthropic";
    baseHelp.textContent = "از کلید API کنسول Anthropic استفاده کن؛ این فیلد آدرس API را می‌گیرد، نه آدرس وب Claude.";
  } else if (selected === "gemini") {
    if (changed || !model.value || !model.value.startsWith("gemini-")) model.value = "gemini-2.5-flash";
    model.placeholder = "مثلاً gemini-2.5-flash";
  } else {
    model.placeholder = "شناسه مدل دقیق سرویس";
    if (changed) setPreset(true);
  }
}

provider.addEventListener("change", () => providerUI(true));
preset.addEventListener("change", () => setPreset(true));
providerUI(false);

const test = document.querySelector("#test-api");
const result = document.querySelector("#test-result");
if (test && result) {
  test.addEventListener("click", async () => {
    test.disabled = true;
    test.classList.add("loading");
    result.className = "test-result";
    result.textContent = "در حال بررسی اتصال؛ ممکن است از سهمیه API استفاده شود...";
    try {
      const data = await postJSON("/settings/test/");
      result.className = "test-result ok";
      result.textContent = "اتصال موفق بود: " + data.reply;
      document.querySelector("#api-status-text").textContent = "متصل";
      document.querySelector("#api-status-dot").classList.remove("status-off");
    } catch (error) {
      result.className = "test-result bad";
      result.textContent = error.message;
    } finally {
      test.disabled = false;
      test.classList.remove("loading");
    }
  });
}
