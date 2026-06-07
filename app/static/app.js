// 取り込みフォーム: ファイル選択とクリップボード貼り付け（Ctrl+V）の補助。
(() => {
  const fileInput = document.getElementById("image");
  const preview = document.getElementById("preview");
  if (!fileInput) return;

  function showPreview(file) {
    if (!preview) return;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  }

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    if (file) showPreview(file);
  });

  // スクショをページ上で Ctrl+V → file input にセットして一緒に送信できるようにする。
  window.addEventListener("paste", (event) => {
    const items = event.clipboardData && event.clipboardData.items;
    if (!items) return;
    for (const item of items) {
      if (!item.type.startsWith("image/")) continue;
      const file = item.getAsFile();
      if (!file) continue;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      fileInput.files = transfer.files;
      showPreview(file);
      event.preventDefault();
      break;
    }
  });
})();
