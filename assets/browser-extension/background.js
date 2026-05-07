// SPDX-License-Identifier: MIT
// pluck browser extension — right-click any git repo link to install
//
// This extension adds a context menu item when you right-click a link.
// It opens the pluck:// protocol handler, which must be registered on
// your system (run scripts/install-protocol-handler.sh).

// Create the context menu item on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "pluck-install",
    title: "Install with pluck",
    contexts: ["link"],
  });
});

// When the menu item is clicked, open the pluck:// protocol URL
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "pluck-install" && info.linkUrl) {
    const pluckUrl = "pluck://install?url=" + encodeURIComponent(info.linkUrl);
    chrome.tabs.create({ url: pluckUrl, active: false });
  }
});
