// Auto-dismiss alerts after a few seconds so they don't clutter the page.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".alert").forEach(function (alertEl) {
    setTimeout(function () {
      var alert = bootstrap.Alert.getOrCreateInstance(alertEl);
      alert.close();
    }, 6000);
  });

  // Reload the consultation request page (GET) when the expert changes so
  // the server can render that expert's currently open slots.
  var expertSelect = document.getElementById("expert_id");
  if (expertSelect) {
    expertSelect.addEventListener("change", function () {
      var url = new URL(window.location.href);
      url.searchParams.set("expert_id", expertSelect.value);
      window.location.href = url.toString();
    });
  }
});
