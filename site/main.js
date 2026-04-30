(function () {
  const config = window.APP_CONFIG || {};
  const appsheetUrl = config.appsheetUrl || "";
  const needsSetup = !appsheetUrl || appsheetUrl.includes("YOUR_APP_ID");

  const frame = document.getElementById("appsheet-frame");
  const setupMessage = document.getElementById("setup-message");
  const openLink = document.getElementById("open-app-link");
  const title = document.querySelector(".header-main h1");
  const subtitle = document.querySelector(".header-main p");

  if (config.title) {
    document.title = config.title;
    title.textContent = config.title;
  }

  if (config.subtitle) {
    subtitle.textContent = config.subtitle;
  }

  if (needsSetup) {
    setupMessage.hidden = false;
    frame.hidden = true;
    openLink.hidden = true;
    return;
  }

  frame.src = appsheetUrl;
  openLink.href = appsheetUrl;
})();
