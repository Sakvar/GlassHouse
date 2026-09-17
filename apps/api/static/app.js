'use strict';
function updateClocks() {
  document.querySelectorAll('[data-countdown]').forEach((el) => {
    const seconds = Math.max(0, Math.ceil((Date.parse(el.dataset.countdown) - Date.now()) / 1000));
    el.textContent = seconds ? `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}` : el.dataset.ready;
  });
}
updateClocks();
setInterval(updateClocks, 1000);
document.addEventListener('htmx:afterSwap', updateClocks);
document.addEventListener('htmx:beforeRequest', (event) => {
  if (event.detail.elt.id === 'live' && document.activeElement?.closest('#goals form')) {
    event.preventDefault();
  }
});
document.addEventListener('htmx:beforeSwap', (event) => {
  if (event.detail.target.id === 'goals' && [401, 403, 409, 422, 429].includes(event.detail.xhr.status)) {
    event.detail.shouldSwap = true;
    event.detail.isError = false;
  }
});
function connectionError() { document.getElementById('connection-error').hidden = false; }
document.addEventListener('htmx:sendError', connectionError);
document.addEventListener('htmx:responseError', connectionError);
document.addEventListener('htmx:afterRequest', (event) => {
  if (event.detail.successful) document.getElementById('connection-error').hidden = true;
});
